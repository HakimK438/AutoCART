"""
Seller assistant (Munim): a seller asks about their own shop and gets an answer built only from rows in the database.
It is instant and cannot invent data: sales analysis, product monitoring, price checks, stock forecasts and recommendations come
from seller_insights.py. A language model is used only for a question nothing here can place, and is given the same facts.
It only ever sees the signed-in seller's own products and the orders that contain them.
"""

import json
import re

from rest_framework import status as http
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .agents.llm_provider import UnifiedLLMProvider
from .models import Enquiry, Order, Product
from .role_views import LOW_STOCK, _seller_or_error
from .seller_analytics import analytics
from .seller_insights import build as build_insights

EXAMPLES = [
    'Analyse my sales this week',
    'What should I do next?',
    'Which products are not selling?',
    'Which products will run out soon?',
    'Are my prices right?',
    'What are my best selling products?',
    'What is my profit?',
    'How many orders are waiting?',
]

FLAG_TEXT = {
    'out_of_stock': 'Out of stock', 'low_stock': 'Running low', 'not_selling': 'Not selling', 'rising': 'Selling faster', 'falling': 'Slowing down',
    'overstocked': 'Overstocked', 'low_rating': 'Low rating', 'priced_high': 'Priced high', 'room_to_raise': 'Room to raise price',
    'thin_margin': 'Thin margin', 'no_cost': 'No cost price', 'weak_listing': 'Thin listing',
}
URGENT = ('out_of_stock', 'low_stock', 'low_rating', 'falling', 'priced_high', 'not_selling', 'overstocked', 'thin_margin', 'rising', 'room_to_raise')


def _has(text, *words):
    return any(w in text for w in words)


def _sales(products):
    """Units and revenue per product id, from non-cancelled orders."""
    ids = {p.id for p in products}
    units, money = {}, {}
    orders = []
    for o in Order.objects.exclude(status='Cancelled'):
        mine = [i for i in (o.items or []) if str(i.get('id')) in ids]
        if not mine:
            continue
        orders.append(o)
        for i in mine:
            pid = str(i.get('id'))
            q = int(i.get('quantity') or 0)
            units[pid] = units.get(pid, 0) + q
            money[pid] = money.get(pid, 0) + q * float(i.get('price') or 0)
    return units, money, orders


def _named(products, text):
    """Products the question names: the whole name, or at least two of its words. A short question may name one by a single word ("flask")."""
    short = len(text.split()) <= 3
    out = []
    for p in products:
        name = p.name.lower()
        words = [w for w in re.findall(r'[a-z0-9]{4,}', name)]
        hits = sum(1 for w in words if re.search(r'(?<![a-z0-9])' + re.escape(w) + r'(?![a-z0-9])', text))
        if name in text or hits >= 2 or (short and hits >= 1):
            out.append(p)
    return out


def _reply(answer, columns=None, rows=None, **extra):
    return {'answer': answer, 'columns': columns or [], 'rows': rows or [], 'matched': True, **extra}


def _recs_reply(ins, lead):
    recs = ins['recommendations']
    if not recs:
        return _reply(f'{lead} Nothing needs your attention right now. Keep stock topped up and keep an eye on new orders.')
    return _reply(f"{lead} Here is what I would do, most urgent first.", recommendations=recs)


def _worded_flags(row):
    return ', '.join(FLAG_TEXT[f] for f in row['flags'] if f in FLAG_TEXT and f in URGENT) or 'Healthy'


def answer(company, message):
    text = (message or '').lower().strip()
    products = list(Product.objects.filter(seller=company))
    if not products:
        return _reply('You have no products listed yet. Add a product with a photo and stock and I can start watching it for you.')
    units, money, orders = _sales(products)
    ins = build_insights(company, products)
    s, rows = ins['summary'], ins['products']
    by_id = {r['id']: r for r in rows}

    named = _named(products, text)
    if named and not _has(text, 'low', 'best', 'revenue', 'waiting', 'recommend', 'analy', 'summary', 'profit'):
        p = named[0]
        r = by_id[p.id]
        status = _worded_flags(r)
        left = f", about {r['daysLeft']} days of stock at the recent pace" if r['daysLeft'] is not None else ''
        return _reply(f"{p.name}: price ₹{p.price:,.0f}, {p.stock} in stock{left}, rated {p.rating:.1f} from {p.reviewCount} reviews, {units.get(p.id, 0)} sold through AutoCart ({r['sold30']} in the last 30 days). Status: {status}.",
                      ['Price', 'Stock', 'Rating', 'Sold'], [[f'₹{p.price:,.0f}', p.stock, f'{p.rating:.1f}', units.get(p.id, 0)]])

    if _has(text, 'recommend', 'suggest', 'advice', 'what should i', 'what to do', 'next step', 'improve', 'tips', 'grow', 'priority', 'priorities', 'action'):
        return _recs_reply(ins, 'Based on your sales, stock and orders.')

    if _has(text, 'analy', 'trend', 'summary', 'how am i doing', 'how is my', 'this week', 'growth', 'performance', 'report', 'insight', 'sales'):
        if not s['revenue7'] and not s['revenuePrev7']:
            a = analytics(products, 14)
            if not any(d['revenue'] for d in a['salesByDay']):
                return _reply('There are no sales in the last 14 days to analyse yet. Keep products in stock and priced fairly, and your first orders will show up here.',
                              recommendations=ins['recommendations'][:3])
        change = ('' if s['changePct'] is None else f", {'up' if s['changePct'] >= 0 else 'down'} {abs(s['changePct'])}% on the 7 days before (₹{s['revenuePrev7']:,})")
        top = max(rows, key=lambda r: r['sold7'] or r['sold30'])
        best = f" Best day: {s['bestDay']['label']} (₹{s['bestDay']['revenue']:,})." if s['bestDay'] else ''
        watch = [r for r in rows if any(f in r['flags'] for f in ('out_of_stock', 'low_stock')) and r['sold30']]
        warn = f" {len(watch)} product{'s' if len(watch) != 1 else ''} that sell need restocking." if watch else ''
        return _reply(f"Last 7 days: ₹{s['revenue7']:,} from {s['orders7']} order{'s' if s['orders7'] != 1 else ''}{change}. Average order ₹{s['avgOrder']:,}.{best} "
                      f"Top mover: {top['name']} ({top['sold30']} sold in 30 days).{warn}",
                      ['Period', 'Revenue', 'Units'], [['Last 7 days', f"₹{s['revenue7']:,}", s['units7']], ['Previous 7 days', f"₹{s['revenuePrev7']:,}", sum(d['units'] for d in s['series'][:7])]],
                      chart=[{'label': d['label'], 'value': d['revenue']} for d in s['series']], recommendations=ins['recommendations'][:3])

    if _has(text, 'not selling', "isn't selling", 'slow', 'dead', 'stuck', 'overstock', 'monitor', 'health', 'problem', 'attention', 'need a look', 'need help'):
        if _has(text, 'not selling', 'slow', 'dead', 'stuck', 'overstock', "isn't selling"):
            flagged = [r for r in rows if any(f in r['flags'] for f in ('not_selling', 'falling', 'overstocked'))]
            if not flagged:
                return _reply('Every product with stock has sold in the last 30 days. Nothing is stuck.')
            flagged.sort(key=lambda r: -(r['price'] * r['stock']))
            return _reply(f"{len(flagged)} product{'s' if len(flagged) != 1 else ''} are slow or stuck. Money tied up in the top one: ₹{flagged[0]['price'] * flagged[0]['stock']:,.0f}. A small discount, a better photo or a clearer description usually helps.",
                          ['Product', 'Status', 'Sold 30d', 'In stock'], [[r['name'], _worded_flags(r), r['sold30'], r['stock']] for r in flagged[:8]])
        watch = sorted((r for r in rows if any(f in r['flags'] for f in URGENT)), key=lambda r: [f in r['flags'] for f in URGENT].index(True))
        if not watch:
            return _reply(f'All {len(rows)} products look healthy: in stock, selling and fairly priced.')
        return _reply(f"{len(watch)} of your {len(rows)} products need a look. The most urgent are first.", ['Product', 'Status', 'Sold 30d', 'In stock'],
                      [[r['name'], _worded_flags(r), r['sold30'], r['stock']] for r in watch[:10]], recommendations=ins['recommendations'][:3])

    if _has(text, 'run out', 'running out', 'will last', 'how long', 'days left', 'forecast', 'when will', 'out of stock soon', 'soon'):
        cover = sorted((r for r in rows if r['daysLeft'] is not None), key=lambda r: r['daysLeft'])
        gone = [r for r in rows if r['stock'] <= 0 and r['sold30']]
        if not cover and not gone:
            return _reply('No product has sold recently, so I cannot forecast when anything runs out. Stock lasts as long as it stays unsold.')
        first = (gone or cover)[0]
        head = f"{first['name']} is already out." if gone else f"{first['name']} runs out first, in about {first['daysLeft']} day{'s' if first['daysLeft'] != 1 else ''}."
        return _reply(f"{head} This uses your last 30 days of sales, so a sale or festival will make it faster.", ['Product', 'In stock', 'Days left', 'Sold 30d'],
                      [[r['name'], r['stock'], 0 if r['stock'] <= 0 else r['daysLeft'], r['sold30']] for r in (gone + cover)[:8]])

    if _has(text, 'price', 'pricing', 'expensive', 'competit', 'market', 'too high', 'too low', 'cheaper'):
        check = [r for r in rows if r['categoryMedian']]
        flagged = [r for r in check if 'priced_high' in r['flags'] or 'room_to_raise' in r['flags']]
        if not check:
            return _reply('There are not enough similar products on AutoCart yet to compare your prices with.')
        if not flagged:
            return _reply('Your prices look in line with similar products on AutoCart. None is far above the usual price while unsold, or far below it while selling well.',
                          ['Product', 'Your price', 'Usual price'], [[r['name'], f"₹{r['price']:,.0f}", f"₹{r['categoryMedian']:,}"] for r in check[:6]])
        return _reply(f"{len(flagged)} product{'s' if len(flagged) != 1 else ''} may be priced wrongly compared with similar items on AutoCart.", ['Product', 'Your price', 'Usual price', 'What I see'],
                      [[r['name'], f"₹{r['price']:,.0f}", f"₹{r['categoryMedian']:,}", 'Too high, not selling' if 'priced_high' in r['flags'] else 'Selling well, could go up'] for r in flagged[:8]])

    if _has(text, 'low', 'stock', 'restock', 'running out', 'almost'):
        low = sorted([p for p in products if p.stock <= LOW_STOCK], key=lambda p: p.stock)
        if not low:
            return _reply(f'All {len(products)} products have more than {LOW_STOCK} in stock.')
        return _reply(f'{len(low)} product(s) need restocking. Start with {low[0].name} ({low[0].stock} left).', ['Product', 'In stock'], [[p.name, p.stock] for p in low[:8]])
    if _has(text, 'best sell', 'top sell', 'most sold', 'selling'):
        ranked = sorted(products, key=lambda p: units.get(p.id, 0), reverse=True)
        ranked = [p for p in ranked if units.get(p.id, 0)] or []
        if not ranked:
            return _reply('No orders contain your products yet, so there is no sales ranking to show.')
        return _reply(f'{ranked[0].name} is your best seller with {units[ranked[0].id]} unit(s) sold.', ['Product', 'Units sold', 'Revenue'],
                      [[p.name, units[p.id], f'₹{money[p.id]:,.0f}'] for p in ranked[:8]])
    if _has(text, 'profit', 'margin', 'make money', 'made money'):
        a = analytics(products)
        e, pr = a['earnings'], a['profit']
        if pr['costKnown']:
            msg = f"Profit so far is ₹{pr['amount']:,.0f}: sales minus AutoCart commission minus what your products cost you."
            if pr['productsWithoutCost']:
                msg += f" This leaves out {len(pr['productsWithoutCost'])} product(s) where you have not entered a cost price."
        else:
            msg = f"After AutoCart's commission you keep ₹{e['youKeep']:,.0f} from ₹{e['gross']:,.0f} of sales. To see true profit, enter what each product costs you in the Your products list (Cost price)."
        return _reply(msg, ['Sold', 'Commission', 'You keep'], [[f"₹{e['gross']:,.0f}", f"₹{e['commission']:,.0f}", f"₹{e['youKeep']:,.0f}"]])
    if _has(text, 'revenue', 'earn', 'income', 'sales so far'):
        total = sum(money.values())
        return _reply(f'₹{total:,.0f} from {sum(units.values())} unit(s) across {len(orders)} order(s). This is the item total, before delivery fees and payment charges.')
    if _has(text, 'order', 'waiting', 'pending', 'ship'):
        open_orders = [o for o in orders if o.status not in ('Delivered', 'Cancelled', 'Returned')]
        extra = f" {s['toPack']} can be packed now" + (f" and {s['toConfirm']} UPI payment{'s' if s['toConfirm'] != 1 else ''} need your confirmation." if s['toConfirm'] else '.') if open_orders else ''
        return _reply(f'{len(open_orders)} order(s) still open out of {len(orders)}.{extra}', ['Order', 'Status', 'Date'], [[o.id, o.status, o.date] for o in open_orders[:8]])
    if _has(text, 'rating', 'rated', 'review'):
        ranked = sorted(products, key=lambda p: (p.rating, p.reviewCount), reverse=True)[:5]
        return _reply(f'{ranked[0].name} has your best rating ({ranked[0].rating:.1f}).', ['Product', 'Rating', 'Reviews'], [[p.name, f'{p.rating:.1f}', p.reviewCount] for p in ranked])
    if _has(text, 'question', 'enquir', 'ask'):
        n = Enquiry.objects.filter(sellerName=company, status='OPEN').count()
        return _reply(f'{n} customer question(s) waiting. Answer them from the Questions section.' if n else 'No customer questions are waiting.')
    if _has(text, 'how many', 'products', 'listed', 'catalog'):
        return _reply(f'You have {len(products)} products listed.')
    return {'answer': "I can analyse your sales, watch your products (stock, slow movers, prices), forecast when stock runs out, and suggest what to do next. Try one of the examples, or name a product.",
            'columns': [], 'rows': [], 'matched': False}


SYSTEM = (
    "You are Munim, the AutoCart seller's shop-keeping assistant (munim means the traditional shop accountant). "
    "Answer the seller's question using ONLY the FACTS JSON. Use rupees (₹). Be specific: name products and numbers. "
    "Keep it under 70 words, warm and practical, and end with one concrete next step when useful. "
    "If the facts do not contain the answer, say so plainly. Never invent figures, customers or products."
)
_llm = UnifiedLLMProvider()


def _facts(company, products):
    a = analytics(products)
    ins = build_insights(company, products)
    return {
        'shop': company,
        'products': [{'name': r['name'], 'category': r['category'], 'price': r['price'], 'stock': r['stock'], 'rating': r['rating'], 'reviews': r['reviews'],
                      'sold30': r['sold30'], 'daysLeft': r['daysLeft'], 'flags': r['flags']} for r in ins['products'][:40]],
        'summary': {k: v for k, v in ins['summary'].items() if k != 'series'}, 'recommendations': ins['recommendations'],
        'topProducts': a['topProducts'], 'categoryMix': a['categoryMix'], 'earnings': a['earnings'], 'profit': a['profit'],
        'openQuestions': Enquiry.objects.filter(sellerName=company, status='OPEN').count(),
    }


def smart_answer(company, first, message):
    """The database answers every question it understands, instantly. Only an open-ended one goes to the language model, with the same facts."""
    base = answer(company, message)
    products = list(Product.objects.filter(seller=company))
    if base.get('matched') or not products or not _llm.is_configured:
        return {**base, 'provider': 'database'}
    prompt = f"Seller first name: {first}\nFACTS: {json.dumps(_facts(company, products), default=str)}\nQUESTION: {message}"
    out = _llm.generate(SYSTEM, prompt, 0.3, 400)
    if out.get('text'):
        return {**base, 'answer': out['text'].strip(), 'provider': out['provider']}
    return {**base, 'provider': 'database'}


@api_view(['POST'])
@permission_classes([AllowAny])
def seller_assistant_view(request):
    user, company, err = _seller_or_error(request)
    if err:
        return err
    message = str(request.data.get('message', ''))[:300]
    if not message.strip():
        return Response({'detail': 'Please type a question.'}, status=http.HTTP_400_BAD_REQUEST)
    first = (user.name or '').split()[0]
    return Response({**smart_answer(company, first, message), 'examples': EXAMPLES, 'assistant': 'Munim',
                     'source': 'Your products and orders in the AutoCart database'})
