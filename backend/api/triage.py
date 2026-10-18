"""
Autopilot triage for seller applications.

The system reads every application that is waiting and prepares the routine work, so the admin does not open each one:
  READY   everything checks out: documents read and matching, store pinned. The admin sets a risk limit; at or under it, one click approves.
  ASK     documents or the map pin are missing. The message to the seller is already written.
  REVIEW  something looks off (mismatch, unreadable ID). A person needs to look. READY ones above the admin's risk limit also wait.

Triage only recommends. It never approves, rejects or changes anything: the admin confirms every decision.
"""

from .models import SellerApplication

WAITING = ('PENDING_ADMIN_APPROVAL', 'NEEDS_MANUAL_REVIEW')


def recommend(app) -> dict:
    """One application -> {action, reason, message}. `message` is a ready-to-send note for ASK."""
    docs = {d.docType: d for d in app.documents.all()}
    missing = [name for key, name in (('AADHAAR', 'Aadhaar card (masked)'), ('PAN', 'PAN card'), ('BANK_PROOF', 'bank proof')) if key not in docs]
    if app.storeLatitude is None or app.storeLongitude is None:
        missing.append('your store location pinned on the map')
    if missing:
        return {'action': 'ASK', 'reason': 'Missing: ' + ', '.join(missing),
                'message': 'Please add the following so we can finish checking your application: ' + ', '.join(missing) + '.'}
    unread = [n for k, n in (('AADHAAR', 'Aadhaar'), ('PAN', 'PAN')) if docs[k].ocrStatus != 'DONE']
    mismatch = [c.get('label', 'a detail') for c in (app.verificationResults or {}).get('checks', []) if c.get('status') == 'mismatch']
    if unread:
        return {'action': 'REVIEW', 'reason': f"{' and '.join(unread)} could not be read automatically", 'message': ''}
    if mismatch:
        return {'action': 'REVIEW', 'reason': 'Does not match the documents: ' + '; '.join(mismatch), 'message': ''}
    return {'action': 'READY', 'reason': f'Documents read and matching, store pinned. Risk {app.riskScore}/100', 'message': ''}


def triage_all() -> dict:
    rows = []
    for app in SellerApplication.objects.filter(status__in=WAITING).order_by('createdAt'):
        rows.append({'id': app.id, 'company': app.companyName, 'city': app.city, 'riskScore': app.riskScore, **recommend(app)})
    return {
        'rows': rows,
        'ready': sum(r['action'] == 'READY' for r in rows),
        'ask': sum(r['action'] == 'ASK' for r in rows),
        'review': sum(r['action'] == 'REVIEW' for r in rows),
    }
