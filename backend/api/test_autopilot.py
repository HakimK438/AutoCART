"""Autopilot: sellers can ask for new orders to be packed for them; everything it does is logged and visible; it never goes past 'Packed'."""

from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from api.models import AutomationEvent, Order, Product, SellerApplication, User
from api.views import generate_token


def authed(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + generate_token(user))
    return c


class AutopilotTests(TestCase):
    def setUp(self):
        self.cust = User.objects.create_user(email='c@example.com', name='Cathy', password='pw-12345')
        self.sita = User.objects.create_user(email='s@example.com', name='Sita', password='pw-12345', role='SELLER')
        self.ravi = User.objects.create_user(email='r@example.com', name='Ravi', password='pw-12345', role='SELLER')
        self.admin = User.objects.create_user(email='boss@example.com', name='Boss', password='pw-12345', role='ADMIN')
        for u, name in ((self.sita, 'Sita Stores'), (self.ravi, 'Ravi Mart')):
            SellerApplication.objects.create(id=f'app-{u.id}', ownerUserId=u.id, applicantName=u.name, companyName=name, email=u.email, phone='9820012345', status='APPROVED')
        Product.objects.create(id='p1', name='Flask', slug='flask', category='Home', price=500, stock=20, seller='Sita Stores')
        Product.objects.create(id='p2', name='Lamp', slug='lamp', category='Home', price=900, stock=20, seller='Ravi Mart')
        self.c, self.s, self.r, self.boss = authed(self.cust), authed(self.sita), authed(self.ravi), authed(self.admin)

    def buy(self, items=None, method='Cash on Delivery'):
        res = self.c.post('/api/orders', {'items': items or [{'id': 'p1', 'quantity': 1}], 'paymentMethod': method,
                                          'shippingAddress': {'fullName': 'Cathy', 'phone': '9820099999', 'addressLine': '12 Hill Rd', 'city': 'Mumbai'}}, format='json')
        self.assertEqual(res.status_code, 201, res.content)
        return res.json()['id']

    def switch(self, client, on=True):
        return client.put('/api/seller/automation', {'autoPackOrders': on}, format='json')

    def test_off_by_default_so_nothing_changes(self):
        oid = self.buy()
        self.assertEqual(Order.objects.get(id=oid).status, 'Confirmed')
        self.assertEqual(self.s.get('/api/seller/automation').json()['waitingToPack'], 1)

    def test_a_new_order_is_packed_at_once_when_the_seller_asked(self):
        self.switch(self.s)
        oid = self.buy()
        o = Order.objects.get(id=oid)
        self.assertEqual(o.status, 'Packed')   # and no further: sending out and delivering are real-world steps
        self.assertIn('automatically', o.timeline[-1]['status'])
        events = self.s.get('/api/seller/automation').json()['events']
        self.assertEqual([e['kind'] for e in events], ['auto_pack'])
        self.assertEqual(events[0]['refId'], oid)

    def test_customer_is_told_and_other_sellers_do_not_see_it(self):
        self.switch(self.s)
        self.buy()
        titles = [n['title'] for n in self.c.get('/api/notifications').json()['items']]
        self.assertIn('Your order is packed', titles)
        self.assertEqual(self.r.get('/api/seller/automation').json()['events'], [])

    def test_a_mixed_order_waits_unless_every_seller_opted_in(self):
        self.switch(self.s)
        oid = self.buy([{'id': 'p1', 'quantity': 1}, {'id': 'p2', 'quantity': 1}])
        self.assertEqual(Order.objects.get(id=oid).status, 'Confirmed')
        self.switch(self.r)   # turning it on also clears what is already waiting
        self.assertEqual(Order.objects.get(id=oid).status, 'Packed')

    def test_online_orders_wait_for_the_money(self):
        self.switch(self.s)
        oid = self.buy(method='Razorpay (Test Mode)')
        self.assertEqual(Order.objects.get(id=oid).status, 'Pending')   # unpaid: never auto-packed

    def test_turning_it_on_packs_what_is_already_waiting(self):
        a, b = self.buy(), self.buy()
        body = self.switch(self.s).json()
        self.assertEqual((body['packedNow'], body['waitingToPack']), (2, 0))
        self.assertEqual(Order.objects.filter(status='Packed').count(), 2)
        self.assertEqual(AutomationEvent.objects.filter(kind='pack_all').count(), 1)
        self.assertTrue({a, b} <= set(Order.objects.values_list('id', flat=True)))

    def test_pack_all_button_and_scheduled_sweep(self):
        a = self.buy()
        self.assertEqual(self.s.post('/api/seller/orders/pack-all').json(), {'packed': 1})
        self.assertEqual(Order.objects.get(id=a).status, 'Packed')
        self.assertEqual(self.s.post('/api/seller/orders/pack-all').json(), {'packed': 0})
        self.switch(self.s)
        b = self.buy()
        Order.objects.filter(id=b).update(status='Confirmed')   # as if packing had been missed
        call_command('run_autopilot')
        self.assertEqual(Order.objects.get(id=b).status, 'Packed')

    def test_auto_restock_is_logged_for_the_seller(self):
        Product.objects.filter(id='p1').update(autoRestock=True, reorderLevel=19, restockQty=30)
        self.buy()
        kinds = [e['kind'] for e in self.s.get('/api/seller/automation').json()['events']]
        self.assertIn('auto_restock', kinds)
        self.assertEqual(self.s.get('/api/seller/automation').json()['autoRestockProducts'], 1)

    def test_who_can_see_what(self):
        self.assertEqual(APIClient().get('/api/seller/automation').status_code, 401)
        self.assertEqual(self.c.get('/api/seller/automation').status_code, 403)
        self.assertEqual(self.s.get('/api/admin/automation').status_code, 403)
        self.switch(self.s)
        self.buy()
        body = self.boss.get('/api/admin/automation').json()
        self.assertEqual((body['sellersOnAutopilot'], body['totals'].get('auto_pack')), (1, 1))
