"""
Seller onboarding, permissions and security tests.
Document reading is replaced with fixed text so nothing here needs the OCR engine or the network.
"""

import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from api.models import Seller, SellerApplication, Store, User
from api.views import generate_token

TMP_MEDIA = tempfile.mkdtemp()

TEXTS = {
    'aadhaar': 'Government of India\nRahul Sharma\nDOB: 14/03/1991\nMALE\nXXXX XXXX 4821\nAddress: 12 Hill Road Andheri East Mumbai 400069',
    'aadhaar_full': 'Government of India\nRahul Sharma\nDOB: 14/03/1991\nMALE\n2345 6789 4821',
    'pan': 'INCOME TAX DEPARTMENT\nABCDE1234F\nName\nRahul Sharma\nFather\'s Name\nMohan Sharma\nDate of Birth\n14/03/1991',
    'pan_other': 'INCOME TAX DEPARTMENT\nZZZZZ9999Z\nName\nPriya Nair\nFather\'s Name\nSuresh Nair\nDate of Birth\n02/02/1990',
    'gst': 'GSTIN: 27ABCDE1234F1Z5\nLegal Name: Sharma Electronics',
    'addr': 'Sharma Electronics 12 Hill Road Andheri East Mumbai 400069',
    'bank': 'IFSC: HDFC0001234 A/c No 123456789012',
}


def fake_read_text(path, mime=''):
    name = path.replace('\\', '/').split('/')[-1].lower()
    for key in ('aadhaar_full', 'aadhaar', 'pan_other', 'pan', 'gst', 'addr', 'bank'):
        if key in name:
            return {'status': 'DONE', 'text': TEXTS[key]}
    return {'status': 'UNREADABLE', 'text': ''}


FORM = dict(
    companyName='Sharma Electronics', contactName='Rahul Sharma', email='shop@sharma.example', phone='9820012345',
    gstin='27ABCDE1234F1Z5', pan='ABCDE1234F', address='12 Hill Road, Andheri East', city='Mumbai', state='Maharashtra',
    pincode='400069', storeLatitude=19.1136, storeLongitude=72.8697, productCategories=['Electronics'],
    plannedProducts=[{'name': 'Wireless Mouse', 'category': 'Electronics', 'approxPrice': 999}],
)


def upload(client, app_id, doc_type, file_name):
    return client.post(
        f'/api/seller/applications/{app_id}/documents',
        {'docType': doc_type, 'file': SimpleUploadedFile(file_name, b'fake-image-bytes', content_type='image/png')},
        format='multipart',
    )


@override_settings(MEDIA_ROOT=TMP_MEDIA)
class SellerOnboardingTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.customer = User.objects.create_user(email='buyer@example.com', name='Rahul Sharma', password='pw-12345', role='CUSTOMER')
        self.other = User.objects.create_user(email='other@example.com', name='Other Person', password='pw-12345', role='CUSTOMER')
        self.admin = User.objects.create_user(email='boss@example.com', name='Admin', password='pw-12345', role='ADMIN')
        self.guest, self.c, self.o, self.a = APIClient(), APIClient(), APIClient(), APIClient()
        self.c.credentials(HTTP_AUTHORIZATION='Bearer ' + generate_token(self.customer))
        self.o.credentials(HTTP_AUTHORIZATION='Bearer ' + generate_token(self.other))
        self.a.credentials(HTTP_AUTHORIZATION='Bearer ' + generate_token(self.admin))
        patcher = patch('api.seller_docs.read_text', side_effect=fake_read_text)
        patcher.start()
        self.addCleanup(patcher.stop)

    # -- helpers --
    def start(self, **over):
        res = self.c.post('/api/seller/applications', {**FORM, **over}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        return res.json()['id']

    def upload_all(self, app_id, pan_file='pan.png'):
        for t, f in (('AADHAAR', 'aadhaar.png'), ('PAN', pan_file), ('GST_CERTIFICATE', 'gst.png'),
                     ('ADDRESS_PROOF', 'addr.png'), ('BANK_PROOF', 'bank.png'), ('STORE_PHOTO', 'shop.jpg')):
            self.assertEqual(upload(self.c, app_id, t, f).status_code, 201)

    # -- who can see what --
    def test_guest_cannot_list_or_apply(self):
        self.assertEqual(self.guest.get('/api/seller/applications').status_code, 401)
        self.assertEqual(self.guest.post('/api/seller/applications', FORM, format='json').status_code, 401)

    def test_customer_sees_only_their_own_application(self):
        app_id = self.start()
        self.assertEqual(len(self.c.get('/api/seller/applications').json()), 1)
        self.assertEqual(self.o.get('/api/seller/applications').json(), [])
        self.assertEqual(self.o.get(f'/api/seller/applications/{app_id}').status_code, 404)
        self.assertEqual(len(self.a.get('/api/seller/applications').json()), 1)

    def test_customer_cannot_take_admin_actions(self):
        app_id = self.start()
        res = self.c.post(f'/api/admin/seller-applications/{app_id}/action', {'action': 'APPROVE'}, format='json')
        self.assertEqual(res.status_code, 403)

    def test_bad_form_is_rejected_with_field_errors(self):
        res = self.c.post('/api/seller/applications', {**FORM, 'pan': '123', 'storeLatitude': None}, format='json')
        self.assertEqual(res.status_code, 400)
        self.assertIn('pan', res.json()['errors'])
        self.assertIn('location', res.json()['errors'])

    # -- documents and Aadhaar privacy --
    def test_masked_aadhaar_stores_only_last_four_digits(self):
        app_id = self.start()
        res = upload(self.c, app_id, 'AADHAAR', 'aadhaar.png').json()
        self.assertEqual(res['ocrStatus'], 'DONE')
        self.assertEqual(res['extractedFields']['aadhaarMasked'], 'XXXX-XXXX-4821')
        self.assertEqual(SellerApplication.objects.get(id=app_id).aadhaarLast4, '4821')
        self.assertNotIn('2345', str(res))

    def test_unmasked_aadhaar_is_rejected_and_nothing_is_kept(self):
        app_id = self.start()
        res = upload(self.c, app_id, 'AADHAAR', 'aadhaar_full.png').json()
        self.assertEqual(res['ocrStatus'], 'REJECTED')
        self.assertEqual(res['extractedFields'], {})
        doc = SellerApplication.objects.get(id=app_id).documents.get(docType='AADHAAR')
        self.assertFalse(doc.file)
        self.assertNotIn('4821', doc.redactedText)
        self.assertNotIn('6789', doc.redactedText)

    def test_files_are_private(self):
        app_id = self.start()
        doc_id = upload(self.c, app_id, 'PAN', 'pan.png').json()['id']
        url = f'/api/seller/applications/{app_id}/documents/{doc_id}/file'
        self.assertEqual(self.guest.get(url).status_code, 401)
        self.assertEqual(self.o.get(url).status_code, 404)
        self.assertEqual(self.c.get(url).status_code, 200)
        self.assertEqual(self.a.get(url).status_code, 200)

    # -- submit decides the status --
    def test_missing_documents_need_more_information(self):
        app_id = self.start()
        upload(self.c, app_id, 'PAN', 'pan.png')
        res = self.c.post(f'/api/seller/applications/{app_id}/submit').json()
        self.assertEqual(res['status'], 'NEEDS_MORE_INFORMATION')
        self.assertIn('AADHAAR', res['missingDocuments'])

    def test_pan_mismatch_goes_to_manual_review(self):
        app_id = self.start()
        self.upload_all(app_id, pan_file='pan_other.png')
        res = self.c.post(f'/api/seller/applications/{app_id}/submit').json()
        self.assertEqual(res['status'], 'NEEDS_MANUAL_REVIEW')
        self.assertGreater(res['comparison']['mismatches'], 0)

    def test_complete_matching_application_waits_for_admin(self):
        app_id = self.start()
        self.upload_all(app_id)
        res = self.c.post(f'/api/seller/applications/{app_id}/submit').json()
        self.assertEqual(res['status'], 'PENDING_ADMIN_APPROVAL')
        self.assertEqual(res['comparison']['mismatches'], 0)

    # -- profile and decisions --
    def test_profile_has_location_products_and_masked_identity(self):
        app_id = self.start()
        self.upload_all(app_id)
        self.c.post(f'/api/seller/applications/{app_id}/submit')
        p = self.a.get(f'/api/seller/applications/{app_id}').json()
        self.assertEqual(p['store']['latitude'], 19.1136)
        self.assertEqual(p['plannedProducts'][0]['name'], 'Wireless Mouse')
        self.assertEqual(p['identity']['aadhaarMasked'], 'XXXX-XXXX-4821')
        self.assertEqual(p['identity']['pan'], 'ABCDE1234F')
        self.assertEqual(len(p['documents']), 6)

    def test_approval_creates_seller_store_and_role(self):
        app_id = self.start()
        self.upload_all(app_id)
        self.c.post(f'/api/seller/applications/{app_id}/submit')
        res = self.a.post(f'/api/admin/seller-applications/{app_id}/action', {'action': 'APPROVE'}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()['currentStatus'], 'APPROVED')
        self.assertTrue(Seller.objects.filter(id=f'sel-{app_id}', status='Approved').exists())
        store = Store.objects.get(id=f'store-{app_id}')
        self.assertAlmostEqual(store.latitude, 19.1136)
        self.customer.refresh_from_db()
        self.assertEqual(self.customer.role, 'SELLER')

    def test_reject_needs_a_reason_and_shows_it_to_the_seller(self):
        app_id = self.start()
        self.upload_all(app_id)
        self.c.post(f'/api/seller/applications/{app_id}/submit')
        url = f'/api/admin/seller-applications/{app_id}/action'
        self.assertEqual(self.a.post(url, {'action': 'REJECT'}, format='json').status_code, 400)
        self.assertEqual(self.a.post(url, {'action': 'REJECT', 'reason': 'GST certificate is expired.'}, format='json').status_code, 200)
        mine = self.c.get(f'/api/seller/applications/{app_id}').json()
        self.assertEqual(mine['status'], 'REJECTED')
        self.assertEqual(mine['rejectionReason'], 'GST certificate is expired.')
        self.assertFalse(Store.objects.filter(id=f'store-{app_id}').exists())

    def test_cannot_approve_an_application_that_is_not_ready(self):
        app_id = self.start()  # still a draft
        res = self.a.post(f'/api/admin/seller-applications/{app_id}/action', {'action': 'APPROVE'}, format='json')
        self.assertEqual(res.status_code, 400)


class SecurityTests(TestCase):
    def setUp(self):
        self.customer = User.objects.create_user(email='buyer@example.com', name='Buyer', password='secret-pass', role='CUSTOMER')
        self.nopass = User.objects.create_user(email='nopass@example.com', name='No Password', role='CUSTOMER')
        self.admin = User.objects.create_user(email='boss@example.com', name='Boss', password='boss-pass', role='ADMIN')
        self.client = APIClient()

    def login(self, email, password):
        return self.client.post('/api/auth/login', {'email': email, 'password': password}, format='json')

    def test_no_master_password(self):
        self.assertEqual(self.login('buyer@example.com', 'admin123').status_code, 401)
        self.assertEqual(self.login('buyer@example.com', 'password').status_code, 401)
        self.assertEqual(self.login('nopass@example.com', 'anything').status_code, 401)
        self.assertEqual(self.login('buyer@example.com', 'secret-pass').status_code, 200)

    def test_admin_only_endpoints(self):
        token = self.login('buyer@example.com', 'secret-pass').json()['token']
        for url in ('/api/users', '/api/admin/stats', '/api/coupons'):
            self.assertEqual(self.client.get(url).status_code, 403, url)
            self.assertEqual(self.client.get(url, HTTP_AUTHORIZATION=f'Bearer {token}').status_code, 403, url)
        admin_token = self.login('boss@example.com', 'boss-pass').json()['token']
        self.assertEqual(self.client.get('/api/users', HTTP_AUTHORIZATION=f'Bearer {admin_token}').status_code, 200)

    def test_catalogue_is_read_only_for_customers(self):
        token = self.login('buyer@example.com', 'secret-pass').json()['token']
        self.assertEqual(self.client.get('/api/products').status_code, 200)
        res = self.client.post('/api/products', {'id': 'x', 'name': 'x', 'slug': 'x'}, format='json', HTTP_AUTHORIZATION=f'Bearer {token}')
        self.assertEqual(res.status_code, 403)

    def test_orders_are_private(self):
        from api.models import Order
        Order.objects.create(id='ORD-1', customerName='Buyer', customerEmail='buyer@example.com')
        Order.objects.create(id='ORD-2', customerName='Someone', customerEmail='someone@example.com')
        self.assertEqual(self.client.get('/api/orders').status_code, 401)
        token = self.login('buyer@example.com', 'secret-pass').json()['token']
        auth = {'HTTP_AUTHORIZATION': f'Bearer {token}'}
        ids = [o['id'] for o in self.client.get('/api/orders', {'email': 'someone@example.com'}, **auth).json()]
        self.assertEqual(ids, ['ORD-1'])  # asking for someone else's email changes nothing
        self.assertEqual(self.client.get('/api/orders/ORD-2', **auth).status_code, 404)
        self.assertEqual(self.client.delete('/api/orders/ORD-1', **auth).status_code, 403)
