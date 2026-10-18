"""
Seller document processing: read an uploaded image/PDF, pull out the details we need,
and compare them with what the seller typed into the application form.

Privacy rules (Aadhaar Act / UIDAI):
- Only a MASKED Aadhaar is accepted. A file that shows all 12 digits is rejected.
- Only the last 4 digits are ever stored. Saved text is redacted first.
- Bank account numbers are kept as last 4 digits only.

OCR is free and local (rapidocr-onnxruntime, pip only). If it is missing or fails,
the document is flagged for manual review. Nothing here ever crashes an upload.
"""

import os
import re
import logging
from typing import Any, Dict, List, Optional

from .ocr_service import DocumentOCRService, GSTIN_REGEX, PAN_REGEX

logger = logging.getLogger(__name__)

REQUIRED_DOC_TYPES = ['AADHAAR', 'PAN', 'BANK_PROOF']  # everything else (name, address, store) is filled in from these three
OCR_DOC_TYPES = {'AADHAAR', 'PAN', 'GST_CERTIFICATE', 'ADDRESS_PROOF', 'BANK_PROOF'}

AADHAAR_PLAIN = re.compile(r'(?<![\dXx*])(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})(?!\d)')
AADHAAR_MASKED = re.compile(r'[Xx*]{4}[\s-]*[Xx*]{4}[\s-]*(\d{4})')
DOB_RE = re.compile(r'(\d{2}[/-]\d{2}[/-]\d{4})')
PIN_RE = re.compile(r'(?<!\d)([1-9]\d{5})(?!\d)')
IFSC_RE = re.compile(r'\b([A-Z]{4}0[A-Z0-9]{6})\b')
ACCOUNT_RE = re.compile(r'(?<!\d)(\d{9,18})(?!\d)')

_NOT_NAMES = {
    'government', 'govt', 'india', 'aadhaar', 'unique', 'identification', 'authority', 'male', 'female', 'transgender',
    'dob', 'year', 'birth', 'address', 'vid', 'download', 'date', 'issued', 'income', 'tax', 'department', 'permanent',
    'account', 'number', 'card', 'father', 'name', 'signature', 'of', 'the', 'to', 'mera', 'aadhaar', 'enrolment', 'help',
}

_engine = None


# ---------------------------------------------------------------- OCR ------

def _get_engine():
    global _engine
    if _engine is None:
        from rapidocr_onnxruntime import RapidOCR  # imported lazily: it is heavy
        _engine = RapidOCR()
    return _engine


def _images_from_file(path: str, mime: str):
    """Yield numpy RGB arrays: one per image, or the first pages of a PDF."""
    import numpy as np
    from PIL import Image

    if path.lower().endswith('.pdf') or 'pdf' in (mime or '').lower():
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(path)
        for i in range(min(len(pdf), 2)):
            yield np.array(pdf[i].render(scale=2).to_pil().convert('RGB'))
    else:
        img = Image.open(path).convert('RGB')
        longest = max(img.size)
        if longest > 1100:  # phone photos are huge; OCR does not need them
            ratio = 1100 / longest
            img = img.resize((int(img.width * ratio), int(img.height * ratio)))
        yield np.array(img)


def warm_ocr() -> None:
    """Load the OCR model in the background when the server starts, so the first upload does not pay for it."""
    import threading

    def run():
        try:
            import numpy as np
            _get_engine()(np.full((64, 256, 3), 255, dtype='uint8'), use_cls=False)
        except Exception as exc:  # reading still works, just slower the first time
            logger.info('OCR warm-up skipped: %s', exc)
    threading.Thread(target=run, daemon=True, name='ocr-warmup').start()


def process_many(jobs: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Reads several documents at the same time. jobs = {doc_type: (path, mime)}. Returns {doc_type: process_document result}."""
    from concurrent.futures import ThreadPoolExecutor
    if not jobs:
        return {}
    with ThreadPoolExecutor(max_workers=len(jobs)) as pool:
        futures = {t: pool.submit(process_document, t, path, mime) for t, (path, mime) in jobs.items()}
        return {t: f.result() for t, f in futures.items()}


def read_text(path: str, mime: str = '') -> Dict[str, Any]:
    """Returns {'status': DONE | UNREADABLE | OCR_UNAVAILABLE, 'text': str}."""
    try:
        engine = _get_engine()
    except Exception as exc:  # missing package or model files
        logger.warning('OCR engine unavailable: %s', exc)
        return {'status': 'OCR_UNAVAILABLE', 'text': ''}
    try:
        lines: List[str] = []
        for img in _images_from_file(path, mime):
            result, _ = engine(img, use_cls=False)  # the angle classifier is slow and uploaded documents are upright
            lines.extend(item[1] for item in (result or []))
        text = '\n'.join(lines).strip()
        return {'status': 'DONE' if text else 'UNREADABLE', 'text': text}
    except Exception as exc:
        logger.warning('OCR failed for %s: %s', os.path.basename(path), exc)
        return {'status': 'UNREADABLE', 'text': ''}


# ------------------------------------------------------------- parsers -----

def _pretty_name(line: str) -> str:
    return re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', line.strip()).title()


def _looks_like_name(line: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z.'-]*", line)
    if not 1 <= len(words) <= 5 or re.search(r'\d', line):
        return False
    if re.sub(r"[A-Za-z .'-]", '', line):
        return False
    return not any(w.lower().strip('.') in _NOT_NAMES for w in words)


def parse_aadhaar(text: str) -> Dict[str, Any]:
    """Details from a masked Aadhaar. Sets 'unmasked' if all 12 digits are visible."""
    masked = AADHAAR_MASKED.search(text)
    if AADHAAR_PLAIN.search(text) and not masked:
        return {'unmasked': True}

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    dob_idx = next((i for i, l in enumerate(lines) if DOB_RE.search(l) or re.search(r'year of birth|dob', l, re.I)), None)
    dob_match = DOB_RE.search(text)

    name = None
    if dob_idx is not None:
        for line in reversed(lines[max(0, dob_idx - 4):dob_idx + 1]):
            if _looks_like_name(line):
                name = _pretty_name(line)
                break
    if not name:
        name = next((_pretty_name(l) for l in lines if _looks_like_name(l)), None)

    gender = re.search(r'\b(male|female|transgender)\b', text, re.I)
    address = None
    addr_match = re.search(r'address\s*[:\-]?\s*(.+)', text, re.I | re.S)
    if addr_match:
        address = re.sub(r'\s+', ' ', addr_match.group(1)).strip()[:250]
    pin = PIN_RE.search(address or text)

    return {
        'name': name,
        'dob': dob_match.group(1) if dob_match else None,
        'gender': gender.group(1).title() if gender else None,
        'address': address,
        'pincode': pin.group(1) if pin else None,
        'aadhaarLast4': masked.group(1) if masked else None,
        'aadhaarMasked': f"XXXX-XXXX-{masked.group(1)}" if masked else None,
    }


def parse_pan(text: str) -> Dict[str, Any]:
    pan = re.search(PAN_REGEX, text.upper())
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    name = father = None
    for i, line in enumerate(lines):
        low = line.lower()
        nxt = lines[i + 1] if i + 1 < len(lines) else ''
        if "father" in low and _looks_like_name(nxt):
            father = _pretty_name(nxt)
        elif re.fullmatch(r"name", low) and _looks_like_name(nxt):
            name = _pretty_name(nxt)
    if not name:
        caps = [_pretty_name(l) for l in lines if _looks_like_name(l)]
        name = caps[0] if caps else None
        father = father or (caps[1] if len(caps) > 1 else None)
    dob = DOB_RE.search(text)
    return {'pan': pan.group(0) if pan else None, 'name': name, 'fatherName': father, 'dob': dob.group(1) if dob else None}


def parse_gst(text: str) -> Dict[str, Any]:
    ent = DocumentOCRService.extract_document_entities(text, 'GST_CERTIFICATE')
    return {'gstin': ent.get('extractedGstin'), 'pan': ent.get('extractedPan'), 'businessName': ent.get('extractedName')}


def parse_address_proof(text: str) -> Dict[str, Any]:
    pin = PIN_RE.search(text)
    return {'pincode': pin.group(1) if pin else None, 'addressSnippet': re.sub(r'\s+', ' ', text)[:200] or None}


BANK_NAME_RE = re.compile(r'(?:account\s*holder(?:\s*name)?|a/?c\s*(?:holder\s*)?name|name\s*of\s*(?:the\s*)?(?:account\s*)?holder|customer\s*name|beneficiary(?:\s*name)?|name)\s*[:\-]?\s*(.*)', re.I)
STATES = ['Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
          'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram', 'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
          'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal', 'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Chandigarh', 'Puducherry']
BUSINESS_WORDS = re.compile(r'\b(traders?|trading|enterprises?|stores?|shop|mart|electronics|agency|agencies|pvt|private|ltd|limited|llp|co|company|industries|sons|brothers|bros|retail|wholesale|solutions|services|supplies|centre|center|bazaar|fashions?|boutique|garments|pharma|medicals?)\b', re.I)


def lookup_ifsc(ifsc: str) -> Dict[str, Any]:
    """Bank, branch and city for an IFSC from the free ifsc.razorpay.com service. Returns {} if offline."""
    try:
        import requests
        r = requests.get(f'https://ifsc.razorpay.com/{ifsc}', timeout=2.5)
        if r.status_code == 200:
            d = r.json()
            return {'bankName': d.get('BANK'), 'branch': d.get('BRANCH'), 'bankCity': d.get('CITY'), 'bankState': d.get('STATE')}
    except Exception:
        pass
    return {}


def lookup_pin(pin: str) -> Dict[str, Any]:
    """City and state for a PIN code from the free api.postalpincode.in service. Returns {} if offline or unknown."""
    try:
        import requests
        d = requests.get(f'https://api.postalpincode.in/pincode/{pin}', timeout=2.5).json()[0]
        if d.get('Status') == 'Success' and d.get('PostOffice'):
            o = d['PostOffice'][0]
            return {'city': o.get('District') or o.get('Division'), 'state': o.get('State'), 'area': o.get('Name')}
    except Exception:
        pass
    return {}


def parse_bank(text: str) -> Dict[str, Any]:
    ifsc = IFSC_RE.search(text.upper())
    acct = ACCOUNT_RE.search(text)
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    holder = None
    for i, line in enumerate(lines):
        m = BANK_NAME_RE.match(line)
        if not m or not re.search(r'name|holder|beneficiary', line, re.I):
            continue
        cand = m.group(1).strip(' :-') or (lines[i + 1] if i + 1 < len(lines) else '')
        if cand and (_looks_like_name(cand) or (BUSINESS_WORDS.search(cand) and not re.search(r'\d{5,}', cand))):
            holder = _pretty_name(cand)
            break
    bank_line = next((l for l in lines if re.search(r'\bbank\b', l, re.I) and len(l) < 60), None)
    out = {'ifsc': ifsc.group(1) if ifsc else None, 'accountLast4': acct.group(1)[-4:] if acct else None, 'accountHolder': holder,
           'bankName': _pretty_name(bank_line) if bank_line else None}
    if out['ifsc']:
        for k, v in lookup_ifsc(out['ifsc']).items():
            if v and (k != 'bankName' or not out['bankName']):
                out[k] = v
    return out


def parse_aadhaar_address(address: Optional[str]) -> Dict[str, Any]:
    """Splits an Aadhaar address into street line, city, state and PIN."""
    if not address:
        return {}
    pin = PIN_RE.search(address)
    text = address[:pin.end()] if pin else address
    text = re.sub(r'(?i)^\s*(c/o|s/o|d/o|w/o|h/o)[^,]*,\s*', '', text).strip(' ,')
    state = next((s for s in STATES if re.search(rf'\b{s}\b', text, re.I)), None)
    info = lookup_pin(pin.group(1)) if pin else {}
    city = info.get('city')
    parts = [p.strip() for p in text.split(',') if p.strip()]
    if parts:
        parts[-1] = re.sub(r'\s*-?\s*\d{6}\s*$', '', parts[-1]).strip()
        parts = [p for p in parts if p]
    if state and parts and parts[-1].lower() == state.lower():
        parts = parts[:-1]
    if not city and parts:
        guess = parts[-1].title()
        if any(st.lower().startswith(guess.lower()) for st in STATES):  # a cut-off state name is not a city
            parts = parts[:-1]
            guess = parts[-1].title() if parts else ''
        city = guess or None
    line_parts = [p for p in parts if not city or p.lower() != city.lower()]
    line = ', '.join(line_parts)
    for tail in (state, city):  # "12 Hill Road Andheri East Mumbai" -> drop the trailing city/state words
        if tail:
            line = re.sub(rf'[\s,]*\b{re.escape(tail)}\b\s*$', '', line, flags=re.I)
    line = re.sub(r'(?<=[a-z])(?=[A-Z])|(?<=\d)(?=[A-Za-z])|(?<=[a-z])(?=\d)', ' ', line)  # OCR often drops spaces: "12HillRoad" -> "12 Hill Road"
    return {'addressLine': line[:200] or text[:200], 'city': city, 'state': state or info.get('state'), 'pincode': pin.group(1) if pin else None}


def build_autofill(user, app, docs) -> Dict[str, Any]:
    """Every application field we can fill from the Aadhaar, PAN and bank proof, plus where each value came from.
    Values are suggestions: the seller can still change any of them."""
    by = {d.docType: (d.extractedFields or {}) for d in docs if d.ocrStatus == 'DONE'}
    aad, pan, bank = by.get('AADHAAR', {}), by.get('PAN', {}), by.get('BANK_PROOF', {})
    fields: Dict[str, Any] = {}
    src: Dict[str, str] = {}

    def put(key, value, source):
        if value:
            fields[key], src[key] = value, source

    names = [(n, s) for n, s in ((pan.get('name'), 'PAN card'), (aad.get('name'), 'Aadhaar'), (bank.get('accountHolder'), 'bank proof')) if n]
    if names:
        name, source = names[0]
        if ' ' not in name:  # OCR ran the words together ("Rahulmohansharma"): use a spaced spelling of the same name from another document
            name, source = next(((n, s) for n, s in names[1:] if ' ' in n and _names_match(name, n)), (name, source))
        put('applicantName', name, source)
    put('pan', pan.get('pan'), 'PAN card')
    addr = parse_aadhaar_address(aad.get('address'))
    put('address', addr.get('addressLine'), 'Aadhaar address')
    put('city', addr.get('city'), 'Aadhaar address')
    put('addressState', addr.get('state'), 'Aadhaar address')
    put('pincode', addr.get('pincode') or aad.get('pincode'), 'Aadhaar address')
    holder = bank.get('accountHolder')
    if holder and BUSINESS_WORDS.search(holder):
        put('companyName', holder, 'bank proof (account holder)')
    elif fields.get('applicantName'):
        put('companyName', f"{fields['applicantName'].split()[0]} Store", 'suggested from your name, you can rename it')
    if fields.get('companyName'):
        fields['storeName'], src['storeName'] = fields['companyName'], src['companyName']
    put('email', user.email.lower(), 'your account')
    put('phone', user.phone, 'your account')
    return {'fields': fields, 'sources': src, 'bank': {k: bank.get(k) for k in ('accountHolder', 'bankName', 'branch', 'ifsc', 'accountLast4') if bank.get(k)}}


# ------------------------------------------------------- orchestration -----

def process_document(doc_type: str, path: str, mime: str = '') -> Dict[str, Any]:
    """Reads one uploaded file. Returns fields ready to save on a SellerDocument."""
    out: Dict[str, Any] = {'ocrStatus': 'NOT_REQUIRED', 'extractedFields': {}, 'redactedText': '', 'confidence': 0.0, 'warnings': []}
    if doc_type not in OCR_DOC_TYPES:
        return out

    res = read_text(path, mime)
    out['ocrStatus'] = res['status']
    text = res['text']
    if res['status'] == 'OCR_UNAVAILABLE':
        out['warnings'].append('Automatic reading is not available. An administrator will read this document by hand.')
        return out
    if res['status'] == 'UNREADABLE':
        out['warnings'].append('We could not read this file. Upload a clearer, well-lit image or PDF.')
        return out

    if doc_type == 'AADHAAR':
        fields = parse_aadhaar(text)
        if fields.get('unmasked'):
            # Do not keep anything from this file.
            out.update(ocrStatus='REJECTED', extractedFields={}, redactedText='')
            out['warnings'].append('This Aadhaar shows all 12 digits. Upload the masked Aadhaar from myAadhaar (first 8 digits hidden).')
            return out
        wanted = ('name', 'dob', 'gender', 'address', 'pincode', 'aadhaarMasked', 'aadhaarLast4')
        if not fields.get('aadhaarLast4'):
            out['warnings'].append('We could not find the masked Aadhaar number (XXXX XXXX 1234).')
    elif doc_type == 'PAN':
        fields, wanted = parse_pan(text), ('pan', 'name', 'fatherName', 'dob')
        if not fields.get('pan'):
            out['warnings'].append('We could not find a valid PAN number on this file.')
    elif doc_type == 'GST_CERTIFICATE':
        fields, wanted = parse_gst(text), ('gstin', 'pan', 'businessName')
        if not fields.get('gstin'):
            out['warnings'].append('We could not find a valid GSTIN on this file.')
    elif doc_type == 'ADDRESS_PROOF':
        fields, wanted = parse_address_proof(text), ('pincode', 'addressSnippet')
    else:
        fields, wanted = parse_bank(text), ('accountHolder', 'bankName', 'branch', 'ifsc', 'accountLast4')

    out['extractedFields'] = {k: fields.get(k) for k in wanted if fields.get(k)}
    out['redactedText'] = DocumentOCRService.redact_sensitive_pii(text)[:1500]
    found = sum(1 for k in wanted if fields.get(k))
    out['confidence'] = round(100.0 * found / max(1, len(wanted)), 1)
    return out


def _name_tokens(value: Optional[str]) -> set:
    return set(re.findall(r'[a-z0-9]+', (value or '').lower()))


def _names_match(a: Optional[str], b: Optional[str]) -> bool:
    """True if two names share a word, or one contains the other once spaces are removed
    (OCR often reads 'Rahul Sharma' as 'RahulSharma')."""
    if _name_tokens(a) & _name_tokens(b):
        return True
    sa, sb = ''.join(sorted(_name_tokens(a))), ''.join(sorted(_name_tokens(b)))
    ca, cb = (re.sub(r'[^a-z0-9]', '', (v or '').lower()) for v in (a, b))  # in order: sets have no order, so they cannot be joined
    for x, y in ((ca, cb), (sa, sb)):
        if len(x) >= 4 and len(y) >= 4 and (x in y or y in x):
            return True
    parts_a, parts_b = _name_tokens(a), cb
    return any(len(w) >= 3 and w in parts_b for w in parts_a)


def compare_application(app, docs) -> Dict[str, Any]:
    """Compares the form with what the documents say. Returns checks plus a risk score."""
    by_type = {d.docType: (d.extractedFields or {}) for d in docs if d.ocrStatus == 'DONE'}
    aad, pan, gst, addr = by_type.get('AADHAAR', {}), by_type.get('PAN', {}), by_type.get('GST_CERTIFICATE', {}), by_type.get('ADDRESS_PROOF', {})
    checks: List[Dict[str, str]] = []

    def add(label: str, status: str, detail: str):
        checks.append({'label': label, 'status': status, 'detail': detail})

    form_pan = (app.pan or '').strip().upper()
    form_gstin = (app.gstin or '').strip().upper()

    if form_pan and pan.get('pan'):
        ok = form_pan == pan['pan']
        add('PAN matches the PAN card', 'match' if ok else 'mismatch', f"Form {form_pan}, card {pan['pan']}")
    else:
        add('PAN matches the PAN card', 'missing', 'PAN could not be read from the card')

    if form_gstin and len(form_gstin) >= 12 and form_pan:
        ok = form_gstin[2:12] == form_pan
        add('PAN is inside the GSTIN', 'match' if ok else 'mismatch', f"GSTIN holds {form_gstin[2:12]}, form PAN {form_pan}")
    if form_gstin and gst.get('gstin'):
        ok = form_gstin == gst['gstin']
        add('GSTIN matches the certificate', 'match' if ok else 'mismatch', f"Form {form_gstin}, certificate {gst['gstin']}")

    for label, doc in (('Applicant name matches Aadhaar', aad), ('Applicant name matches PAN card', pan)):
        if doc.get('name'):
            ok = _names_match(app.applicantName, doc['name'])
            add(label, 'match' if ok else 'mismatch', f"Form '{app.applicantName}', document '{doc['name']}'")
        else:
            add(label, 'missing', 'Name could not be read')

    bank = by_type.get('BANK_PROOF', {})
    if bank.get('accountHolder'):
        ok = _names_match(app.applicantName, bank['accountHolder']) or _names_match(app.companyName, bank['accountHolder'])
        add('Bank account holder matches the applicant', 'match' if ok else 'mismatch', f"Form '{app.applicantName}', bank '{bank['accountHolder']}'")
    else:
        add('Bank account holder matches the applicant', 'missing', 'Account holder name could not be read')

    form_pin = (app.pincode or '').strip()
    doc_pin = addr.get('pincode') or aad.get('pincode')
    if form_pin and doc_pin:
        add('Store PIN code matches the documents', 'match' if form_pin == doc_pin else 'mismatch', f"Form {form_pin}, document {doc_pin}")

    mismatches = sum(1 for c in checks if c['status'] == 'mismatch')
    missing = sum(1 for c in checks if c['status'] == 'missing')
    risk = min(100, 10 + 20 * mismatches + 8 * missing)
    return {
        'checks': checks, 'mismatches': mismatches, 'missing': missing, 'riskScore': risk,
        'riskCategory': 'Low' if risk <= 25 else ('Medium' if risk <= 55 else 'High'),
    }


def merge_identity(docs) -> Dict[str, Any]:
    """One masked identity card for the admin, built from the Aadhaar and PAN reads."""
    ident: Dict[str, Any] = {}
    for d in docs:
        f = d.extractedFields or {}
        if d.docType == 'AADHAAR' and d.ocrStatus == 'DONE':
            ident.update({k: f[k] for k in ('name', 'dob', 'gender', 'address', 'pincode', 'aadhaarMasked') if f.get(k)})
        if d.docType == 'PAN' and d.ocrStatus == 'DONE':
            ident.update({'pan': f.get('pan'), 'panName': f.get('name'), 'fatherName': f.get('fatherName')})
            ident.setdefault('dob', f.get('dob'))
        if d.docType == 'BANK_PROOF' and d.ocrStatus == 'DONE':
            ident.update({k: f[k] for k in ('accountHolder', 'bankName', 'branch', 'ifsc', 'accountLast4') if f.get(k)})
    return {k: v for k, v in ident.items() if v}


def decide_status(app, docs, comparison: Dict[str, Any]) -> Dict[str, Any]:
    """Which status a submitted application should land in, and why."""
    have = {d.docType for d in docs}
    missing = [t for t in REQUIRED_DOC_TYPES if t not in have]
    if missing:
        return {'status': 'NEEDS_MORE_INFORMATION', 'reason': f"Missing documents: {', '.join(missing)}", 'missing': missing}
    rejected = [d.docType for d in docs if d.ocrStatus == 'REJECTED']
    if rejected:
        return {'status': 'NEEDS_MORE_INFORMATION', 'reason': 'A document must be uploaded again: ' + ', '.join(rejected), 'missing': rejected}
    unread = [d.docType for d in docs if d.docType in ('AADHAAR', 'PAN') and d.ocrStatus != 'DONE']
    if comparison['mismatches'] or unread:
        why = 'Details do not match the documents' if comparison['mismatches'] else 'Identity documents could not be read automatically'
        return {'status': 'NEEDS_MANUAL_REVIEW', 'reason': why, 'missing': []}
    return {'status': 'PENDING_ADMIN_APPROVAL', 'reason': 'All documents uploaded and the details match.', 'missing': []}
