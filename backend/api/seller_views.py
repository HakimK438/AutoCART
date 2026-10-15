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
    if not re.fullmatch(GSTIN_REGEX, get('gstin').upper()):
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
    products = data.get('plannedProducts') or []
    if not isinstance(products, list) or not [p for p in products if str(p.get('name', '')).strip()]:
        errors['plannedProducts'] = 'Add at least one product you plan to sell.'
    return errors


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
        'phone': str(data['phone']).strip(), 'gstin': str(data['gstin']).strip().upper(), 'pan': str(data['pan']).strip().upper(),
        'businessType': str(data.get('businessType') or 'Retailer'), 'address': str(data['address']).strip(),
        'city': str(data.get('city') or '').strip(), 'addressState': str(data.get('state') or '').strip(),
        'pincode': str(data['pincode']).strip(), 'storeLatitude': float(data['storeLatitude']),
        'storeLongitude': float(data['storeLongitude']), 'productCategories': data.get('productCategories') or [],
        'plannedProducts': [
            {'name': str(p.get('name')).strip(), 'category': str(p.get('category') or '').strip(), 'approxPrice': p.get('approxPrice') or 0}
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

    for old in app.documents.filter(docType=doc_type):  # one file per type: a new upload replaces the old one
        old.file.delete(save=False)
        old.delete()
    doc = SellerDocument(id=f"doc-{uuid.uuid4().hex[:8]}", application=app, docType=doc_type, fileName=upload.name[:255],
                         mimeType=upload.content_type or '', sizeBytes=upload.size)
    doc.file.save(upload.name, upload, save=False)
    doc.save()

    result = seller_docs.process_document(doc_type, doc.file.path, doc.mimeType)
    doc.ocrStatus, doc.extractedFields = result['ocrStatus'], result['extractedFields']
    doc.redactedText, doc.confidence, doc.warnings = result['redactedText'], result['confidence'], result['warnings']
    doc.save()

    if doc_type == 'AADHAAR':
        app.aadhaarLast4 = (doc.extractedFields or {}).get('aadhaarLast4', '')
        app.save(update_fields=['aadhaarLast4'])
    if doc.ocrStatus == 'REJECTED':  # an unmasked Aadhaar is not kept at all
        doc.file.delete(save=False)
        doc.file = ''
        doc.save()
    return Response(_doc_json(doc, _is_admin(user)), status=http.HTTP_201_CREATED)


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
    return Response({'success': True, 'applicationId': app.id, 'previousStatus': previous, 'currentStatus': new_status,
                     'profile': _profile(app, user)})
