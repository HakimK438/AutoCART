"""What each role can see: sellers see only their own business, admins see the marketplace, customers see neither."""

from django.test import TestCase
from rest_framework.test import APIClient

from api.models import Enquiry, Order, Product, SellerApplication, SupportTicket, User
from api.views import generate_token


def authed(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + generate_token(user))
    return c


class RoleViewTests(TestCase):
    def setUp(self):
        mk = lambda e, n, r='CUSTOMER': User.objects.create_user(email=e, name=n, password='pw-12345', role=r)  # noqa: E731
        self.cust = mk('cust@example.com', 'Cathy Customer')
        self.s1 = mk('s1@example.com', 'Sita One', 'SELLER')
        self.s2 = mk('s2@example.com', 'Ravi Two', 'SELLER')
        self.pending = mk('pending@example.com', 'Pia Pending', 'SELLER')  # role set but never approved
        self.admin = mk('boss@example.com', 'Boss', 'ADMIN')
        for u, name in ((self.s1, 'Sita Stores'), (self.s2, 'Ravi Mart')):
            SellerApplication.objects.create(id=f'app-{u.id}', ownerUserId=u.id, applicantName=u.name, companyName=name, email=u.email, phone='9820012345', status='APPROVED')
        Product.objects.create(id='a1', name='Flask', slug='flask', category='Home', seller='Sita Stores', price=500, originalPrice=800, stock=3, specifications={'Capacity': '1 litre', 'Material': 'Steel'})
        Product.objects.create(id='a2', name='Bottle', slug='bottle', category='Home', seller='Sita Stores', price=200, stock=50)
        Product.objects.create(id='b1', name='Rival Lamp', slug='lamp', category='Home', seller='Ravi Mart', price=900, stock=0)
        Order.objects.create(id='ORD-1', customerName='Cathy Customer', customerEmail='cust@example.com', date='2026-01-01', status='Confirmed',
                             items=[{'id': 'a1', 'name': 'Flask', 'price': 500, 'quantity': 2}, {'id': 'b1', 'name': 'Rival Lamp', 'price': 900, 'quantity': 1}])
        self.c, self.a, self.b, self.p, self.boss, self.guest = authed(self.cust), authed(self.s1), authed(self.s2), authed(self.pending), authed(self.admin), APIClient()

    def test_seller_overview_is_only_for_active_sellers(self):
        self.assertEqual(self.guest.get('/api/seller/overview').status_code, 401)
        self.assertEqual(self.c.get('/api/seller/overview').status_code, 403)
        self.assertEqual(self.boss.get('/api/seller/overview').status_code, 403)  # even the admin does not get a seller's view
        self.assertEqual(self.p.get('/api/seller/overview').status_code, 403)

    def test_a_seller_sees_only_their_own_business(self):
        d = self.a.get('/api/seller/overview').json()
        self.assertEqual((d['company'], d['productsCount'], d['lowStock'], d['unitsSold'], d['revenue']), ('Sita Stores', 2, 1, 2, 1000))
        self.assertEqual([p['id'] for p in d['products']].sort(), ['a1', 'a2'].sort())
        self.assertNotIn('Rival Lamp', str(d))  # the other seller's product in the same order is not shown
        self.assertEqual(d['orders'][0]['customerFirstName'], 'Cathy')
        self.assertNotIn('cust@example.com', str(d))
        other = self.b.get('/api/seller/overview').json()
        self.assertEqual((other['company'], other['productsCount'], other['outOfStock']), ('Ravi Mart', 1, 1))
        self.assertNotIn('Flask', str(other))

    def test_seller_can_change_own_price_and_stock_only(self):
        res = self.a.patch('/api/seller/products/a1', {'price': 400, 'stock': 20}, format='json')
        self.assertEqual(res.status_code, 200)
        self.assertEqual((res.json()['discount'], res.json()['stockStatus']), (50, 'In Stock'))
        self.assertEqual(self.a.patch('/api/seller/products/b1', {'stock': 99}, format='json').status_code, 404)  # someone else's product
        self.assertEqual(self.a.patch('/api/seller/products/a1', {'price': -5, 'stock': 'x'}, format='json').status_code, 400)
        self.assertEqual(self.c.patch('/api/seller/products/a1', {'stock': 9}, format='json').status_code, 403)
        self.assertEqual(Product.objects.get(id='b1').stock, 0)

    def test_admin_overview_is_admin_only_and_counts_real_things(self):
        self.assertEqual(self.a.get('/api/admin/overview').status_code, 403)
        self.assertEqual(self.c.get('/api/admin/overview').status_code, 403)
        SellerApplication.objects.create(id='app-new', ownerUserId='x', applicantName='N', companyName='New Shop', email='n@example.com', phone='1', status='PENDING_ADMIN_APPROVAL', riskScore=40)
        Enquiry.objects.create(id='ENQ-1', customerName='A', customerEmail='a@example.com', message='Is this good?')
        SupportTicket.objects.create(id='TKT-1', customerEmail='cust@example.com', subject='Late')
        d = self.boss.get('/api/admin/overview').json()
        self.assertEqual((d['cards']['applications'], d['cards']['openEnquiries'], d['cards']['openTickets'], d['cards']['outOfStock'], d['cards']['lowStock']), (1, 1, 1, 1, 1))
        text = ' '.join(b['text'] for b in d['briefing'])
        self.assertIn('New Shop', text)
        self.assertIn('Flask', text)

    def test_answer_draft_uses_only_the_products_own_details(self):
        enq = Enquiry.objects.create(id='ENQ-2', productId='a1', productName='Flask', sellerName='Sita Stores', customerName='Anita Rao', customerEmail='a@example.com', message='What is the capacity and do you have it in stock?')
        d = self.a.post('/api/enquiries/ENQ-2/draft').json()
        self.assertIn('1 litre', d['draft'])
        self.assertIn('3 in stock', d['draft'])
        self.assertEqual(d['confidence'], 'high')
        self.assertEqual(self.b.post('/api/enquiries/ENQ-2/draft').status_code, 404)  # a rival seller cannot see it
        self.assertEqual(self.c.post('/api/enquiries/ENQ-2/draft').status_code, 404)
        enq.message = 'Will it survive a trip to Mars?'
        enq.save()
        self.assertEqual(self.a.post('/api/enquiries/ENQ-2/draft').json()['confidence'], 'low')


class SellerAssistantTests(RoleViewTests):
    """The seller assistant answers from the seller's own rows only."""

    def ask(self, client, q):
        return client.post('/api/seller/assistant', {'message': q}, format='json')

    def test_only_active_sellers_can_ask(self):
        for client, code in ((self.guest, 401), (self.c, 403), (self.boss, 403), (self.p, 403)):
            self.assertEqual(self.ask(client, 'low stock').status_code, code)

    def test_low_stock_and_sales_come_from_the_database(self):
        low = self.ask(self.a, 'Which products are low on stock?').json()
        self.assertEqual(low['rows'], [['Flask', 3]])
        best = self.ask(self.a, 'What are my best selling products?').json()
        self.assertEqual(best['rows'][0][:2], ['Flask', 2])
        self.assertIn('1,000', self.ask(self.a, 'What is my revenue?').json()['answer'])

    def test_it_never_shows_another_sellers_product(self):
        d = self.ask(self.a, 'tell me about Rival Lamp and all stock').json()
        self.assertNotIn('Rival', str(d))

    def test_empty_question_is_rejected(self):
        self.assertEqual(self.ask(self.a, '  ').status_code, 400)


class SellerCreateProductTests(RoleViewTests):
    def test_seller_adds_a_product_with_no_fake_reviews(self):
        r = self.a.post('/api/seller/products', {'name': 'Steel Tiffin', 'category': 'Home', 'price': '350', 'stock': '12'}, format='json')
        self.assertEqual(r.status_code, 201)
        p = Product.objects.get(id=r.json()['id'])
        self.assertEqual((p.seller, p.rating, p.reviewCount, p.stock), ('Sita Stores', 0, 0, 12))

    def test_bad_input_and_wrong_roles(self):
        self.assertEqual(self.a.post('/api/seller/products', {'name': 'x', 'price': '-1', 'stock': 'a'}, format='json').status_code, 400)
        self.assertEqual(self.c.post('/api/seller/products', {'name': 'Steel Tiffin', 'category': 'Home', 'price': 5, 'stock': 1}, format='json').status_code, 403)
        self.assertEqual(self.guest.post('/api/seller/products', {}, format='json').status_code, 401)


class DashboardAndMemoryTests(RoleViewTests):
    def test_overview_has_chart_data_and_commission(self):
        d = self.a.get('/api/seller/overview').json()
        self.assertEqual(len(d['salesByDay']), 30)
        self.assertEqual(d['earnings'], {'gross': 1000, 'commission': 60, 'youKeep': 940})  # 'Home' is not a listed category, so the 6% default applies
        self.assertEqual(d['topProducts'][0]['name'], 'Flask')

    def test_commission_terms_are_public(self):
        t = APIClient().get('/api/commission').json()
        self.assertEqual((t['joiningFee'], t['listingFee'], t['monthlyFee']), (0, 0, 0))

    def test_chat_uses_the_name_and_remembers_then_forgets(self):
        r = self.c.post('/api/support/chat', {'message': 'show me a laptop under 50000'}, format='json').json()
        self.assertIn('Cathy', r['reply'])
        mem = self.c.get('/api/support/memory').json()
        self.assertEqual((mem['budgetMax'], 'Electronics' in mem['interests']), (50000, True))
        self.c.delete('/api/support/memory')
        self.assertEqual(self.c.get('/api/support/memory').json()['interests'], [])
        self.assertEqual(self.guest.get('/api/support/memory').status_code, 401)
