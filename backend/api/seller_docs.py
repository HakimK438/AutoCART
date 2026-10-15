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

REQUIRED_DOC_TYPES = ['AADHAAR', 'PAN', 'GST_CERTIFICATE', 'ADDRESS_PROOF', 'BANK_PROOF', 'STORE_PHOTO']
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
        if longest > 1400:  # phone photos are huge; OCR does not need them
            ratio = 1400 / longest
            img = img.resize((int(img.width * ratio), int(img.height * ratio)))
        yield np.array(img)


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
            result, _ = engine(img)
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


def parse_bank(text: str) -> Dict[str, Any]:
    ifsc = IFSC_RE.search(text.upper())
    acct = ACCOUNT_RE.search(text)
    return {'ifsc': ifsc.group(1) if ifsc else None, 'accountLast4': acct.group(1)[-4:] if acct else None}


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
        fields, wanted = parse_bank(text), ('ifsc', 'accountLast4')

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
    ca, cb = ''.join(_name_tokens(a)), ''.join(_name_tokens(b))
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
