"""Saathi (customer assistant) and Munim (seller assistant): understanding, product answers, phone numbers, nearby stock, sales analysis and recommendations.
The language model and the embedding model are switched off in tests, so every answer comes from the database."""

import datetime

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from api import nlu
from api.models import Enquiry, Order, OrderFulfillment, Product, Seller, SellerApplication, Store, StoreInventory, User
from api.views import generate_token


def authed(user):
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION='Bearer ' + generate_token(user))
    return c


class UnderstandingTests(TestCase):
    def test_budgets_in_everyday_words(self):
        self.assertEqual(nlu.parse_budget('phone under 20k'), (None, 20000))
        self.assertEqual(nlu.parse_budget('earbuds between 1000 and 2000'), (1000, 2000))
        self.assertEqual(nlu.parse_budget('1500-3000 shoes'), (1500, 3000))
        self.assertEqual(nlu.parse_budget('tv around 1.5 lakh'), (112500, 187500))
        self.assertEqual(nlu.parse_budget('above 5000 watch'), (5000, None))
        self.assertEqual(nlu.parse_budget('iphone 13 pro'), (None, None))  # a model number is not a price

    def test_sorting_and_the_product_words_left_over(self):
        self.assertEqual(nlu.parse_sort('cheapest laptop'), 'price_asc')
        self.assertEqual(nlu.parse_sort('best running shoes'), 'rating')
        self.assertEqual(nlu.clean_query('cheapest laptop under 50k'), 'laptop')

    def test_questions_phone_requests_and_pointing(self):
        self.assertEqual(nlu.aspects('does it have a warranty?'), {'warranty'})
        self.assertTrue(nlu.wants_phone('can you give me the seller phone number'))
        self.assertFalse(nlu.wants_phone('track order ORD-2026-1234 number'))
        self.assertTrue(nlu.needs_person('i need 50 pieces in bulk with a gst invoice'))
        self.assertEqual(nlu.reference('the second one', 3), '1')
        self.assertEqual(nlu.reference('the cheaper one', 3), 'cheapest')


class SaathiTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user(email='alice@example.com', name='Alice Rao', password='pw-12345')
        self.c = authed(self.alice)
        Seller.objects.create(id='s1', name='Kalyan Gadgets', companyName='Kalyan Gadgets', email='k@example.com', phone='9820011122', status='Approved')
        self.buds = Product.objects.create(id='p1', name='Zoom Earbuds', slug='zoom', category='Electronics', brand='Zoom', seller='Kalyan Gadgets', price=1499, originalPrice=2999,
                                           stock=12, rating=4.4, reviewCount=300, images=['http://x/zoom.jpg'], specifications={'Warranty': '1 year warranty'},
                                           description='Wireless earbuds with 40 hours battery playback.')
        Product.objects.create(id='p2', name='Pulse Earbuds', slug='pulse', category='Electronics', brand='Pulse', price=799, originalPrice=999, stock=5, rating=4.0, reviewCount=80, images=['http://x/pulse.jpg'])
        Product.objects.create(id='p3', name='Titan Laptop 15', slug='titan', category='Electronics', brand='Titan', price=55000, stock=4, rating=4.5, reviewCount=90)
        Product.objects.create(id='p4', name='Basic Laptop 14', slug='basic', category='Electronics', brand='Basic', price=32000, stock=4, rating=4.1, reviewCount=40)
        self.near = Store.objects.create(id='st1', name='AutoCart Smart Store — Kolsewadi', address='Pune Link Road', city='Kalyan', pincode='421306', latitude=19.2295, longitude=73.141, phone='+91 251 235 5005')
        StoreInventory.objects.create(id='i1', store=self.near, product=self.buds, availableQuantity=7, storePrice=1499)

    def chat(self, message, sid='', **extra):
        return self.c.post('/api/support/chat', {'message': message, 'sessionId': sid, **extra}, format='json').json()

    def test_cheapest_sorts_by_price_and_budget_ranges_work(self):
        r = self.chat('cheapest laptop')
        self.assertEqual([c['name'] for c in r['cards'] if c['type'] == 'product'], ['Basic Laptop 14', 'Titan Laptop 15'])
        r = self.chat('earbuds between 1000 and 2000')
        self.assertEqual([c['name'] for c in r['cards']], ['Zoom Earbuds'])

    def test_a_budget_nothing_fits_never_shows_unrelated_products(self):
        """Regression: "laptops under 50000" showed headphones and a pen. Look-alikes found by meaning joined the pool, the budget
        filter dropped the real (over-budget) laptops, and the cheap unrelated items were all that was left."""
        from unittest import mock
        from api import agent_graph
        by_meaning = lambda q, kind, k=12: [(0.9, {'kind': 'product', 'id': i, 'text': ''}) for i in ('p1', 'p2')] if kind == 'product' else []  # noqa: E731
        with mock.patch.object(agent_graph.INDEX, 'search', side_effect=by_meaning):
            r = self.chat('laptops under 20000')
        names = [c['name'] for c in r['cards'] if c['type'] == 'product']
        self.assertEqual(names, ['Basic Laptop 14', 'Titan Laptop 15'])  # the closest laptops, not earbuds
        self.assertIn('Nothing matches', r['reply'])

    def test_product_cards_carry_the_photo_and_a_badge(self):
        card = self.chat('earbuds')['cards'][0]
        self.assertEqual((card['image'], card['type']), ('http://x/zoom.jpg', 'product'))
        self.assertTrue(card['badge'])

    def test_a_follow_up_question_is_answered_from_the_product_it_is_about(self):
        first = self.chat('zoom earbuds')
        r = self.chat('does it have a warranty?', first['sessionId'])
        self.assertIn('1 year warranty', r['reply'])
        self.assertEqual(r['cards'][0]['id'], 'p1')
        r = self.chat('what is the battery life of the first one', first['sessionId'])
        self.assertIn('40 hours', r['reply'])

    def test_a_missing_detail_gets_a_phone_number_instead_of_a_guess(self):
        first = self.chat('zoom earbuds')
        r = self.chat('what is the screen size?', first['sessionId'])
        contact = next(c for c in r['cards'] if c['type'] == 'contact')
        phones = [ln['phone'] for ln in contact['lines']]
        self.assertIn('9820011122', phones)  # the seller of this product
        self.assertTrue(any('+91 22' in p for p in phones))  # AutoCart support
        self.assertIn('rather not guess', r['reply'])

    def test_phone_numbers_on_request_and_for_detailed_questions(self):
        r = self.chat('give me your customer care number')
        self.assertTrue(any(c['type'] == 'contact' for c in r['cards']))
        r = self.chat('i need 50 pieces in bulk with a gst invoice')
        self.assertTrue(any(c['type'] == 'contact' for c in r['cards']))

    def test_stock_near_the_shopper_uses_their_location(self):
        loc = {'lat': 19.229, 'lng': 73.142, 'pincode': '421306', 'area': 'Kolsewadi'}
        first = self.chat('zoom earbuds', location=loc)
        self.assertEqual(first['cards'][0]['near']['store'], 'Smart Store — Kolsewadi')
        r = self.chat('is it in stock near me?', first['sessionId'], location=loc)
        self.assertIn('Smart Store — Kolsewadi', r['reply'])
        far = self.chat('is it in stock near me?', first['sessionId'], location={'lat': 12.97, 'lng': 77.59, 'area': 'Bengaluru'})
        self.assertIn('No store within 25 km', far['reply'])

    def test_compare_uses_the_products_on_screen(self):
        first = self.chat('earbuds')
        r = self.chat('compare the first two', first['sessionId'])
        self.assertEqual([c['name'] for c in r['cards']], ['Zoom Earbuds', 'Pulse Earbuds'])
        self.assertIn('Cheapest', r['reply'])

    def test_order_cards_show_the_photo_the_store_and_what_can_still_be_done(self):
        Order.objects.create(id='ORD-2026-1111', customerName='Alice Rao', customerEmail='alice@example.com', date='2026-10-17', status='Confirmed', totalAmount=1499, paymentStatus='Pending',
                             items=[{'id': 'p1', 'name': 'Zoom Earbuds', 'price': 1499, 'quantity': 1, 'image': 'http://x/zoom.jpg'}])
        OrderFulfillment.objects.create(id='ful-1', order_id='ORD-2026-1111', store=self.near, estimatedDeliveryMinutes=28)
        card = self.chat('where is my order')['cards'][0]
        self.assertEqual((card['image'], card['store']['name'], card['etaMinutes'], card['canCancel'], card['canReturn']), ('http://x/zoom.jpg', 'Smart Store — Kolsewadi', 28, True, False))
        Order.objects.filter(id='ORD-2026-1111').update(status='Packed')
        self.assertFalse(self.chat('track ORD-2026-1111')['cards'][0]['canCancel'])  # the server refuses to cancel a packed order, so the chat does not offer it

    def test_a_typo_in_a_greeting_is_a_greeting_and_a_word_we_never_saw_finds_nothing(self):
        for word in ('heloo', 'helo', 'hey there', 'namste'):
            r = self.chat(word)
            self.assertEqual(r['cards'], [], word)
            self.assertIn('Tell me what you need', r['reply'])
        r = self.chat('asdfgh')
        self.assertEqual([c for c in r['cards'] if c['type'] == 'product'], [])
        self.assertIn('could not find', r['reply'])

    def test_policy_questions_get_one_short_answer(self):
        r = self.chat('how long does delivery take')
        self.assertIn('Delivery: most orders', r['reply'])
        self.assertEqual(r['cards'], [])


class MunimTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email='seller@example.com', name='Sita One', password='pw-12345', role='SELLER')
        SellerApplication.objects.create(id='app-1', ownerUserId=self.user.id, applicantName='Sita', companyName='Sita Stores', email=self.user.email, phone='9820012345', status='APPROVED')
        self.a = authed(self.user)
        mk = lambda pid, name, price, stock, cat='Home', **kw: Product.objects.create(id=pid, name=name, slug=pid, category=cat, seller='Sita Stores', price=price, stock=stock, **kw)  # noqa: E731
        self.hot = mk('h1', 'Steel Flask', 500, 4, description='A long enough description for a flask that keeps drinks hot.', images=['x.jpg'])
        self.dead = mk('d1', 'Brass Lamp', 900, 80, description='A long enough description for a brass lamp that looks good.', images=['x.jpg'])
        self.gone = mk('g1', 'Glass Jar', 150, 0, description='A long enough description for a jar with a tight lid.', images=['x.jpg'])
        for i in range(6):  # a median to compare prices with
            Product.objects.create(id=f'o{i}', name=f'Other {i}', slug=f'o{i}', category='Home', seller='Rival', price=300, stock=9)
        today = timezone.localdate()
        for n, (pid, qty, ago) in enumerate([('h1', 6, 1), ('h1', 4, 3), ('g1', 5, 2)]):
            Order.objects.create(id=f'ORD-{n}', customerName='Cathy', customerEmail='c@example.com', date=(today - datetime.timedelta(days=ago)).isoformat(), status='Confirmed',
                                 items=[{'id': pid, 'name': 'x', 'price': 500 if pid == 'h1' else 150, 'quantity': qty}])

    def ask(self, q):
        return self.a.post('/api/seller/assistant', {'message': q}, format='json').json()

    def test_sales_analysis_has_the_week_numbers_a_chart_and_actions(self):
        d = self.ask('analyse my sales this week')
        self.assertIn('₹5,750', d['answer'])  # 10 flasks x 500 + 5 jars x 150
        self.assertEqual(len(d['chart']), 14)
        self.assertTrue(d['recommendations'])

    def test_recommendations_are_ranked_and_explain_themselves(self):
        recs = self.ask('what should i do next?')['recommendations']
        titles = [r['title'] for r in recs]
        self.assertEqual(recs[0]['priority'], 'high')
        self.assertIn('Restock Glass Jar', titles)  # out of stock but it sold 5 this month
        self.assertIn('Restock Steel Flask soon', titles)  # 4 left at 10 sold in 30 days
        self.assertTrue(any('Brass Lamp' in t for t in titles))  # 80 on the shelf, nothing sold
        self.assertTrue(all(r['detail'] and r['link'].startswith('/seller/dashboard') for r in recs))

    def test_product_monitoring_lists_what_is_stuck_and_what_runs_out(self):
        stuck = self.ask('which products are not selling?')
        self.assertEqual([r[0] for r in stuck['rows']], ['Brass Lamp'])
        soon = self.ask('which products will run out soon?')
        self.assertEqual(soon['rows'][0][0], 'Glass Jar')
        self.assertIn('already out', soon['answer'])

    def test_price_check_compares_with_similar_products(self):
        d = self.ask('are my prices right?')
        self.assertEqual(d['rows'][0][0], 'Brass Lamp')  # 900 against a usual 300 and not selling
        self.assertIn('Too high', d['rows'][0][3])

    def test_a_named_product_gets_its_status(self):
        d = self.ask('brass lamp')
        self.assertIn('Not selling', d['answer'])

    def test_waiting_orders_and_questions_show_up_as_actions(self):
        Enquiry.objects.create(id='ENQ-1', productId='h1', productName='Steel Flask', sellerName='Sita Stores', customerName='Cathy', customerEmail='c@example.com', message='Is it hot?', status='OPEN')
        titles = [r['title'] for r in self.ask('recommend something')['recommendations']]
        self.assertIn('Pack 3 orders waiting', titles)
        self.assertIn('Answer 1 customer question', titles)


class ProductKindTests(TestCase):
    """Asking for one kind of product must never bring another kind (an "iphone" search showed a HomePod and a charger).
    When the named product is not stocked, the same kind from other brands is offered, and the reply says so."""

    def setUp(self):
        self.c = authed(User.objects.create_user(email='kind@example.com', name='Kind Tester', password='pw-12345'))
        for pid, name, brand, price, rating in (
            ('a1', 'iPhone 13 Pro', 'Apple', 90000, 4.1), ('a2', 'Apple HomePod Mini', 'Apple', 9500, 4.6), ('a3', 'Apple iPhone Charger', 'Apple', 1900, 4.0),
            ('a4', 'iPhone 12 Silicone Case', 'Apple', 2800, 4.0), ('s1', 'Samsung Galaxy S10', 'Samsung', 60000, 4.5), ('s2', 'Samsung Galaxy Tab S8', 'Samsung', 57000, 4.4),
            ('r1', 'Realme C35', 'Realme', 14000, 4.2), ('o1', 'OnePlus Nord CE 4', 'OnePlus', 25000, 4.3), ('h1', 'Sony Wireless Headphones', 'Sony', 29000, 4.7),
        ):
            Product.objects.create(id=pid, name=name, slug=pid, category='Electronics', brand=brand, price=price, stock=5, rating=rating, reviewCount=50)

    def ask(self, message):
        r = self.c.post('/api/support/chat', {'message': message, 'sessionId': ''}, format='json').json()
        return r['reply'], [c['name'] for c in r['cards'] if c['type'] == 'product']

    PHONES = {'iPhone 13 Pro', 'Samsung Galaxy S10', 'Realme C35', 'OnePlus Nord CE 4'}

    def test_kinds_are_read_from_names(self):
        from api import agent_graph as g
        self.assertEqual([g.query_kind(q) for q in ('iphone', 'phones', 'mobile', 'laptops', 'iphone charger', 'apple', 'sofa')], ['phone', 'phone', 'phone', 'laptop', 'accessory', '', ''])
        self.assertEqual([g.product_kind(Product.objects.get(id=i)) for i in ('a1', 'a2', 'a3', 's1', 's2', 'h1')], ['phone', 'speaker', 'accessory', 'phone', 'tablet', 'audio'])

    def test_iphone_brings_phones_and_never_a_speaker_charger_or_case(self):
        reply, names = self.ask('iphone')
        self.assertEqual(names[0], 'iPhone 13 Pro')
        self.assertTrue(set(names) <= self.PHONES, names)  # only one iPhone is stocked, so other brands' phones fill the list
        self.assertIn('similar phones from other brands', reply)

    def test_phones_means_phones_of_every_brand(self):
        for word in ('phones', 'phone', 'mobile'):
            reply, names = self.ask(word)
            self.assertEqual(set(names), self.PHONES, word)
            self.assertNotIn("We don't have", reply)  # the shopper asked for the kind itself: nothing is a substitute

    def test_a_brand_and_kind_lists_that_brands_phones_first(self):
        _, names = self.ask('samsung phone')
        self.assertEqual(names[0], 'Samsung Galaxy S10')
        self.assertNotIn('Samsung Galaxy Tab S8', names)  # a tablet is not a phone

    def test_a_brand_we_do_not_stock_gets_the_same_kind_from_other_brands(self):
        reply, names = self.ask('nokia phone')
        self.assertIn("We don't have", reply)
        self.assertEqual(set(names), self.PHONES)

    def test_a_budget_applies_to_the_substitutes_too(self):
        reply, names = self.ask('iphone under 20000')
        self.assertEqual(names, ['Realme C35'])  # the iPhone costs more, so only the in-budget phone is shown

    def test_an_accessory_search_returns_accessories_only(self):
        _, names = self.ask('iphone charger')
        self.assertEqual(names[0], 'Apple iPhone Charger')
        self.assertNotIn('iPhone 13 Pro', names)

    def test_a_model_we_do_not_stock_is_called_the_closest_not_a_match(self):
        reply, names = self.ask('iphone 17')
        self.assertIn("I don't have", reply)
        self.assertEqual(names[0], 'iPhone 13 Pro')

    def test_a_kind_we_have_none_of_shows_nothing_unrelated(self):
        reply, names = self.ask('laptop')
        self.assertEqual(names, [])
        self.assertIn('could not find', reply)
