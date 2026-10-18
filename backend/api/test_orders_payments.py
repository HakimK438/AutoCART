"""Orders and payments: the server decides prices and payment status, and orders stay private. Online payment is Razorpay in test mode."""

import os
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from api.models import Coupon, Order, OrderFulfillment, Payment, Product, SellerApplication, Store, StoreInventory, User
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
        pod = self.place(items=[{'id': 'p2', 'quantity': 1}], paymentMethod='UPI or Card on Delivery').json()
        self.assertEqual((pod['paymentStatus'], pod['status'], pod['paymentRequired']), ('Pending', 'Confirmed', False))
        self.assertEqual(self.place(paymentMethod='UPI').status_code, 400)  # unknown methods are refused
        online = self.place(paymentMethod='Razorpay (Test Mode)').json()  # online payment: unpaid until the signature is verified
        self.assertEqual((online['paymentStatus'], online['status'], online['paymentRequired']), ('Awaiting Payment', 'Pending', True))

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


class UpiScanAndPayTests(TestCase):
    """Customer pays the seller's own UPI ID; the seller confirms the money arrived."""

    def setUp(self):
        self.cust = User.objects.create_user(email='c@example.com', name='Cathy', password='pw-12345')
        self.other = User.objects.create_user(email='o@example.com', name='Omar', password='pw-12345')
        self.seller = User.objects.create_user(email='s@example.com', name='Sita', password='pw-12345', role='SELLER')
        self.rival = User.objects.create_user(email='r@example.com', name='Ravi', password='pw-12345', role='SELLER')
        self.admin = User.objects.create_user(email='a@example.com', name='Boss', password='pw-12345', role='ADMIN')
        SellerApplication.objects.create(id='app-s', ownerUserId=self.seller.id, applicantName='Sita', companyName='Sita Stores', email='s@example.com', phone='9820012345', status='APPROVED')
        SellerApplication.objects.create(id='app-r', ownerUserId=self.rival.id, applicantName='Ravi', companyName='Ravi Mart', email='r@example.com', phone='9820012346', status='APPROVED')
        Product.objects.create(id='p1', name='Flask', slug='flask', category='Home', price=500, stock=10, seller='Sita Stores')
        Product.objects.create(id='p2', name='Lamp', slug='lamp', category='Home', price=900, stock=10, seller='Ravi Mart')
        self.c, self.o, self.s, self.r, self.boss, self.guest = authed(self.cust), authed(self.other), authed(self.seller), authed(self.rival), authed(self.admin), APIClient()

    def order(self, items=None):
        return self.c.post('/api/orders', {'items': items or [{'id': 'p1', 'quantity': 1}], 'paymentMethod': 'UPI (Scan & Pay)',
                                           'shippingAddress': {'fullName': 'Cathy', 'phone': '9820012345', 'addressLine': '1 Road', 'city': 'Mumbai'}}, format='json')

    def test_upi_needs_a_seller_upi_id_and_a_single_seller(self):
        r = self.order()
        self.assertEqual(r.status_code, 400)  # Sita has not added a UPI ID
        self.assertIn('UPI ID', r.json()['detail'])
        self.assertEqual(Order.objects.count(), 0)
        self.s.put('/api/seller/payout-settings', {'upiId': 'sita@okaxis'}, format='json')
        mixed = self.order([{'id': 'p1', 'quantity': 1}, {'id': 'p2', 'quantity': 1}])
        self.assertEqual(mixed.status_code, 400)
        self.assertIn('one seller', mixed.json()['detail'])
        self.assertEqual(Product.objects.get(id='p1').stock, 10)  # nothing was taken

    def test_bad_upi_id_is_refused_and_buyers_cannot_set_one(self):
        self.assertEqual(self.s.put('/api/seller/payout-settings', {'upiId': 'not valid'}, format='json').status_code, 400)
        self.assertEqual(self.c.put('/api/seller/payout-settings', {'upiId': 'x@okaxis'}, format='json').status_code, 403)

    def test_full_flow_pay_submit_reference_seller_confirms(self):
        self.s.put('/api/seller/payout-settings', {'upiId': 'sita@okaxis'}, format='json')
        o = self.order().json()
        self.assertEqual((o['paymentStatus'], o['status'], o['paymentRequired']), ('Awaiting Payment', 'Pending', True))
        self.assertIn('pa=sita%40okaxis', o['upi']['link'])
        oid = o['id']
        self.assertEqual(self.o.get(f'/api/orders/{oid}/upi').status_code, 404)  # someone else's order
        self.assertEqual(self.c.get(f'/api/orders/{oid}/upi').json()['amount'], o['totalAmount'])
        self.assertEqual(self.s.post(f'/api/orders/{oid}/payment', {'action': 'received'}, format='json').status_code, 400)  # nothing submitted yet
        self.assertEqual(self.c.post(f'/api/orders/{oid}/upi-reference', {'utr': '12345'}, format='json').status_code, 400)
        self.assertEqual(self.c.post(f'/api/orders/{oid}/upi-reference', {'utr': '123456789012'}, format='json').json()['paymentStatus'], 'Verifying')
        self.assertEqual(self.c.post(f'/api/orders/{oid}/payment', {'action': 'received'}, format='json').status_code, 403)  # the buyer cannot confirm their own payment
        self.assertEqual(self.r.post(f'/api/orders/{oid}/payment', {'action': 'received'}, format='json').status_code, 403)  # a different seller cannot
        done = self.s.post(f'/api/orders/{oid}/payment', {'action': 'received'}, format='json').json()
        self.assertEqual((done['paymentStatus'], done['status']), ('Paid', 'Confirmed'))

    def test_reference_cannot_be_reused_and_a_rejected_payment_can_be_retried(self):
        self.s.put('/api/seller/payout-settings', {'upiId': 'sita@okaxis'}, format='json')
        one, two = self.order().json()['id'], self.order().json()['id']
        self.c.post(f'/api/orders/{one}/upi-reference', {'utr': '123456789012'}, format='json')
        self.assertEqual(self.c.post(f'/api/orders/{two}/upi-reference', {'utr': '123456789012'}, format='json').status_code, 409)
        self.s.post(f'/api/orders/{one}/payment', {'action': 'not_received'}, format='json')
        self.assertEqual(Order.objects.get(id=one).paymentStatus, 'Failed')
        self.assertEqual(self.c.post(f'/api/orders/{one}/upi-reference', {'utr': '999999999999'}, format='json').status_code, 200)  # try again with the right number

    def test_seller_cannot_pack_until_paid_and_admin_sees_waiting_payments(self):
        self.s.put('/api/seller/payout-settings', {'upiId': 'sita@okaxis'}, format='json')
        oid = self.order().json()['id']
        self.assertEqual(self.s.post(f'/api/seller/orders/{oid}/pack').status_code, 400)
        self.c.post(f'/api/orders/{oid}/upi-reference', {'utr': '123456789012'}, format='json')
        waiting = self.boss.get('/api/payments/status').json()['waiting']
        self.assertEqual((waiting[0]['orderId'], waiting[0]['utr'], waiting[0]['seller']), (oid, '123456789012', 'Sita Stores'))
        self.assertEqual(self.c.get('/api/payments/status').status_code, 403)
        self.s.post(f'/api/orders/{oid}/payment', {'action': 'received'}, format='json')
        self.assertEqual(self.s.post(f'/api/seller/orders/{oid}/pack').json()['status'], 'Packed')

    def test_checkout_knows_when_upi_cannot_work(self):
        c = APIClient()
        empty = c.post('/api/payments/upi-check', {'items': []}, format='json').json()
        self.assertEqual(empty['available'], False)
        no_upi = c.post('/api/payments/upi-check', {'items': [{'id': 'p1'}]}, format='json').json()
        self.assertEqual(no_upi['available'], False)
        self.assertIn('UPI ID', no_upi['reason'])
        self.s.put('/api/seller/payout-settings', {'upiId': 'sita@okaxis'}, format='json')
        yes = c.post('/api/payments/upi-check', {'items': [{'id': 'p1'}]}, format='json').json()
        self.assertEqual((yes['available'], yes['payee']), (True, 'Sita Stores'))
        mixed = c.post('/api/payments/upi-check', {'items': [{'id': 'p1'}, {'id': 'p2'}]}, format='json').json()
        self.assertEqual(mixed['available'], False)


@patch.dict(os.environ, NO_KEYS)
class RazorpayTests(TestCase):
    """Online payment. With no keys it is a labelled local demo of the same signed flow; the server checks the signature."""

    def setUp(self):
        self.alice = User.objects.create_user(email='alice@example.com', name='Alice', password='pw-12345')
        self.bob = User.objects.create_user(email='bob@example.com', name='Bob', password='pw-12345')
        self.a, self.b = authed(self.alice), authed(self.bob)
        Product.objects.create(id='p1', name='Mouse', slug='mouse', category='Electronics', price=1000, stock=5)
        res = self.a.post('/api/orders', {'items': [{'id': 'p1', 'quantity': 1}], 'paymentMethod': 'Razorpay (Test Mode)', 'shippingAddress': {'fullName': 'Alice'}}, format='json').json()
        self.oid, self.created = res['id'], res

    def start(self, client=None):
        return (client or self.a).post('/api/payments/razorpay/order', {'orderId': self.oid}, format='json')

    def sign(self, pay, outcome='success'):
        return self.a.post('/api/payments/razorpay/demo-sign', {'orderId': self.oid, 'razorpayOrderId': pay['razorpayOrderId'], 'outcome': outcome}, format='json')

    def test_an_online_order_waits_for_payment(self):
        self.assertTrue(self.created['paymentRequired'])
        o = Order.objects.get(id=self.oid)
        self.assertEqual((o.paymentStatus, o.status), ('Awaiting Payment', 'Pending'))

    def test_config_reports_demo_mode_without_keys_and_never_a_secret(self):
        cfg = APIClient().get('/api/payments/config').json()
        self.assertEqual((cfg['mode'], cfg['keyId']), ('demo', ''))

    def test_amount_comes_from_the_stored_order(self):
        res = self.a.post('/api/payments/razorpay/order', {'orderId': self.oid, 'amount': 1}, format='json').json()
        self.assertEqual((res['amount'], res['currency'], res['demo']), (100000, 'INR', True))  # 1000 rupees in paise

    def test_demo_payment_succeeds_and_marks_the_order_paid(self):
        sig = self.sign(self.start().json()).json()
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
        self.assertEqual(Order.objects.get(id=self.oid).paymentStatus, 'Failed')
        self.assertEqual(self.start().status_code, 200)  # the customer can try again

    def test_a_declined_test_payment_stays_unpaid(self):
        self.assertEqual(self.sign(self.start().json(), 'failure').status_code, 402)
        self.assertNotEqual(Order.objects.get(id=self.oid).paymentStatus, 'Paid')

    def test_someone_else_cannot_pay_or_verify_my_order(self):
        self.assertEqual(self.start(self.b).status_code, 404)
        self.assertEqual(self.start(APIClient()).status_code, 401)
        sig = self.sign(self.start().json()).json()
        self.assertEqual(self.b.post('/api/payments/razorpay/verify', {'orderId': self.oid, **sig}, format='json').status_code, 404)

    def test_a_signature_cannot_be_used_twice(self):
        sig = self.sign(self.start().json()).json()
        self.assertEqual(self.a.post('/api/payments/razorpay/verify', {'orderId': self.oid, **sig}, format='json').status_code, 200)
        self.assertEqual(self.a.post('/api/payments/razorpay/verify', {'orderId': self.oid, **sig}, format='json').status_code, 400)

    def test_cash_orders_do_not_need_online_payment(self):
        cod = self.a.post('/api/orders', {'items': [{'id': 'p1', 'quantity': 1}], 'paymentMethod': 'Cash on Delivery'}, format='json').json()['id']
        self.assertEqual(self.a.post('/api/payments/razorpay/order', {'orderId': cod}, format='json').status_code, 400)

    def test_live_keys_are_refused(self):
        with patch.dict(os.environ, {'RAZORPAY_KEY_ID': 'rzp_live_abc', 'RAZORPAY_KEY_SECRET': 'secret'}):
            self.assertEqual(self.start().status_code, 503)

    def test_admin_overview_shows_the_razorpay_mode_and_no_secret(self):
        admin = authed(User.objects.create_user(email='boss@example.com', name='Boss', password='pw-12345', role='ADMIN'))
        d = admin.get('/api/payments/status').json()
        self.assertEqual((d['razorpay']['mode'], d['razorpay']['connection']), ('demo', None))
        self.assertEqual(self.a.get('/api/payments/status').status_code, 403)
        with patch.dict(os.environ, {'RAZORPAY_KEY_ID': 'rzp_test_ABCDEFGH1234', 'RAZORPAY_KEY_SECRET': 'topsecretvalue'}), \
                patch('api.order_views.requests.get', return_value=type('Ok', (), {'status_code': 200})()):
            text = admin.get('/api/payments/status').content.decode()
        self.assertIn('"test"', text)
        self.assertNotIn('topsecretvalue', text)


class NearestStoreTests(TestCase):
    """A delivery order is packed by the nearest store that has every item, not by one fixed seller pin."""

    def setUp(self):
        self.alice = User.objects.create_user(email='alice@example.com', name='Alice', password='pw-12345')
        self.a = authed(self.alice)
        Product.objects.create(id='p1', name='Mouse', slug='mouse', category='Electronics', price=1000, stock=5)
        self.near = Store.objects.create(id='near', name='AutoCart Near', address='x', city='Kalyan', pincode='421301', latitude=19.23, longitude=73.14)
        self.far = Store.objects.create(id='far', name='AutoCart Far', address='y', city='Andheri', pincode='400069', latitude=19.11, longitude=72.87)
        for st in (self.near, self.far):
            StoreInventory.objects.create(id=f'inv-{st.id}', store=st, product_id='p1', availableQuantity=5, storePrice=1000)

    def place(self, lat=19.229, lng=73.142, **over):
        body = {'items': [{'id': 'p1', 'quantity': 1}], 'paymentMethod': 'Cash on Delivery',
                'shippingAddress': {'fullName': 'Alice', 'addressLine': 'Kolsewadi', 'city': 'Kalyan', 'latitude': lat, 'longitude': lng}, **over}
        return self.a.post('/api/orders', body, format='json')

    def test_the_nearest_store_with_stock_packs_it(self):
        oid = self.place().json()['id']
        ful = OrderFulfillment.objects.get(order_id=oid)
        self.assertEqual(ful.store_id, 'near')
        self.assertLess(ful.distanceKm, 3)
        track = self.a.get(f'/api/orders/{oid}/tracking').json()
        self.assertEqual(track['fulfilledBy']['storeName'], 'AutoCart Near')

    def test_a_store_without_stock_is_skipped(self):
        StoreInventory.objects.filter(store_id='near').update(availableQuantity=0)
        ful = OrderFulfillment.objects.get(order_id=self.place().json()['id'])
        self.assertEqual(ful.store_id, 'far')

    def test_an_online_order_is_not_packable_until_it_is_paid(self):
        res = self.place(paymentMethod='Razorpay (Test Mode)').json()
        self.assertEqual((res['paymentStatus'], res['paymentRequired']), ('Awaiting Payment', True))


class OrderLifecycleTests(TestCase):
    """Packed is not the end: out for delivery, delivered, the customer is told at each step, and the sale is recorded for the seller."""

    def setUp(self):
        self.cust = User.objects.create_user(email='cathy@example.com', name='Cathy Customer', password='pw-12345')
        self.other = User.objects.create_user(email='other@example.com', name='Other', password='pw-12345')
        self.s1 = User.objects.create_user(email='s1@example.com', name='Sita One', password='pw-12345', role='SELLER')
        self.s2 = User.objects.create_user(email='s2@example.com', name='Ravi Two', password='pw-12345', role='SELLER')
        for u, name in ((self.s1, 'Sita Stores'), (self.s2, 'Ravi Mart')):
            SellerApplication.objects.create(id=f'app-{u.id}', ownerUserId=u.id, applicantName=u.name, companyName=name, email=u.email, phone='9820012345', status='APPROVED')
        Product.objects.create(id='p1', name='Steel Flask', slug='flask', category='Home', seller='Sita Stores', price=500, stock=10)
        self.c, self.o, self.a, self.b = authed(self.cust), authed(self.other), authed(self.s1), authed(self.s2)
        res = self.c.post('/api/orders', {'items': [{'id': 'p1', 'quantity': 2}], 'paymentMethod': 'Cash on Delivery',
                                          'shippingAddress': {'fullName': 'Cathy', 'phone': '9820099999', 'addressLine': '12 Hill Rd', 'city': 'Mumbai'}}, format='json').json()
        self.oid = res['id']

    def step(self, name, client=None):
        return (client or self.a).post(f'/api/seller/orders/{self.oid}/{name}')

    def titles(self):
        return [n['title'] for n in self.c.get('/api/notifications').json()['items']]

    def test_the_order_goes_through_every_step_and_the_customer_is_told_each_time(self):
        self.assertEqual(self.step('pack').status_code, 200)
        self.assertEqual(self.step('dispatch').json()['status'], 'Out for Delivery')
        done = self.step('deliver').json()
        self.assertEqual((done['status'], done['paymentStatus']), ('Delivered', 'Paid'))  # cash collected at the door
        order = Order.objects.get(id=self.oid)
        self.assertEqual((order.status, order.paymentStatus), ('Delivered', 'Paid'))
        self.assertEqual(self.titles(), ['Your product has reached you', 'Your order is on its way', 'Your order is packed', 'Order placed'])
        track = self.c.get(f'/api/orders/{self.oid}/tracking').json()
        self.assertTrue(all(s['completed'] for s in track['timeline']))  # every courier step is ticked
        self.assertEqual(track['orderStatus'], 'Delivered')

    def test_steps_must_happen_in_order(self):
        self.assertEqual(self.step('dispatch').status_code, 400)  # not packed yet
        self.assertEqual(self.step('deliver').status_code, 400)
        self.step('pack')
        self.assertEqual(self.step('deliver').status_code, 400)  # not sent out yet
        self.step('dispatch')
        self.assertEqual(self.step('dispatch').status_code, 400)  # only once
        self.assertEqual(self.step('pack').status_code, 400)

    def test_only_the_seller_of_the_product_can_move_the_order(self):
        self.assertEqual(self.step('pack', self.b).status_code, 404)  # another seller
        self.assertEqual(self.step('pack', self.c).status_code, 403)  # a customer
        self.assertEqual(Order.objects.get(id=self.oid).status, 'Confirmed')

    def test_the_delivered_sale_is_recorded_on_the_seller_dashboard(self):
        before = self.a.get('/api/seller/overview').json()
        self.assertEqual((before['revenue'], before['deliveredRevenue'], before['unitsSold']), (1000, 0, 2))  # counted as soon as it is bought
        row = next(o for o in before['orders'] if o['id'] == self.oid)
        self.assertEqual((row['canPack'], row['canDispatch'], row['canDeliver']), (True, False, False))
        self.step('pack')
        self.assertTrue(next(o for o in self.a.get('/api/seller/overview').json()['orders'] if o['id'] == self.oid)['canDispatch'])
        self.step('dispatch')
        self.assertTrue(next(o for o in self.a.get('/api/seller/overview').json()['orders'] if o['id'] == self.oid)['canDeliver'])
        self.step('deliver')
        after = self.a.get('/api/seller/overview').json()
        self.assertEqual((after['revenue'], after['deliveredRevenue'], after['deliveredOrders'], after['unitsSold']), (1000, 1000, 1, 2))

    def test_a_delivered_order_can_be_returned_and_not_cancelled(self):
        for name in ('pack', 'dispatch', 'deliver'):
            self.step(name)
        self.assertEqual(self.c.post(f'/api/orders/{self.oid}/cancel').status_code, 400)
        self.assertEqual(self.c.post(f'/api/orders/{self.oid}/return').status_code, 200)

    def test_notifications_are_private_and_can_be_marked_read(self):
        self.step('pack')
        mine = self.c.get('/api/notifications').json()
        self.assertEqual(mine['unread'], 2)  # order placed, packed
        self.assertEqual(self.o.get('/api/notifications').json()['items'], [])  # someone else sees none of it
        self.assertEqual(APIClient().get('/api/notifications').status_code, 401)
        self.o.post('/api/notifications/read', {})  # another user cannot clear mine
        self.assertEqual(self.c.get('/api/notifications').json()['unread'], 2)
        self.c.post('/api/notifications/read', {'id': mine['items'][0]['id']}, format='json')
        self.assertEqual(self.c.get('/api/notifications').json()['unread'], 1)
        self.c.post('/api/notifications/read', {}, format='json')
        self.assertEqual(self.c.get('/api/notifications').json()['unread'], 0)

    def test_a_pickup_order_becomes_ready_for_pickup_then_collected(self):
        Store.objects.create(id='s9', name='AutoCart Pick Store', address='x', city='Mumbai', pincode='400069', latitude=19.1, longitude=72.8)
        oid = self.c.post('/api/orders', {'items': [{'id': 'p1', 'quantity': 1}], 'paymentMethod': 'Pay at Store', 'storeId': 's9', 'shippingAddress': {'fullName': 'Cathy'}}, format='json').json()['id']
        self.a.post(f'/api/seller/orders/{oid}/pack')
        self.assertEqual(self.a.post(f'/api/seller/orders/{oid}/dispatch').json()['status'], 'Ready for Pickup')
        self.assertEqual(self.a.post(f'/api/seller/orders/{oid}/deliver').json()['status'], 'Delivered')
        self.assertIn('Thanks for collecting your order', [n['title'] for n in self.c.get('/api/notifications').json()['items']])
