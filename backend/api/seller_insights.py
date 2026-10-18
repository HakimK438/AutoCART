"""
Sales analysis, product monitoring and recommendations for one seller. Everything is computed from the seller's own products
and the orders that contain them, so Munim (the seller assistant) never has to guess.

    build(company, products) -> {
        'summary':         last 7 days vs the 7 before: revenue, orders, units, average order, best day, a 14-day series,
        'products':        one monitoring row per product: sold, days of stock left, status flags, price vs similar items,
        'recommendations': what to do next, most urgent first, each with a plain reason and a link into the seller centre,
    }
"""

import datetime
import statistics
from typing import Any, Dict, List

from django.utils import timezone

from .commission import fee_for
from .models import Enquiry, Order, Product

LOW_STOCK = 10
DONE = ('Delivered', 'Cancelled', 'Returned')
PACKABLE = ('Confirmed', 'Processing', 'Pending', 'Order Placed')
ONLINE = ('UPI (Scan & Pay)', 'Razorpay (Test Mode)')
WINDOW = 30


def _day(order):
    try:
        return datetime.date.fromisoformat(str(order.date)[:10])
    except ValueError:
        return None


def _inr(n: float) -> str:
    return f'₹{n:,.0f}'


def _category_medians() -> Dict[str, float]:
    by: Dict[str, List[float]] = {}
    for cat, price in Product.objects.filter(price__gt=0).values_list('category', 'price'):
        by.setdefault(cat, []).append(price)
    return {c: statistics.median(v) for c, v in by.items() if len(v) >= 5}


def build(company: str, products: List[Product]) -> Dict[str, Any]:
    today = timezone.localdate()
    ids = {p.id: p for p in products}
    sold = {pid: {'u30': 0, 'u7': 0, 'uPrev7': 0, 'rev30': 0.0, 'last': None} for pid in ids}
    series = {today - datetime.timedelta(days=i): {'revenue': 0.0, 'units': 0} for i in range(14)}
    mine, open_orders, to_pack, to_confirm, to_send, to_deliver = [], [], [], [], [], []
    for o in Order.objects.exclude(status='Cancelled'):
        lines = [i for i in (o.items or []) if str(i.get('id')) in ids]
        if not lines:
            continue
        mine.append(o)
        d = _day(o)
        if o.status not in DONE:
            open_orders.append(o)
            if o.status == 'Packed':
                to_send.append(o)
            elif o.status in ('Out for Delivery', 'Ready for Pickup'):
                to_deliver.append(o)
            if o.paymentMethod in ONLINE and o.paymentStatus == 'Verifying':
                to_confirm.append(o)
            elif o.status in PACKABLE and not (o.paymentMethod in ONLINE and o.paymentStatus != 'Paid'):
                to_pack.append(o)
        if d is None:
            continue
        age = (today - d).days
        for i in lines:
            pid, q = str(i.get('id')), int(i.get('quantity') or 0)
            amount = q * float(i.get('price') or 0)
            row = sold[pid]
            if 0 <= age < WINDOW:
                row['u30'] += q
                row['rev30'] += amount
                row['last'] = max(row['last'] or d, d)
            if 0 <= age < 7:
                row['u7'] += q
            elif 7 <= age < 14:
                row['uPrev7'] += q
            if d in series:
                series[d]['revenue'] += amount
                series[d]['units'] += q

    days = sorted(series.items())
    rev7, prev7 = sum(v['revenue'] for _, v in days[-7:]), sum(v['revenue'] for _, v in days[:7])
    orders7 = sum(1 for o in mine if (_day(o) and 0 <= (today - _day(o)).days < 7))
    units7 = sum(v['units'] for _, v in days[-7:])
    best = max(days, key=lambda kv: kv[1]['revenue'])
    summary = {
        'revenue7': round(rev7), 'revenuePrev7': round(prev7), 'changePct': round((rev7 - prev7) / prev7 * 100) if prev7 else None,
        'orders7': orders7, 'units7': units7, 'avgOrder': round(rev7 / orders7) if orders7 else 0,
        'bestDay': {'label': best[0].strftime('%d %b'), 'revenue': round(best[1]['revenue'])} if best[1]['revenue'] else None,
        'series': [{'label': d.strftime('%d %b'), 'revenue': round(v['revenue']), 'units': v['units']} for d, v in days],
        'openOrders': len(open_orders), 'toPack': len(to_pack), 'toConfirm': len(to_confirm), 'toSend': len(to_send), 'toDeliver': len(to_deliver),
    }

    medians = _category_medians()
    rows = []
    for p in products:
        s = sold[p.id]
        daily = s['u30'] / WINDOW
        cover = round(p.stock / daily) if daily > 0 else None
        median = medians.get(p.category)
        flags = []
        if p.stock <= 0:
            flags.append('out_of_stock')
        elif p.stock <= LOW_STOCK or (cover is not None and cover <= 7):
            flags.append('low_stock')
        if s['u30'] == 0 and p.stock > 0:
            flags.append('not_selling')
        if s['u7'] >= 2 and s['u7'] >= s['uPrev7'] * 1.5 and s['u7'] > s['uPrev7']:
            flags.append('rising')
        if s['uPrev7'] >= 2 and s['u7'] <= s['uPrev7'] * 0.5:
            flags.append('falling')
        if p.stock >= 40 and (cover is None or cover > 120):
            flags.append('overstocked')
        if p.rating and p.reviewCount >= 5 and p.rating < 3.8:
            flags.append('low_rating')
        if median and p.price > median * 1.3 and s['u30'] == 0:
            flags.append('priced_high')
        if median and p.price < median * 0.8 and s['u30'] >= 5:
            flags.append('room_to_raise')
        if p.costPrice > 0 and p.price > 0:
            margin = (p.price - fee_for(p.category, p.price) - p.costPrice) / p.price
            if margin < 0.10:
                flags.append('thin_margin')
        if s['u30'] > 0 and p.costPrice <= 0:
            flags.append('no_cost')
        if len((p.description or '').strip()) < 40 or not (p.images or []):
            flags.append('weak_listing')
        rows.append({'id': p.id, 'name': p.name, 'category': p.category, 'price': p.price, 'stock': p.stock, 'rating': p.rating, 'reviews': p.reviewCount,
                     'sold30': s['u30'], 'sold7': s['u7'], 'revenue30': round(s['rev30']), 'daysLeft': cover, 'categoryMedian': round(median) if median else None,
                     'flags': flags})
    return {'summary': summary, 'products': rows, 'recommendations': _recommend(company, rows, summary, products, sold)}


def _recommend(company: str, rows: List[Dict[str, Any]], summary: Dict[str, Any], products: List[Product], sold: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """The few things worth doing next, most urgent first. Each has a reason a shopkeeper can check against their own numbers."""
    recs: List[Dict[str, Any]] = []

    def add(priority, title, detail, tab, pid=''):
        recs.append({'priority': priority, 'title': title, 'detail': detail, 'link': f'/seller/dashboard?tab={tab}', 'productId': pid})

    if summary['toConfirm']:
        add('high', f"Confirm {summary['toConfirm']} UPI payment{'s' if summary['toConfirm'] > 1 else ''}", 'Customers have sent a UPI reference. Check your account, then confirm so the order can be packed.', 'orders')
    if summary['toPack']:
        add('high', f"Pack {summary['toPack']} order{'s' if summary['toPack'] > 1 else ''} waiting", 'Orders packed quickly get better ratings and fewer cancellations.', 'orders')
    if summary['toSend']:
        add('high', f"Send out {summary['toSend']} packed order{'s' if summary['toSend'] > 1 else ''}", 'They are packed but have not left the store. Press Out for delivery so the customer can follow it.', 'orders')
    if summary['toDeliver']:
        add('high', f"Mark {summary['toDeliver']} order{'s' if summary['toDeliver'] > 1 else ''} delivered", 'Once it reaches the customer, press Mark delivered. The sale is completed and the customer is told.', 'orders')
    for r in sorted((r for r in rows if 'out_of_stock' in r['flags'] and r['sold30']), key=lambda r: -r['revenue30'])[:2]:
        add('high', f"Restock {r['name']}", f"It is out of stock and sold {r['sold30']} in the last 30 days (about {_inr(r['revenue30'])}). Every day empty is a lost sale.", 'products', r['id'])
    for r in sorted((r for r in rows if 'low_stock' in r['flags'] and r['stock'] > 0 and r['sold30']), key=lambda r: (r['daysLeft'] if r['daysLeft'] is not None else 99))[:2]:
        left = f"about {r['daysLeft']} day{'s' if r['daysLeft'] != 1 else ''} of stock left" if r['daysLeft'] is not None else f"{r['stock']} left"
        add('high', f"Restock {r['name']} soon", f"{r['stock']} left, {left} at your recent pace.", 'products', r['id'])
    waiting = Enquiry.objects.filter(sellerName=company, status='OPEN').count()
    if waiting:
        add('medium', f"Answer {waiting} customer question{'s' if waiting > 1 else ''}", 'Quick answers turn questions into orders.', 'questions')
    for r in [r for r in rows if 'rising' in r['flags']][:2]:
        add('medium', f"{r['name']} is picking up", f"{r['sold7']} sold this week against fewer the week before. Keep it stocked, and consider an auto-restock rule.", 'products', r['id'])
    for r in [r for r in rows if 'falling' in r['flags']][:1]:
        add('medium', f"{r['name']} is slowing down", f"{r['sold7']} sold this week, down from the week before. Check its price and photo.", 'products', r['id'])
    dead = sorted((r for r in rows if 'not_selling' in r['flags']), key=lambda r: -(r['price'] * r['stock']))
    if dead:
        r = dead[0]
        tied = r['price'] * r['stock']
        add('medium', f"{r['name']} has not sold in 30 days", f"{r['stock']} units ({_inr(tied)}) are sitting on the shelf. Try a small discount, a better photo or a clearer description." + (f" {len(dead) - 1} more products are in the same state." if len(dead) > 1 else ''), 'products', r['id'])
    for r in [r for r in rows if 'priced_high' in r['flags']][:1]:
        add('medium', f"{r['name']} may be priced too high", f"It costs {_inr(r['price'])} against a usual {_inr(r['categoryMedian'])} for {r['category']}, and has not sold. A price near the usual range could help.", 'products', r['id'])
    for r in [r for r in rows if 'low_rating' in r['flags']][:1]:
        add('medium', f"Look into the low rating of {r['name']}", f"Rated {r['rating']:.1f}★ from {r['reviews']} reviews. Read the complaints and fix the cause, or update the listing so it sets the right expectations.", 'products', r['id'])
    for r in sorted((r for r in rows if 'room_to_raise' in r['flags']), key=lambda r: -r['sold30'])[:1]:
        add('low', f"You could raise the price of {r['name']}", f"It sells well ({r['sold30']} in 30 days) at {_inr(r['price'])}, below the usual {_inr(r['categoryMedian'])} for {r['category']}.", 'products', r['id'])
    for r in [r for r in rows if 'thin_margin' in r['flags']][:1]:
        add('low', f"Thin margin on {r['name']}", 'After AutoCart commission and your cost price, less than 10% of the price is left. Check the price or the cost.', 'products', r['id'])
    nocost = [r for r in rows if 'no_cost' in r['flags']]
    if nocost:
        add('low', 'Add cost prices to see your real profit', f"{len(nocost)} product{'s' if len(nocost) > 1 else ''} that sell have no cost price, starting with {nocost[0]['name']}.", 'products', nocost[0]['id'])
    weak = [r for r in rows if 'weak_listing' in r['flags']]
    if weak:
        add('low', 'Improve thin listings', f"{len(weak)} product{'s' if len(weak) > 1 else ''} have a short description or no photo, for example {weak[0]['name']}. Complete listings get more orders.", 'products', weak[0]['id'])
    order = {'high': 0, 'medium': 1, 'low': 2}
    recs.sort(key=lambda r: order[r['priority']])
    return recs[:8]
