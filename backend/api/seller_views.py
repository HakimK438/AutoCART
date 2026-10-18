"""
Seller onboarding API.

Flow:  create application (DRAFT) -> upload documents (read automatically) -> submit
       -> admin reviews the full profile -> APPROVE / REJECT / REQUEST_INFO / SUSPEND.

Rules enforced here, on the server:
- Only a signed-in user can apply, and sees only their own application.
- Only ADMIN / STAFF can list everything or take a decision.
- Uploaded files are private: served only to the applicant and to admins.
- The AI/OCR never approves anyone. It only reads documents and suggests a risk score.
"""

import re
import uuid
import datetime
from typing import Optional, Tuple

from django.http import FileResponse
from rest_framework import status as http
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from . import seller_docs
from .models import (
    Product, Seller, SellerApplication, SellerApplicationAudit, SellerDocument, Store, User,
)
from .ocr_service import GSTIN_REGEX, PAN_REGEX, DocumentOCRService
from .location_service import resolve_coordinates
from .secure_fields import decrypt, encrypt
from .serializers import SellerApplicationAuditSerializer, SellerApplicationSerializer
from .views import get_user_from_token

ADMIN_ROLES = ('ADMIN', 'STAFF')
FINAL_STATES = ('APPROVED', 'REJECTED', 'SUSPENDED')
EDITABLE_STATES = ('DRAFT', 'NEEDS_MORE_INFORMATION')
IMAGE_ONLY = {'STORE_PHOTO'}


# ----------------------------------------------------------------- helpers --

def _require(request, roles: Optional[Tuple[str, ...]] = None):
    """Returns (user, error_response). error_response is None when the caller may continue."""
    user = get_user_from_token(request)
    if not user:
        return None, Response({'detail': 'Please sign in to continue.'}, status=http.HTTP_401_UNAUTHORIZED)
    if roles and user.role not in roles:
        return user, Response({'detail': 'You do not have permission to do this.'}, status=http.HTTP_403_FORBIDDEN)
    return user, None


def _is_admin(user) -> bool:
    return user.role in ADMIN_ROLES


def _owns(user, app) -> bool:
    return bool(app.ownerUserId) and app.ownerUserId == user.id


def _audit(app, from_status, to_status, action, by, reason=''):
    SellerApplicationAudit.objects.create(
        id=f"aud-{uuid.uuid4().hex[:8]}", application=app, fromStatus=from_status, toStatus=to_status,
        action=action, performedBy=by, reason=reason,
    )


def _load(pk):
    return SellerApplication.objects.filter(id=pk).first()


def _doc_json(doc, admin: bool):
    data = {
        'id': doc.id, 'docType': doc.docType, 'fileName': doc.fileName, 'mimeType': doc.mimeType, 'sizeBytes': doc.sizeBytes,
        'ocrStatus': doc.ocrStatus, 'extractedFields': doc.extractedFields, 'confidence': doc.confidence,
        'warnings': doc.warnings, 'uploadedAt': doc.uploadedAt,
        'fileUrl': f"/api/seller/applications/{doc.application_id}/documents/{doc.id}/file",
    }
    if admin:
        data['redactedText'] = doc.redactedText
    return data


def _profile(app, viewer):
    """Everything an admin (or the applicant) needs to see about one application, in one response."""
    admin = _is_admin(viewer)
    docs = list(app.documents.all().order_by('uploadedAt'))
    comparison = seller_docs.compare_application(app, docs)
    have = {d.docType for d in docs}
    data = SellerApplicationSerializer(app).data
    data.pop('audit_logs', None)
    data.update({
        'documents': [_doc_json(d, admin) for d in docs],
        'requiredDocuments': seller_docs.REQUIRED_DOC_TYPES,
        'missingDocuments': [t for t in seller_docs.REQUIRED_DOC_TYPES if t not in have],
        'identity': app.identityDetails or seller_docs.merge_identity(docs),
        'comparison': comparison,
        'store': {
            'name': app.storeName or app.companyName, 'address': app.address, 'city': app.city, 'state': app.addressState,
            'pincode': app.pincode, 'latitude': app.storeLatitude, 'longitude': app.storeLongitude,
        },
        'auditTrail': SellerApplicationAuditSerializer(app.audit_logs.all().order_by('timestamp'), many=True).data,
        'liveProducts': [
            {'id': p.id, 'name': p.name, 'price': p.price, 'image': (p.images or [''])[0]}
            for p in Product.objects.filter(seller=app.companyName)[:24]
        ] if app.status == 'APPROVED' else [],
    })
    return data


def _validate_form(data) -> dict:
    errors = {}
    get = lambda k: str(data.get(k) or '').strip()  # noqa: E731
    if not get('companyName'):
        errors['companyName'] = 'Enter your business name.'
    if not get('contactName'):
        errors['contactName'] = 'Enter the name of the person applying.'
    if len(re.sub(r'\D', '', get('phone'))) < 10:
        errors['phone'] = 'Enter a 10-digit phone number.'
    if '@' not in get('email'):
        errors['email'] = 'Enter a valid business email.'
    if not re.fullmatch(r'[A-Z]{5}[0-9]{4}[A-Z]', get('pan').upper()):
        errors['pan'] = 'PAN must look like ABCDE1234F.'
    if get('gstin') and not re.fullmatch(GSTIN_REGEX, get('gstin').upper()):  # optional: only checked when given
        errors['gstin'] = 'GSTIN must be 15 characters, like 27ABCDE1234F1Z5.'
    if not get('address'):
        errors['address'] = 'Enter the store address.'
    if not re.fullmatch(r'[1-9]\d{5}', get('pincode')):
        errors['pincode'] = 'Enter a 6-digit PIN code.'
    try:
        lat, lng = float(data.get('storeLatitude')), float(data.get('storeLongitude'))
        if not (6 <= lat <= 38 and 68 <= lng <= 98):
            errors['location'] = 'The pin must be on the map inside India.'
    except (TypeError, ValueError):
        errors['location'] = 'Drop the pin on the map where your store is.'
    return errors  # products are added later, from the seller dashboard


# ------------------------------------------------------------------- views --

@api_view(['GET', 'POST'])
@permission_classes([AllowAny])
@parser_classes([JSONParser, FormParser, MultiPartParser])
def seller_applications_view(request):
    """GET: admins see all (filter with ?status=), everyone else sees only their own. POST: start or update your application."""
    user, err = _require(request)
    if err:
        return err

    if request.method == 'GET':
        if _is_admin(user):
            apps = SellerApplication.objects.all().order_by('-createdAt')
            wanted = request.query_params.get('status') or request.query_params.get('state')
            if wanted:
                apps = apps.filter(status=wanted)
        else:
            apps = SellerApplication.objects.filter(ownerUserId=user.id).order_by('-createdAt')
        rows = []
        for a in apps:
            row = SellerApplicationSerializer(a).data
            row.pop('audit_logs', None)
            row['documentCount'] = a.documents.count()
            rows.append(row)
        return Response(rows)

    data = request.data
    errors = _validate_form(data)
    if errors:
        return Response({'detail': 'Please fix the highlighted fields.', 'errors': errors}, status=http.HTTP_400_BAD_REQUEST)

    fields = {
        'companyName': str(data['companyName']).strip(), 'storeName': str(data.get('storeName') or data['companyName']).strip(),
        'applicantName': str(data['contactName']).strip(), 'email': str(data['email']).strip().lower(),
        'phone': str(data['phone']).strip(), 'gstin': str(data.get('gstin') or '').strip().upper(), 'pan': str(data['pan']).strip().upper(),
        'businessType': str(data.get('businessType') or 'Retailer'), 'address': str(data['address']).strip(),
        'city': str(data.get('city') or '').strip(), 'addressState': str(data.get('state') or '').strip(),
        'pincode': str(data['pincode']).strip(), 'storeLatitude': float(data['storeLatitude']),
        'storeLongitude': float(data['storeLongitude']), 'productCategories': data.get('productCategories') or [],
        'plannedProducts': [
            {'name': str(p.get('name')).strip(), 'category': str(p.get('category') or '').strip(), 'approxPrice': p.get('approxPrice') or 0,
             'stock': max(0, int(p.get('stock') or 0)) if str(p.get('stock') or '0').isdigit() else 0, 'image': str(p.get('image') or '')[:500]}
            for p in data.get('plannedProducts', []) if str(p.get('name', '')).strip()
        ],
    }
    existing = SellerApplication.objects.filter(ownerUserId=user.id).exclude(status__in=FINAL_STATES).first()
    if existing and existing.status not in EDITABLE_STATES:
        return Response({'detail': 'You already have an application under review.', 'applicationId': existing.id},
                        status=http.HTTP_409_CONFLICT)
    if existing:
        for k, v in fields.items():
            setattr(existing, k, v)
        existing.save()
        return Response(_profile(existing, user))

    app = SellerApplication.objects.create(id=f"app-{uuid.uuid4().hex[:8]}", ownerUserId=user.id, status='DRAFT', **fields)
    _audit(app, '', 'DRAFT', 'APPLICATION_STARTED', user.email, 'Seller started an application.')
    return Response(_profile(app, user), status=http.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
def seller_application_start_view(request):
    """Someone created a seller account: open a draft application straight away so the admin can see the sign-up and the seller can resume."""
    user, err = _require(request)
    if err:
        return err
    existing = SellerApplication.objects.filter(ownerUserId=user.id).exclude(status__in=FINAL_STATES).first()
    if existing:
        return Response(_profile(existing, user))
    app = SellerApplication.objects.create(id=f"app-{uuid.uuid4().hex[:8]}", ownerUserId=user.id, status='DRAFT', applicantName=user.name, email=user.email.lower(),
                                           phone=user.phone or '', companyName=f"{user.name} (store not named yet)", city='Mumbai')
    _audit(app, '', 'DRAFT', 'SELLER_ACCOUNT_CREATED', user.email, 'Created a seller account. Application not submitted yet.')
    return Response(_profile(app, user), status=http.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def seller_application_detail_view(request, pk):
    """The full seller profile: identity, store location, products, documents, checks and history."""
    user, err = _require(request)
    if err:
        return err
    app = _load(pk)
    if not app or not (_is_admin(user) or _owns(user, app)):
        return Response({'detail': 'Application not found.'}, status=http.HTTP_404_NOT_FOUND)
    return Response(_profile(app, user))


def _save_upload(app, doc_type, upload):
    """Saves one uploaded file (replacing the previous one of that type). Reading happens separately so several files can be read at once."""
    for old in app.documents.filter(docType=doc_type):  # one file per type: a new upload replaces the old one
        old.file.delete(save=False)
        old.delete()
    doc = SellerDocument(id=f"doc-{uuid.uuid4().hex[:8]}", application=app, docType=doc_type, fileName=upload.name[:255],
                         mimeType=upload.content_type or '', sizeBytes=upload.size)
    doc.file.save(upload.name, upload, save=False)
    doc.save()
    return doc


def _apply_result(app, doc, result):
    """Stores what the reader found on the document row."""
    doc.ocrStatus, doc.extractedFields = result['ocrStatus'], result['extractedFields']
    doc.redactedText, doc.confidence, doc.warnings = result['redactedText'], result['confidence'], result['warnings']
    doc.save()
    if doc.docType == 'AADHAAR':
        app.aadhaarLast4 = (doc.extractedFields or {}).get('aadhaarLast4', '')
        # The full number exactly as read from the card, encrypted. A new upload that shows no full number clears the old one, so it never goes stale.
        app.aadhaarNumberEnc = encrypt(result.get('aadhaarNumber') or '')
        app.save(update_fields=['aadhaarLast4', 'aadhaarNumberEnc'])
    if doc.ocrStatus == 'REJECTED':  # an unmasked Aadhaar is not kept at all
        doc.file.delete(save=False)
        doc.file = ''
        doc.save()
    return doc


def _store_document(app, doc_type, upload):
    """Saves one uploaded file, reads it with OCR and returns the SellerDocument."""
    doc = _save_upload(app, doc_type, upload)
    return _apply_result(app, doc, seller_docs.process_document(doc_type, doc.file.path, doc.mimeType))


def _geocode(address, city, pincode):
    """Latitude and longitude for the store address, from OpenStreetMap (street first, then the PIN code alone), then our built-in PIN table."""
    import requests
    for q in (f'{address}, {city}, {pincode}, India', f'{pincode}, India'):
        try:
            hits = requests.get('https://nominatim.openstreetmap.org/search', params={'q': q, 'format': 'json', 'limit': 1, 'countrycodes': 'in'},
                                headers={'User-Agent': 'AutoCart-seller-onboarding/1.0'}, timeout=3).json()
            if hits:
                return float(hits[0]['lat']), float(hits[0]['lon'])
        except Exception:
            continue
    hit = resolve_coordinates(pincode or '')
    return (hit[0], hit[1]) if hit else (None, None)


@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def seller_application_documents_view(request, pk):
    """Upload one document. It is read straight away and the details are returned."""
    user, err = _require(request)
    if err:
        return err
    app = _load(pk)
    if not app or not _owns(user, app):
        return Response({'detail': 'Application not found.'}, status=http.HTTP_404_NOT_FOUND)
    if app.status not in EDITABLE_STATES:
        return Response({'detail': 'This application can no longer be changed.'}, status=http.HTTP_409_CONFLICT)

    doc_type = str(request.data.get('docType') or '').upper()
    upload = request.FILES.get('file')
    if doc_type not in seller_docs.REQUIRED_DOC_TYPES:
        return Response({'detail': 'Unknown document type.'}, status=http.HTTP_400_BAD_REQUEST)
    if not upload:
        return Response({'detail': 'Choose a file to upload.'}, status=http.HTTP_400_BAD_REQUEST)
    check = DocumentOCRService.validate_document_upload(upload.name, upload.size, upload.content_type or '')
    if not check['valid']:
        return Response({'detail': check['error']}, status=http.HTTP_400_BAD_REQUEST)
    if doc_type in IMAGE_ONLY and not (upload.content_type or '').startswith('image/'):
        return Response({'detail': 'The store photo must be an image.'}, status=http.HTTP_400_BAD_REQUEST)

    doc = _store_document(app, doc_type, upload)
    return Response(_doc_json(doc, _is_admin(user)), status=http.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def seller_application_autofill_view(request):
    """The whole onboarding in one call: the seller uploads the Aadhaar, PAN and bank proof, we read them and fill every field
    (name, PAN, address, city, PIN, store name, bank details, map pin). Nothing is submitted; the seller reviews and can change anything."""
    user, err = _require(request)
    if err:
        return err
    app = SellerApplication.objects.filter(ownerUserId=user.id).exclude(status__in=FINAL_STATES).first()
    if not app:
        app = SellerApplication.objects.create(id=f"app-{uuid.uuid4().hex[:8]}", ownerUserId=user.id, status='DRAFT', applicantName=user.name, email=user.email.lower(),
                                               phone=user.phone or '', companyName=f"{user.name} (store not named yet)", city='Mumbai')
        _audit(app, '', 'DRAFT', 'APPLICATION_STARTED', user.email, 'Seller started an application.')
    if app.status not in EDITABLE_STATES:
        return Response({'detail': 'This application can no longer be changed.'}, status=http.HTTP_409_CONFLICT)

    uploads = {'AADHAAR': request.FILES.get('aadhaar'), 'PAN': request.FILES.get('pan'), 'BANK_PROOF': request.FILES.get('bank')}
    if not any(uploads.values()):
        return Response({'detail': 'Choose your Aadhaar, PAN card and bank proof to continue.'}, status=http.HTTP_400_BAD_REQUEST)
    problems, saved = {}, {}
    for doc_type, upload in uploads.items():
        if not upload:
            continue
        check = DocumentOCRService.validate_document_upload(upload.name, upload.size, upload.content_type or '')
        if not check['valid']:
            problems[doc_type] = check['error']
            continue
        saved[doc_type] = _save_upload(app, doc_type, upload)
    # All the files are read at the same time, which is what makes the upload fast.
    results = seller_docs.process_many({t: (d.file.path, d.mimeType) for t, d in saved.items()})
    for doc_type, doc in saved.items():
        _apply_result(app, doc, results[doc_type])
        if doc.ocrStatus == 'REJECTED':
            problems[doc_type] = (doc.warnings or ['This document could not be used.'])[0]
    docs = list(app.documents.all())
    fill = seller_docs.build_autofill(user, app, docs)
    for key, value in fill['fields'].items():
        setattr(app, key, value)
    if app.address and app.pincode:
        lat, lng = _geocode(app.address, app.city, app.pincode)
        if lat is not None:
            app.storeLatitude, app.storeLongitude = lat, lng
    ident = seller_docs.merge_identity(docs)
    app.identityDetails = ident
    app.save()
    _audit(app, app.status, app.status, 'DOCUMENTS_AUTOFILLED', user.email, f"Filled from documents: {', '.join(sorted(fill['fields'])) or 'nothing readable'}.")
    data = _profile(app, user)
    data['autofill'] = {'sources': fill['sources'], 'bank': fill['bank'], 'problems': problems, 'filled': sorted(fill['fields'])}
    return Response(data)


@api_view(['POST'])
@permission_classes([AllowAny])
def seller_application_submit_view(request, pk):
    """Finish the application. The status depends on what was uploaded and whether it matches the form."""
    user, err = _require(request)
    if err:
        return err
    app = _load(pk)
    if not app or not _owns(user, app):
        return Response({'detail': 'Application not found.'}, status=http.HTTP_404_NOT_FOUND)
    if app.status not in EDITABLE_STATES:
        return Response({'detail': 'This application was already submitted.'}, status=http.HTTP_409_CONFLICT)

    docs = list(app.documents.all())
    comparison = seller_docs.compare_application(app, docs)
    decision = seller_docs.decide_status(app, docs, comparison)
    previous = app.status
    app.status = decision['status']
    app.identityDetails = seller_docs.merge_identity(docs)
    app.verificationResults = comparison
    app.riskScore, app.riskCategory = comparison['riskScore'], comparison['riskCategory']
    app.missingFields = decision['missing']
    app.aiAssessment = f"{decision['reason']} Automatic risk score {comparison['riskScore']}/100. A person makes the final decision."
    app.save()
    _audit(app, previous, app.status, 'APPLICATION_SUBMITTED', user.email, decision['reason'])
    return Response(_profile(app, user))


@api_view(['GET'])
@permission_classes([AllowAny])
def seller_document_file_view(request, pk, doc_id):
    """Streams a private document to the applicant or an admin. Never public."""
    user, err = _require(request)
    if err:
        return err
    app = _load(pk)
    doc = SellerDocument.objects.filter(id=doc_id, application_id=pk).first()
    if not app or not doc or not doc.file or not (_is_admin(user) or _owns(user, app)):
        return Response({'detail': 'File not found.'}, status=http.HTTP_404_NOT_FOUND)
    return FileResponse(doc.file.open('rb'), filename=doc.fileName, content_type=doc.mimeType or 'application/octet-stream')


ACTIONS = {
    # action: (new status, allowed from, reason required)
    'APPROVE': ('APPROVED', ('PENDING_ADMIN_APPROVAL', 'NEEDS_MANUAL_REVIEW'), False),
    'REJECT': ('REJECTED', ('PENDING_ADMIN_APPROVAL', 'NEEDS_MANUAL_REVIEW', 'NEEDS_MORE_INFORMATION'), True),
    'REQUEST_INFO': ('NEEDS_MORE_INFORMATION', ('PENDING_ADMIN_APPROVAL', 'NEEDS_MANUAL_REVIEW'), True),
    'SUSPEND': ('SUSPENDED', ('APPROVED',), True),
}


def _activate_seller(app, admin_email):
    """Creates the Seller and the Store (so it shows on the nearby-store map) and upgrades the applicant's role."""
    today = datetime.date.today().isoformat()
    seller, _ = Seller.objects.update_or_create(
        id=f"sel-{app.id}",
        defaults={'name': app.applicantName, 'companyName': app.companyName, 'email': app.email, 'phone': app.phone,
                  'productsCount': len(app.plannedProducts or []), 'status': 'Approved', 'joinedDate': today, 'city': app.city},
    )
    lat, lng = app.storeLatitude, app.storeLongitude
    if lat is None or lng is None:
        found = resolve_coordinates(app.pincode) or resolve_coordinates(app.city)
        lat, lng = (found[0], found[1]) if found else (19.076, 72.8777)
    Store.objects.update_or_create(
        id=f"store-{app.id}",
        defaults={'name': app.storeName or app.companyName, 'seller': app.companyName, 'sellerId': seller.id, 'address': app.address,
                  'city': app.city or 'Mumbai', 'state': app.addressState, 'pincode': app.pincode, 'latitude': lat, 'longitude': lng,
                  'phone': app.phone, 'email': app.email, 'operatingStatus': 'Open', 'fulfillmentCapability': 'Pickup and Delivery'},
    )
    # The products the seller listed while applying go live with the stock and photo they gave, so the dashboard starts full.
    from django.utils.text import slugify
    for item in app.plannedProducts or []:
        price = float(item.get('approxPrice') or 0)
        name = str(item.get('name') or '').strip()
        if not name or price <= 0 or Product.objects.filter(seller=app.companyName, name=name).exists():
            continue
        pid = f"prod-{uuid.uuid4().hex[:8]}"
        stock = int(item.get('stock') or 0)
        Product.objects.create(
            id=pid, name=name, slug=f"{slugify(name)[:200]}-{pid[-4:]}", category=item.get('category') or (app.productCategories or ['Home & Kitchen'])[0],
            price=price, originalPrice=0, discount=0, stock=stock, stockStatus='Out of Stock' if stock <= 0 else ('Low Stock' if stock <= 10 else 'In Stock'),
            images=[item['image']] if item.get('image') else [], seller=app.companyName, createdAt=today, newArrival=True)
    Seller.objects.filter(id=seller.id).update(productsCount=Product.objects.filter(seller=app.companyName).count())
    owner = User.objects.filter(id=app.ownerUserId).first()
    if owner and owner.role == 'CUSTOMER':
        owner.role = 'SELLER'
        owner.save(update_fields=['role'])
    app.sellerId = seller.id
    app.reviewedBy = admin_email


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_seller_application_action_view(request, pk):
    """Admin decision on an application: APPROVE, REJECT, REQUEST_INFO or SUSPEND."""
    user, err = _require(request, ADMIN_ROLES)
    if err:
        return err
    app = _load(pk)
    if not app:
        return Response({'detail': 'Application not found.'}, status=http.HTTP_404_NOT_FOUND)

    action = str(request.data.get('action') or '').upper()
    reason = str(request.data.get('reason') or '').strip()
    if action not in ACTIONS:
        return Response({'detail': f"Unknown action. Use one of: {', '.join(ACTIONS)}."}, status=http.HTTP_400_BAD_REQUEST)
    new_status, allowed_from, needs_reason = ACTIONS[action]
    if app.status not in allowed_from:
        return Response({'detail': f"You can't {action.replace('_', ' ').lower()} an application that is {app.status.replace('_', ' ').lower()}."},
                        status=http.HTTP_400_BAD_REQUEST)
    if needs_reason and not reason:
        return Response({'detail': 'Write a reason. The applicant will see it.', 'errors': {'reason': 'Required'}},
                        status=http.HTTP_400_BAD_REQUEST)

    if action == 'APPROVE':  # never go live without the identity documents and a store location
        have = set(app.documents.values_list('docType', flat=True))
        gaps = [name for key, name in (('AADHAAR', 'Aadhaar'), ('PAN', 'PAN card')) if key not in have]
        if app.storeLatitude is None or app.storeLongitude is None:
            gaps.append('a store location on the map')
        if gaps:
            return Response({'detail': f"Cannot approve yet. Missing: {', '.join(gaps)}. Ask the seller for them."}, status=http.HTTP_400_BAD_REQUEST)

    previous = app.status
    app.status = new_status
    if action == 'APPROVE':
        app.rejectionReason = ''
        _activate_seller(app, user.email)
    elif action == 'REJECT':
        app.rejectionReason, app.reviewedBy = reason, user.email
    elif action == 'REQUEST_INFO':
        app.adminNotes, app.reviewedBy = reason, user.email
    elif action == 'SUSPEND':
        app.rejectionReason, app.reviewedBy = reason, user.email
        Seller.objects.filter(id=app.sellerId).update(status='Suspended')
        Store.objects.filter(sellerId=app.sellerId).update(operatingStatus='Closed')
    app.save()
    _audit(app, previous, new_status, action, user.email, reason)
    if request.data.get('auto'):   # the admin used the application autopilot: keep a visible record of what it did
        from .automation import record
        record('admin', user.id, {'APPROVE': 'auto_approve', 'REQUEST_INFO': 'auto_reminder'}.get(action, 'auto_' + action.lower()),
               f"{app.companyName or app.applicantName}: {'approved' if action == 'APPROVE' else 'reminder sent' if action == 'REQUEST_INFO' else action.lower()} by autopilot.", app.id)
    return Response({'success': True, 'applicationId': app.id, 'previousStatus': previous, 'currentStatus': new_status,
                     'profile': _profile(app, user)})


@api_view(['POST'])
@permission_classes([AllowAny])
def admin_seller_aadhaar_reveal_view(request, pk):
    """Admin only: the full Aadhaar number of an application. POST (never cached or prefetched) and every use is written to the audit trail."""
    user, err = _require(request, ADMIN_ROLES)
    if err:
        return err
    app = _load(pk)
    number = decrypt(app.aadhaarNumberEnc) if app else ''
    if not number:
        return Response({'detail': 'No full Aadhaar number is stored for this application.'}, status=http.HTTP_404_NOT_FOUND)
    _audit(app, app.status, app.status, 'AADHAAR_REVEALED', user.email, 'Admin viewed the full Aadhaar number.')
    return Response({'aadhaarNumber': f'{number[:4]} {number[4:8]} {number[8:]}', 'masked': f'XXXX-XXXX-{number[-4:]}'})


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_seller_detail_view(request, seller_id):
    """One seller in full for the admin: contact, live numbers worked out from real orders, and the onboarding application with its documents."""
    from .models import Order
    from .seller_analytics import analytics
    user, err = _require(request, ADMIN_ROLES)
    if err:
        return err
    seller = Seller.objects.filter(id=seller_id).first()
    if not seller:
        return Response({'detail': 'Seller not found.'}, status=http.HTTP_404_NOT_FOUND)
    app = SellerApplication.objects.filter(sellerId=seller.id).first() or SellerApplication.objects.filter(companyName=seller.companyName or seller.name).first()
    products = list(Product.objects.filter(seller__in=[x for x in (seller.companyName, seller.name) if x]))
    ids = {p.id for p in products}
    orders = [o for o in Order.objects.exclude(status='Cancelled') if any(str(i.get('id')) in ids for i in (o.items or []))]
    earn = analytics(products)['earnings'] if products else {'gross': 0, 'commission': 0, 'youKeep': 0}
    sold = {}  # units sold per product, from real orders
    for o in orders:
        for i in o.items or []:
            if str(i.get('id')) in ids:
                sold[str(i.get('id'))] = sold.get(str(i.get('id')), 0) + int(i.get('quantity') or 0)
    return Response({
        'seller': {'id': seller.id, 'name': seller.name, 'companyName': seller.companyName, 'email': seller.email, 'phone': seller.phone,
                   'city': seller.city, 'status': seller.status, 'joinedDate': seller.joinedDate, 'rating': seller.rating},
        'live': {'products': len(products), 'orders': len(orders), 'revenue': earn['gross'], 'commission': earn['commission'],
                 'lowStock': sum(1 for p in products if 0 < p.stock <= 10), 'outOfStock': sum(1 for p in products if p.stock <= 0),
                 'inStock': sum(1 for p in products if p.stock > 10), 'units': sum(sold.values()), 'stockUnits': sum(max(p.stock, 0) for p in products)},
        'products': [{'id': p.id, 'name': p.name, 'category': p.category, 'price': p.price, 'stock': p.stock,
                      'status': 'Out of stock' if p.stock <= 0 else ('Low stock' if p.stock <= 10 else 'In stock'),
                      'sold': sold.get(p.id, 0), 'image': (p.images or [''])[0] if isinstance(p.images, list) else ''} for p in products[:500]],
        'application': _profile(app, user) if app else None,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
@parser_classes([MultiPartParser, FormParser])
def seller_application_product_image_view(request, pk):
    """An applicant uploads a photo for one of their planned products. Returns the public URL to store on the product."""
    from .product_images import save_photo
    user, err = _require(request)
    if err:
        return err
    app = _load(pk)
    if not app or not _owns(user, app):
        return Response({'detail': 'Application not found.'}, status=http.HTTP_404_NOT_FOUND)
    photo = request.FILES.get('image')
    if not photo:
        return Response({'detail': 'Choose a photo first.'}, status=http.HTTP_400_BAD_REQUEST)
    url, problem = save_photo(photo, request)
    if problem:
        return Response({'detail': problem}, status=http.HTTP_400_BAD_REQUEST)
    return Response({'url': url})


# City centres (public coordinates): the map pin for a seller that has no store of its own yet.
CITY_CENTRES = {
    'Mumbai': (19.0760, 72.8777, 'Maharashtra'), 'Bengaluru': (12.9716, 77.5946, 'Karnataka'), 'New Delhi': (28.6139, 77.2090, 'Delhi'),
    'Pune': (18.5204, 73.8567, 'Maharashtra'), 'Gurugram': (28.4595, 77.0266, 'Haryana'), 'Surat': (21.1702, 72.8311, 'Gujarat'),
    'Kolkata': (22.5726, 88.3639, 'West Bengal'), 'Jaipur': (26.9124, 75.7873, 'Rajasthan'), 'Chandigarh': (30.7333, 76.7794, 'Chandigarh'),
    'Hyderabad': (17.3850, 78.4867, 'Telangana'), 'Dehradun': (30.3165, 78.0322, 'Uttarakhand'),
}


# Mumbai localities used to spread Mumbai sellers across the map when a seller has no exact store pin yet.
MUMBAI_AREAS = [
    ('Bandra West', 19.0596, 72.8295), ('Andheri West', 19.1364, 72.8296), ('Powai', 19.1176, 72.9060), ('Borivali West', 19.2307, 72.8567),
    ('Lower Parel', 18.9938, 72.8258), ('Colaba', 18.9067, 72.8147), ('Dadar', 19.0178, 72.8478), ('Juhu', 19.1075, 72.8263),
    ('Malad West', 19.1874, 72.8484), ('Goregaon East', 19.1663, 72.8526), ('Kurla', 19.0726, 72.8845), ('Ghatkopar', 19.0860, 72.9081),
    ('Mulund West', 19.1726, 72.9425), ('Chembur', 19.0522, 72.9005), ('Worli', 19.0176, 72.8179), ('Vile Parle', 19.0990, 72.8446),
    ('Byculla', 18.9780, 72.8335),
]


def mumbai_area_for(seller_id):
    """A stable Mumbai locality for a seller (same seller, same area, every time)."""
    return MUMBAI_AREAS[sum(ord(c) for c in str(seller_id)) % len(MUMBAI_AREAS)]


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_sellers_overview_view(request):
    """Every seller in one table for the admin: contact, store location and live numbers worked out from real products and orders."""
    from .models import Order
    user, err = _require(request, ADMIN_ROLES)
    if err:
        return err
    orders = [o for o in Order.objects.exclude(status='Cancelled')]
    rows = []
    for seller in Seller.objects.all():
        company = seller.companyName or seller.name
        names = {n for n in (company, seller.name) if n}  # products are filed under the trading name or the legal name
        app = SellerApplication.objects.filter(sellerId=seller.id).first() or SellerApplication.objects.filter(companyName__in=names, status='APPROVED').first()
        store = Store.objects.filter(sellerId=seller.id).exclude(latitude=0).first() or Store.objects.filter(seller__in=names).exclude(latitude=0).first()
        products = list(Product.objects.filter(seller__in=names))
        ids = {p.id for p in products}
        units = revenue = to_pack = 0
        for o in orders:
            mine = [i for i in (o.items or []) if str(i.get('id')) in ids]
            if mine:
                units += sum(int(i.get('quantity') or 0) for i in mine)
                revenue += sum(float(i.get('price') or 0) * int(i.get('quantity') or 0) for i in mine)
                to_pack += 1 if o.status in ('Confirmed', 'Processing', 'Pending', 'Order Placed') else 0
        lat = (app.storeLatitude if app and app.storeLatitude else None) or (store.latitude if store and store.latitude else None)
        lng = (app.storeLongitude if app and app.storeLongitude else None) or (store.longitude if store and store.longitude else None)
        approx = False
        if lat is None and seller.city == 'Mumbai':  # no exact store: a stable Mumbai locality, flagged as approximate
            _area, lat, lng = mumbai_area_for(seller.id)
            approx = True
        elif lat is None and seller.city in CITY_CENTRES:  # no exact store: show the city centre and say so
            lat, lng, _state = CITY_CENTRES[seller.city]
            approx = True
        rows.append({
            'id': seller.id, 'name': seller.name, 'companyName': company, 'status': seller.status, 'email': seller.email or (app.email if app else ''),
            'phone': seller.phone or (app.phone if app else '') or (store.phone if store else ''), 'city': seller.city or (store.city if store else ''),
            'address': (app.address if app else '') or (store.address if store else ''), 'lat': lat, 'lng': lng, 'approxLocation': approx,
            'products': len(products), 'unitsSold': units, 'revenue': round(revenue), 'ordersToPack': to_pack,
            'lowStock': sum(1 for p in products if 0 < p.stock <= 10), 'outOfStock': sum(1 for p in products if p.stock <= 0), 'joined': seller.joinedDate,
        })
    rows.sort(key=lambda r: -r['revenue'])
    return Response({
        'sellers': rows,
        'totals': {'sellers': len(rows), 'products': sum(r['products'] for r in rows), 'revenue': sum(r['revenue'] for r in rows), 'ordersToPack': sum(r['ordersToPack'] for r in rows),
                   'pendingApplications': SellerApplication.objects.filter(status__in=['PENDING_ADMIN_APPROVAL', 'NEEDS_MANUAL_REVIEW']).count(),
                   'stillFilling': SellerApplication.objects.filter(status='DRAFT').count()},
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_seller_report_view(request):
    """Seller report for the admin: sales, commission, delivery record, stock health and a 30-day trend per seller, all from real orders."""
    import datetime
    from django.utils import timezone
    from .commission import fee_for
    from .models import Order
    user, err = _require(request, ADMIN_ROLES)
    if err:
        return err
    today = timezone.localdate()
    days = [today - datetime.timedelta(days=i) for i in range(29, -1, -1)]
    orders = list(Order.objects.all())
    out = []
    for seller in Seller.objects.all():
        names = {n for n in (seller.companyName, seller.name) if n}
        products = list(Product.objects.filter(seller__in=names))
        by_id = {p.id: p for p in products}
        revenue = fees = units = 0.0
        n_orders = delivered = cancelled = 0
        trend = {d: 0.0 for d in days}
        per_product = {}
        for o in orders:
            mine = [i for i in (o.items or []) if str(i.get('id')) in by_id]
            if not mine:
                continue
            if o.status == 'Cancelled':
                cancelled += 1
                continue
            n_orders += 1
            delivered += 1 if o.status == 'Delivered' else 0
            try:
                day = datetime.date.fromisoformat(str(o.date)[:10])
            except ValueError:
                day = None
            for i in mine:
                q = int(i.get('quantity') or 0)
                amount = float(i.get('price') or 0) * q
                revenue += amount
                units += q
                fees += fee_for(by_id[str(i.get('id'))].category, amount)
                per_product[i.get('name')] = per_product.get(i.get('name'), 0) + amount
                if day in trend:
                    trend[day] += amount
        top = max(per_product.items(), key=lambda kv: kv[1]) if per_product else None
        out.append({
            'id': seller.id, 'name': seller.name, 'companyName': seller.companyName or seller.name, 'city': seller.city, 'status': seller.status,
            'products': len(products), 'orders': n_orders, 'units': int(units), 'revenue': round(revenue), 'commission': round(fees), 'youKeep': round(revenue - fees),
            'avgOrder': round(revenue / n_orders) if n_orders else 0, 'deliveredPercent': round(100 * delivered / n_orders) if n_orders else None,
            'cancelled': cancelled, 'lowStock': sum(1 for x in products if 0 < x.stock <= 10), 'outOfStock': sum(1 for x in products if x.stock <= 0),
            'topProduct': top[0] if top else '', 'trend': [round(trend[d]) for d in days],
        })
    out.sort(key=lambda r: -r['revenue'])
    total = sum(r['revenue'] for r in out)
    selling = [r for r in out if r['orders']]
    insights = []
    if selling and total:
        lead = selling[0]
        share = round(100 * lead['revenue'] / total)
        insights.append({'level': 'warn' if share >= 70 else 'info', 'text': f"{lead['name']} brings in {share}% of all seller sales{' - the marketplace leans heavily on one seller.' if share >= 70 else '.'}"})
    quiet = [r for r in out if r['status'] == 'Approved' and not r['orders']]
    if quiet:
        insights.append({'level': 'info', 'text': f"{len(quiet)} approved seller{'s have' if len(quiet) > 1 else ' has'} no orders yet: {', '.join(r['name'] for r in quiet[:3])}{'...' if len(quiet) > 3 else ''}."})
    slow = [r for r in selling if r['deliveredPercent'] is not None and r['deliveredPercent'] < 50 and r['orders'] >= 2]
    if slow:
        insights.append({'level': 'warn', 'text': f"Fewer than half of orders are delivered for {', '.join(r['name'] for r in slow[:3])}. Worth a check."})
    stock = [r for r in out if r['outOfStock']]
    if stock:
        insights.append({'level': 'info', 'text': f"{sum(r['outOfStock'] for r in stock)} products are out of stock across {len(stock)} seller{'s' if len(stock) > 1 else ''}."})
    return Response({
        'days': [d.strftime('%d %b') for d in days], 'sellers': out, 'insights': insights,
        'totals': {'revenue': total, 'commission': sum(r['commission'] for r in out), 'orders': sum(r['orders'] for r in out), 'sellersWithSales': len(selling), 'sellers': len(out)},
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_triage_view(request):
    """Autopilot triage: reads every application waiting for a decision and recommends what to do. It never decides: the admin confirms."""
    from . import triage
    user, err = _require(request, ADMIN_ROLES)
    if err:
        return err
    return Response(triage.triage_all())
