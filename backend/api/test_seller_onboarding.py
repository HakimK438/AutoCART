"""
Seller onboarding, permissions and security tests.
Document reading is replaced with fixed text so nothing here needs the OCR engine or the network.
"""

import shutil
import tempfile
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from types import SimpleNamespace

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from api import secure_fields, seller_docs
from api.models import Seller, SellerApplication, Store, User
from api.views import generate_token

TMP_MEDIA = tempfile.mkdtemp()


def with_check_digit(first11: str) -> str:
    """An Aadhaar-shaped number whose last digit makes it pass the Verhoeff checksum (the test's own copy of the algorithm)."""
    inverse, c = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9], 0
    for i, ch in enumerate(reversed(first11)):
        c = seller_docs._VERHOEFF_D[c][seller_docs._VERHOEFF_P[(i + 1) % 8][int(ch)]]
    return first11 + str(inverse[c])


VALID_AADHAAR = with_check_digit('23456789012')

TEXTS = {
    'aadhaar': 'Government of India\nRahul Sharma\nDOB: 14/03/1991\nMALE\nXXXX XXXX 4821\nAddress: 12 Hill Road Andheri East Mumbai 400069',
    'aadhaar_full': 'Government of India\nRahul Sharma\nDOB: 14/03/1991\nMALE\n2345 6789 4821',  # fails the checksum on purpose: still stored as displayed
    'aadhaar_valid': f'Government of India\nRahul Sharma\nDOB: 14/03/1991\nMALE\n{VALID_AADHAAR[:4]} {VALID_AADHAAR[4:8]} {VALID_AADHAAR[8:]}',
    'pan': 'INCOME TAX DEPARTMENT\nABCDE1234F\nName\nRahul Sharma\nFather\'s Name\nMohan Sharma\nDate of Birth\n14/03/1991',
    'pan_other': 'INCOME TAX DEPARTMENT\nZZZZZ9999Z\nName\nPriya Nair\nFather\'s Name\nSuresh Nair\nDate of Birth\n02/02/1990',
    'gst': 'GSTIN: 27ABCDE1234F1Z5\nLegal Name: Sharma Electronics',
    'addr': 'Sharma Electronics 12 Hill Road Andheri East Mumbai 400069',
    'bank': 'HDFC Bank\nAccount Holder Name: Rahul Sharma\nIFSC: HDFC0001234 A/c No 123456789012',
}


def fake_read_text(path, mime=''):
    name = path.replace('\\', '/').split('/')[-1].lower()
    for key in ('aadhaar_full', 'aadhaar_valid', 'aadhaar', 'pan_other', 'pan', 'gst', 'addr', 'bank'):
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
        for t, f in (('AADHAAR', 'aadhaar.png'), ('PAN', pan_file), ('BANK_PROOF', 'bank.png')):
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

    def test_three_documents_fill_the_whole_application(self):
        files = {k: SimpleUploadedFile(n, b'x', content_type='image/png') for k, n in (('aadhaar', 'aadhaar.png'), ('pan', 'pan.png'), ('bank', 'bank.png'))}
        with patch('api.seller_docs.lookup_pin', return_value={'city': 'Mumbai', 'state': 'Maharashtra'}), \
                patch('api.seller_docs.lookup_ifsc', return_value={'branch': 'Andheri'}), \
                patch('api.seller_views._geocode', return_value=(19.1136, 72.8697)):
            res = self.c.post('/api/seller/applications/autofill', files, format='multipart')
        self.assertEqual(res.status_code, 200, res.content)
        d = res.json()
        self.assertEqual((d['applicantName'], d['pan'], d['pincode'], d['city'], d['addressState']), ('Rahul Sharma', 'ABCDE1234F', '400069', 'Mumbai', 'Maharashtra'))
        self.assertEqual(d['address'], '12 Hill Road Andheri East')
        self.assertEqual(d['companyName'], 'Rahul Store')
        self.assertEqual((d['store']['latitude'], d['store']['longitude']), (19.1136, 72.8697))
        self.assertEqual(d['identity']['accountHolder'], 'Rahul Sharma')
        self.assertEqual(d['autofill']['problems'], {})
        self.assertEqual(self.c.post(f"/api/seller/applications/{d['id']}/submit").json()['status'], 'PENDING_ADMIN_APPROVAL')

    def test_login_account_that_is_still_a_customer_can_resume(self):
        self.c.post('/api/seller/applications/start')
        self.assertEqual(len(self.c.get('/api/seller/applications').json()), 1)

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

    def test_full_aadhaar_is_accepted_and_stored_exactly_as_displayed(self):
        app_id = self.start()
        res = upload(self.c, app_id, 'AADHAAR', 'aadhaar_full.png').json()
        self.assertEqual(res['ocrStatus'], 'DONE')
        self.assertEqual(res['extractedFields']['aadhaarMasked'], 'XXXX-XXXX-4821')
        app = SellerApplication.objects.get(id=app_id)
        self.assertEqual(secure_fields.decrypt(app.aadhaarNumberEnc), '234567894821')  # the number as read, even though it fails the checksum
        self.assertNotIn('234567894821', app.aadhaarNumberEnc)  # encrypted at rest
        self.assertEqual(app.aadhaarLast4, '4821')
        self.assertTrue(any('checksum' in w for w in res['warnings']))  # a warning only: nothing is rejected
        doc = app.documents.get(docType='AADHAAR')
        self.assertTrue(doc.file)
        self.assertNotIn('6789', doc.redactedText)  # saved text never carries the digits

    def test_a_number_that_passes_the_checksum_has_no_warning(self):
        app_id = self.start()
        res = upload(self.c, app_id, 'AADHAAR', 'aadhaar_valid.png').json()
        self.assertEqual(res['warnings'], [])
        self.assertEqual(secure_fields.decrypt(SellerApplication.objects.get(id=app_id).aadhaarNumberEnc), VALID_AADHAAR)

    def test_the_full_number_never_appears_in_any_response(self):
        app_id = self.start()
        upload(self.c, app_id, 'AADHAAR', 'aadhaar_full.png')
        for client in (self.c, self.a):
            body = client.get(f'/api/seller/applications/{app_id}').content.decode()
            self.assertNotIn('234567894821', body)
            self.assertNotIn('2345 6789', body)
            self.assertNotIn('aadhaarNumberEnc', body)
        self.assertNotIn('aadhaarNumberEnc', self.a.get('/api/seller/applications').content.decode())

    def test_uploading_a_masked_copy_later_clears_the_old_full_number(self):
        app_id = self.start()
        upload(self.c, app_id, 'AADHAAR', 'aadhaar_full.png')
        upload(self.c, app_id, 'AADHAAR', 'aadhaar.png')
        app = SellerApplication.objects.get(id=app_id)
        self.assertEqual((app.aadhaarNumberEnc, app.aadhaarLast4), ('', '4821'))

    def test_only_an_admin_can_reveal_the_number_and_it_is_audited(self):
        app_id = self.start()
        url = f'/api/admin/seller-applications/{app_id}/aadhaar'
        self.assertEqual(self.a.post(url).status_code, 404)  # nothing stored yet
        upload(self.c, app_id, 'AADHAAR', 'aadhaar_full.png')
        self.assertEqual(self.guest.post(url).status_code, 401)
        self.assertEqual(self.c.post(url).status_code, 403)  # not even the applicant
        self.assertEqual(self.o.post(url).status_code, 403)
        res = self.a.post(url)
        self.assertEqual((res.status_code, res.json()['aadhaarNumber'], res.json()['masked']), (200, '2345 6789 4821', 'XXXX-XXXX-4821'))
        self.assertTrue(SellerApplication.objects.get(id=app_id).audit_logs.filter(action='AADHAAR_REVEALED', performedBy='boss@example.com').exists())

    def test_parser_reads_a_standalone_number_but_not_a_virtual_id(self):
        self.assertEqual(seller_docs.parse_aadhaar('Aadhaar no.\n2345 6789 4821\n400069')['aadhaarNumber'], '234567894821')
        self.assertEqual(seller_docs.parse_aadhaar('2345-6789-4821')['aadhaarNumber'], '234567894821')
        self.assertIsNone(seller_docs.parse_aadhaar('VID : 9123 4567 8901 2345')['aadhaarNumber'])  # 16 digits: not an Aadhaar number
        self.assertIsNone(seller_docs.parse_aadhaar('XXXX XXXX 4821')['aadhaarNumber'])  # masked copy: nothing to store
        self.assertTrue(seller_docs.verhoeff_valid(VALID_AADHAAR))
        self.assertFalse(seller_docs.verhoeff_valid('234567894821'))

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
        self.assertEqual(len(p['documents']), 3)

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


@patch('api.seller_docs.lookup_ifsc', return_value={})  # no network: the live IFSC lookup is switched off
class DocumentReadingTests(SimpleTestCase):
    """What the reader does with the text the OCR engine really returns, which has no spaces inside lines ("StateBankofIndia")."""

    def test_ocr_fragments_and_card_headings_are_not_names(self, _):
        self.assertFalse(seller_docs.plausible_name('Fa'))
        self.assertFalse(seller_docs.plausible_name('K R'))
        self.assertTrue(seller_docs.plausible_name('Rahul Sharma'))
        self.assertTrue(seller_docs.plausible_name('RAHULMOHANSHARMA'))  # spaces lost, still a name
        self.assertFalse(seller_docs._looks_like_name('INCOMETAXDEPARTMENT'))
        self.assertFalse(seller_docs._looks_like_name('GOVTOFINDIA'))

    def test_a_pan_with_an_unreadable_name_leaves_it_empty(self, _):
        out = seller_docs.parse_pan('INCOMETAXDEPARTMENT\nGOVTOFINDIA\nAIVPU0924A\nName\nFa')
        self.assertEqual((out['pan'], out['name']), ('AIVPU0924A', None))

    def test_the_pan_number_checks_the_surname_letter(self, _):
        self.assertTrue(seller_docs.name_fits_pan('Rahul Sharma', 'ABCPS1234F'))  # 4th letter P = individual, 5th = S for Sharma
        self.assertFalse(seller_docs.name_fits_pan('Priya Nair', 'ABCPS1234F'))
        self.assertTrue(seller_docs.name_fits_pan('Priya Nair', 'ABCDS1234F'))  # not an individual's PAN: no surname rule
        self.assertIsNone(seller_docs.parse_pan('INCOME TAX DEPARTMENT\nABCPS1234F\nName\nPriya Nair')['name'])
        self.assertEqual(seller_docs.parse_pan('INCOME TAX DEPARTMENT\nABCPS1234F\nName\nRahul Sharma')['name'], 'Rahul Sharma')

    def test_a_bad_name_never_reaches_the_form(self, _):
        docs = [SimpleNamespace(docType='PAN', ocrStatus='DONE', extractedFields={'pan': 'AIVPU0924A', 'name': 'Fa'})]
        user = SimpleNamespace(email='Seller@Example.com', phone='7895689545')
        fill = seller_docs.build_autofill(user, None, docs)['fields']
        self.assertNotIn('applicantName', fill)
        self.assertNotIn('companyName', fill)  # no more "Fa Store"
        docs.append(SimpleNamespace(docType='AADHAAR', ocrStatus='DONE', extractedFields={'name': 'Umesh Pal'}))
        self.assertEqual(seller_docs.build_autofill(user, None, docs)['fields']['applicantName'], 'Umesh Pal')  # another document supplies it

    def test_bank_is_named_from_the_ifsc_and_the_account_from_its_label(self, _):
        out = seller_docs.parse_bank('StateBankofIndia\nIFSC:SBIN0001234A/cNo31234567044')
        self.assertEqual((out['ifsc'], out['bankName'], out['accountLast4']), ('SBIN0001234', 'State Bank of India', '7044'))

    def test_a_labelled_account_number_beats_the_first_long_number(self, _):
        out = seller_docs.parse_bank('Customer ID 99887766554\nAccount Number: 3123 4567 044\nIFSC HDFC0001234')
        self.assertEqual(out['accountLast4'], '7044')  # not the customer ID
        self.assertEqual(seller_docs.parse_bank('Ref 99887766554')['accountLast4'], '6554')  # no label: falls back to the first long number

    def test_a_misread_bank_name_is_matched_to_the_real_one(self, _):
        self.assertEqual(seller_docs.canonical_bank('State Bank Of Indla'), 'State Bank of India')
        self.assertEqual(seller_docs.canonical_bank('HDFC Bnak'), 'HDFC Bank')
        self.assertEqual(seller_docs.canonical_bank('Local Mahila Society'), 'Local Mahila Society')  # unknown: left as read
        self.assertEqual(seller_docs.parse_bank('State Bank Of Indla\nA/c No 123456789012')['bankName'], 'State Bank of India')  # no IFSC either
