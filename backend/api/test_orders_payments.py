"""Orders and Razorpay (test mode): the server decides prices and payment status, and orders stay private."""

import os
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from api.models import Coupon, Order, Payment, Product, Store, User
from api.views import generate_token

NO_KEYS = {'RAZORPAY_KEY_ID': '', 'RAZORPAY_KEY_SECRET': ''}


def authed(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + generate_token(user))
    return c


class OrderTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(email='alice@example.com', name='Alice', password='pw-12345')
        self.bob = User.objects.create_user(email='bob@example.com', name='Bob', password='pw-12345')
        self.admin = User.objects.create_user(email='boss@example.com', name='Boss', password='pw-12345', role='ADMIN')
        self.a, self.b, self.boss, self.guest = authed(self.alice), authed(self.bob), authed(self.admin), APIClient()
        Product.objects.create(id='p1', name='Mouse', slug='mouse', category='Electronics', price=1000, stock=5, images=['m.jpg'])
        Product.objects.create(id='p2', name='Cable', slug='cable', category='Electronics', price=100, stock=2)
        Store.objects.create(id='s1', name='Andheri Store', address='x', city='Mumbai', pincode='400069', latitude=19.1, longitude=72.8)

    def place(self, client=None, items=None, **over):
        body = {'items': items or [{'id': 'p1', 'quantity': 2, 'price': 1}], 'paymentMethod': 'Cash on Delivery',
                'shippingAddress': {'fullName': 'Alice', 'phone': '9820012345', 'addressLine': 'x', 'city': 'Mumbai'}, **over}
        return (client or self.a).post('/api/orders', body, format='json')

    def test_guest_cannot_order(self):
        self.assertEqual(self.place(self.guest).status_code, 401)

    def test_prices_come_from_the_database_not_the_browser(self):
        res = self.place(items=[{'id': 'p1', 'quantity': 2, 'price': 1}], totalAmount=1, subtotal=1, userEmail='bob@example.com')
        self.assertEqual(res.status_code, 201, res.content)
        o = Order.objects.get(id=res.json()['id'])
        self.assertEqual((o.subtotal, o.shippingFee, o.totalAmount), (2000.0, 0.0, 2000.0))  # over 499: free delivery
        self.assertEqual(o.customerEmail, 'alice@example.com')  # not the email in the request
        self.assertEqual(o.items[0]['price'], 1000)

    def test_small_order_pays_the_delivery_fee(self):
        res = self.place(items=[{'id': 'p2', 'quantity': 1}])
        self.assertEqual(res.json()['totalAmount'], 140.0)

    def test_stock_goes_down_and_cannot_go_below_zero(self):
        self.assertEqual(self.place(items=[{'id': 'p1', 'quantity': 5}]).status_code, 201)
        p = Product.objects.get(id='p1')
        self.assertEqual((p.stock, p.stockStatus), (0, 'Out of Stock'))
        res = self.place(items=[{'id': 'p1', 'quantity': 1}])
        self.assertEqual(res.status_code, 409)
        self.assertIn('out of stock', res.json()['detail'].lower())
        self.assertEqual(Product.objects.get(id='p1').stock, 0)

    def test_asking_for_more_than_is_left_is_refused_and_changes_nothing(self):
        res = self.place(items=[{'id': 'p1', 'quantity': 3}, {'id': 'p2', 'quantity': 9}])
        self.assertEqual(res.status_code, 409)
        self.assertEqual((Product.objects.get(id='p1').stock, Product.objects.get(id='p2').stock), (5, 2))
        self.assertEqual(Order.objects.count(), 0)

    def test_payment_status_is_never_paid_by_default(self):
        cod = self.place(items=[{'id': 'p2', 'quantity': 1}]).json()
        self.assertEqual((cod['paymentStatus'], cod['status']), ('Pending', 'Confirmed'))
        online = self.place(items=[{'id': 'p2', 'quantity': 1}], paymentMethod='Razorpay (Test Mode)').json()
        self.assertEqual((online['paymentStatus'], online['status'], online['paymentRequired']), ('Awaiting Payment', 'Pending', True))
        self.assertEqual(self.place(paymentMethod='UPI').status_code, 400)  # the old "UPI/Card = instantly Paid" is gone

    def test_pay_at_store_needs_a_store(self):
        self.assertEqual(self.place(paymentMethod='Pay at Store').status_code, 400)
        ok = self.place(paymentMethod='Pay at Store', storeId='s1')
        self.assertEqual(ok.status_code, 201)
        self.assertEqual(ok.json()['shippingAddress']['storeName'], 'Andheri Store')

    def test_coupon_is_checked_on_the_server(self):
        Coupon.objects.create(id='c1', code='SAVE10', discountType='Percentage', discountValue=10, maxDiscount=150, minOrderAmount=500, status='Active')
        res = self.place(couponCode='save10')
        self.assertEqual((res.json()['discountAmount'], res.json()['totalAmount']), (150.0, 1850.0))
        self.assertEqual(self.place(items=[{'id': 'p2', 'quantity': 1}], couponCode='SAVE10').status_code, 400)  # below the minimum
        self.assertEqual(self.place(couponCode='NOPE').status_code, 400)

    def test_orders_are_private_to_their_owner(self):
        oid = self.place().json()['id']
        for path in (f'/api/orders/{oid}', f'/api/orders/{oid}/tracking'):
            self.assertEqual(self.guest.get(path).status_code, 401, path)
            self.assertEqual(self.b.get(path).status_code, 404, path)
            self.assertEqual(self.a.get(path).status_code, 200, path)
            self.assertEqual(self.boss.get(path).status_code, 200, path)
        self.assertEqual(self.b.post(f'/api/orders/{oid}/cancel').status_code, 404)
        self.assertEqual(self.guest.post(f'/api/orders/{oid}/cancel').status_code, 401)

    def test_cancelling_puts_the_stock_back(self):
        oid = self.place(items=[{'id': 'p1', 'quantity': 3}]).json()['id']
        self.assertEqual(Product.objects.get(id='p1').stock, 2)
        res = self.a.post(f'/api/orders/{oid}/cancel')
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(Product.objects.get(id='p1').stock, 5)
        self.assertEqual(Order.objects.get(id=oid).status, 'Cancelled')
        self.assertEqual(self.a.post(f'/api/orders/{oid}/cancel').status_code, 400)  # already cancelled

    def test_return_only_after_delivery(self):
        oid = self.place().json()['id']
        self.assertEqual(self.a.post(f'/api/orders/{oid}/return').status_code, 400)
        Order.objects.filter(id=oid).update(status='Delivered')
        self.assertEqual(self.a.post(f'/api/orders/{oid}/return').status_code, 200)


@patch.dict(os.environ, NO_KEYS)
class RazorpayTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(email='alice@example.com', name='Alice', password='pw-12345')
        self.bob = User.objects.create_user(email='bob@example.com', name='Bob', password='pw-12345')
        self.a, self.b = authed(self.alice), authed(self.bob)
        Product.objects.create(id='p1', name='Mouse', slug='mouse', category='Electronics', price=1000, stock=5)
        self.oid = self.a.post('/api/orders', {'items': [{'id': 'p1', 'quantity': 1}], 'paymentMethod': 'Razorpay (Test Mode)',
                                               'shippingAddress': {'fullName': 'Alice'}}, format='json').json()['id']

    def start(self, client=None):
        return (client or self.a).post('/api/payments/razorpay/order', {'orderId': self.oid}, format='json')

    def test_config_reports_demo_mode_without_keys_and_never_a_secret(self):
        cfg = APIClient().get('/api/payments/config').json()
        self.assertEqual((cfg['mode'], cfg['keyId']), ('demo', ''))

    def test_amount_comes_from_the_stored_order(self):
        res = self.a.post('/api/payments/razorpay/order', {'orderId': self.oid, 'amount': 1}, format='json').json()
        self.assertEqual((res['amount'], res['currency'], res['demo']), (100000, 'INR', True))  # 1000 rupees in paise

    def test_demo_payment_succeeds_and_marks_the_order_paid(self):
        pay = self.start().json()
        sig = self.a.post('/api/payments/razorpay/demo-sign', {'orderId': self.oid, 'razorpayOrderId': pay['razorpayOrderId'], 'outcome': 'success'}, format='json').json()
        done = self.a.post('/api/payments/razorpay/verify', {'orderId': self.oid, **sig}, format='json')
        self.assertEqual(done.status_code, 200, done.content)
        o = Order.objects.get(id=self.oid)
        self.assertEqual((o.paymentStatus, o.status), ('Paid', 'Confirmed'))
        self.assertEqual(Payment.objects.get(orderId=self.oid).status, 'PAID')

    def test_a_forged_signature_is_rejected(self):
        pay = self.start().json()
        res = self.a.post('/api/payments/razorpay/verify', {'orderId': self.oid, 'razorpay_order_id': pay['razorpayOrderId'],
                                                           'razorpay_payment_id': 'pay_fake', 'razorpay_signature': 'deadbeef'}, format='json')
        self.assertEqual(res.status_code, 400)
        o = Order.objects.get(id=self.oid)
        self.assertEqual(o.paymentStatus, 'Failed')
        self.assertEqual(self.start().status_code, 200)  # the customer can try again

    def test_a_declined_test_payment_stays_unpaid(self):
        pay = self.start().json()
        res = self.a.post('/api/payments/razorpay/demo-sign', {'orderId': self.oid, 'razorpayOrderId': pay['razorpayOrderId'], 'outcome': 'failure'}, format='json')
        self.assertEqual(res.status_code, 402)
        self.assertNotEqual(Order.objects.get(id=self.oid).paymentStatus, 'Paid')

    def test_someone_else_cannot_pay_or_verify_my_order(self):
        self.assertEqual(self.start(self.b).status_code, 404)
        self.assertEqual(self.start(APIClient()).status_code, 401)
        pay = self.start().json()
        sig = self.a.post('/api/payments/razorpay/demo-sign', {'orderId': self.oid, 'razorpayOrderId': pay['razorpayOrderId'], 'outcome': 'success'}, format='json').json()
        self.assertEqual(self.b.post('/api/payments/razorpay/verify', {'orderId': self.oid, **sig}, format='json').status_code, 404)

    def test_a_signature_cannot_be_used_twice(self):
        pay = self.start().json()
        sig = self.a.post('/api/payments/razorpay/demo-sign', {'orderId': self.oid, 'razorpayOrderId': pay['razorpayOrderId'], 'outcome': 'success'}, format='json').json()
        self.assertEqual(self.a.post('/api/payments/razorpay/verify', {'orderId': self.oid, **sig}, format='json').status_code, 200)
        self.assertEqual(self.a.post('/api/payments/razorpay/verify', {'orderId': self.oid, **sig}, format='json').status_code, 400)

    def test_cash_orders_do_not_need_online_payment(self):
        cod = self.a.post('/api/orders', {'items': [{'id': 'p1', 'quantity': 1}], 'paymentMethod': 'Cash on Delivery'}, format='json').json()['id']
        self.assertEqual(self.a.post('/api/payments/razorpay/order', {'orderId': cod}, format='json').status_code, 400)

    def test_live_keys_are_refused(self):
        with patch.dict(os.environ, {'RAZORPAY_KEY_ID': 'rzp_live_abc', 'RAZORPAY_KEY_SECRET': 'secret'}):
            self.assertEqual(self.start().status_code, 503)


class PaymentStatusTests(TestCase):
    def setUp(self):
        self.admin = authed(User.objects.create_user(email='boss@example.com', name='Boss', password='pw-12345', role='ADMIN'))
        self.customer = authed(User.objects.create_user(email='c@example.com', name='C', password='pw-12345'))

    def test_admin_only(self):
        self.assertEqual(APIClient().get('/api/payments/status').status_code, 403)
        self.assertEqual(self.customer.get('/api/payments/status').status_code, 403)

    @patch.dict(os.environ, NO_KEYS)
    def test_demo_mode_without_keys(self):
        d = self.admin.get('/api/payments/status').json()
        self.assertEqual((d['mode'], d['connection']), ('demo', None))

    def test_connection_check_with_test_keys_and_the_secret_is_never_returned(self):
        class Ok:
            status_code = 200
        with patch.dict(os.environ, {'RAZORPAY_KEY_ID': 'rzp_test_ABCDEFGH1234', 'RAZORPAY_KEY_SECRET': 'topsecretvalue'}), \
                patch('api.order_views.requests.get', return_value=Ok()):
            res = self.admin.get('/api/payments/status')
        d = res.json()
        self.assertEqual((d['mode'], d['connection']['ok']), ('test', True))
        self.assertNotIn('topsecretvalue', res.content.decode())
        self.assertNotIn('ABCDEFGH1234'[:-4], res.content.decode().replace('rzp_test_...', ''))

    def test_rejected_keys_are_reported(self):
        class No:
            status_code = 401
        with patch.dict(os.environ, {'RAZORPAY_KEY_ID': 'rzp_test_ABCDEFGH1234', 'RAZORPAY_KEY_SECRET': 'x'}), patch('api.order_views.requests.get', return_value=No()):
            self.assertFalse(self.admin.get('/api/payments/status').json()['connection']['ok'])

    def test_live_keys_are_blocked_and_never_contacted(self):
        with patch.dict(os.environ, {'RAZORPAY_KEY_ID': 'rzp_live_ABCDEFGH1234', 'RAZORPAY_KEY_SECRET': 'x'}), patch('api.order_views.requests.get') as get:
            d = self.admin.get('/api/payments/status').json()
        self.assertEqual((d['mode'], d['liveKeyBlocked']), ('blocked', True))
        get.assert_not_called()
