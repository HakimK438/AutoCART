"""
Saathi's product desk: answers a shopper's questions about one product (or compares a few) from our own data, instantly.

Everything here comes from rows in the database: the product's price, stock, rating, specifications and description,
its seller, and the stores near the shopper. Nothing is invented. When a detail is not in our data the answer says so and
offers a phone number instead of guessing (see `contact_card`).
"""

import os
import re
import statistics
from typing import Any, Dict, List, Optional

from django.db.models import Q

from . import nlu
from .models import Product, Review, Seller, Store

SUPPORT_PHONE = os.getenv('SUPPORT_PHONE', '+91 22 4890 2278')
SUPPORT_HOURS = os.getenv('SUPPORT_HOURS', '9 AM to 9 PM, every day')

POLICY = [
    ('delivery', 'Delivery: most orders from nearby stores arrive the same day, often within an hour or two. The delivery fee and time are shown at checkout before you pay. Orders above ₹499 ship free.'),
    ('pickup', 'Pickup: you can collect an order from the store yourself. Choose Pay at Store at checkout and pick the store.'),
    ('payment', 'Payment: Cash on Delivery, UPI or card on delivery, Pay at Store, or Pay now with UPI straight to the seller. The seller confirms a UPI payment once it arrives.'),
    ('returns', 'Returns: delivered items can be returned within 7 days. Open your order and choose Return, or ask for a person. Refunds are processed after inspection.'),
    ('cancel', 'Cancelling: an order can be cancelled before it is out for delivery. Stock is put back and any online payment is marked for refund.'),
    ('tracking', 'Tracking: open Orders, then the order, to see each step and a map route from the store to you.'),
    ('sellers', 'Sellers: every product is sold by a local store. The product page shows which stores near you have it in stock.'),
    ('coupons', 'Coupons: enter a coupon code at checkout. The discount is worked out before you pay, and the order total shows it.'),
    ('help', 'Help: ask here, call us, or say talk to a person to open a support ticket with the full chat attached.'),
]

# Words in a product's own specification list that answer each kind of question.
SPEC_KEYS = {
    'warranty': ('warranty', 'guarantee'), 'return': ('return',), 'battery': ('battery', 'playback', 'backup', 'mah'), 'storage': ('storage', 'rom', 'capacity'),
    'ram': ('ram', 'memory'), 'display': ('display', 'screen', 'resolution'), 'camera': ('camera',), 'colour': ('colour', 'color'),
    'size': ('size', 'dimension', 'volume', 'capacity', 'length', 'width', 'height'), 'weight': ('weight',), 'material': ('material', 'fabric', 'ingredient'),
    'processor': ('processor', 'cpu', 'chip'),
}
DESC_STEMS = {
    'warranty': ('warranty', 'guarantee'), 'battery': ('battery', 'mah', 'hours of'), 'storage': ('storage', ' gb', ' tb'), 'ram': (' ram',),
    'display': ('display', 'screen', 'inch', 'oled'), 'camera': ('camera', 'megapixel'), 'colour': ('colour', 'color'), 'size': ('size', 'dimension', 'fit'),
    'weight': ('weight', 'lightweight', 'light '), 'material': ('made of', 'made from', 'material', 'fabric', 'cotton', 'leather', 'steel'), 'processor': ('processor', 'chip'),
}
LABEL = {'warranty': 'Warranty', 'return': 'Returns', 'battery': 'Battery', 'storage': 'Storage', 'ram': 'RAM', 'display': 'Display', 'camera': 'Camera',
         'colour': 'Colour', 'size': 'Size', 'weight': 'Weight', 'material': 'Material', 'processor': 'Processor'}
HIDDEN_SPECS = {'source price (usd)', 'usd to inr rate used'}
SPEC_ASPECTS = tuple(LABEL)
ANSWER_ORDER = ['warranty', 'return', 'battery', 'storage', 'ram', 'display', 'camera', 'colour', 'size', 'weight', 'material', 'processor',
                'stock', 'delivery', 'price', 'payment', 'seller', 'reviews']

THEMES = {'battery': r'battery', 'sound': r'sound|bass|audio|volume', 'build quality': r'quality|build|sturdy|durable|solid', 'value for money': r'value|worth|price|money',
          'delivery': r'deliver|packag|arriv', 'fit and comfort': r'comfort|fit|size|soft', 'looks': r'look|design|colou?r|style'}


def inr(n: float) -> str:
    return f'₹{float(n or 0):,.0f}'


def short_store(name: str) -> str:
    return re.sub(r'^AutoCart\s+', '', name or '').strip()


def product_dict(p: Product) -> Dict[str, Any]:
    return {'id': p.id, 'name': p.name, 'price': p.price, 'originalPrice': p.originalPrice, 'rating': p.rating, 'reviewCount': p.reviewCount,
            'stock': p.stock, 'images': p.images or [], 'category': p.category, 'brand': p.brand, 'seller': p.seller}


# ---------------------------------------------------------------- stores near --

def clean_location(raw: Any) -> Optional[Dict[str, Any]]:
    """The shopper's saved location from the browser, or None. Only numbers and short text are kept."""
    if not isinstance(raw, dict):
        return None
    try:
        lat, lng = float(raw.get('lat')), float(raw.get('lng'))
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        return None
    return {'lat': lat, 'lng': lng, 'pincode': str(raw.get('pincode') or '')[:10], 'area': str(raw.get('area') or raw.get('city') or '')[:60]}


def nearest_stores(product_id: str, loc: Optional[Dict[str, Any]], limit: int = 3, radius_km: float = 25.0) -> List[Dict[str, Any]]:
    """Open stores within `radius_km` of the shopper that have this product, nearest first."""
    if not loc:
        return []
    from .location_service import find_nearby_stores_with_inventory
    return find_nearby_stores_with_inventory(product_id=product_id, customer_lat=loc['lat'], customer_lng=loc['lng'], max_radius_km=radius_km)[:limit]


def near_map(product_ids: List[str], loc: Optional[Dict[str, Any]], radius_km: float = 25.0) -> Dict[str, Dict[str, Any]]:
    """For each product, the nearest open store within `radius_km` that has it: {product_id: {store, km, minutes, phone}}. Two queries in all."""
    if not loc or not product_ids:
        return {}
    from .location_service import haversine_distance_km
    from .models import StoreInventory
    near = {}
    for s in Store.objects.filter(operatingStatus='Open').exclude(latitude=0):
        d = haversine_distance_km(loc['lat'], loc['lng'], s.latitude, s.longitude)
        if d <= radius_km:
            near[s.id] = (d, s)
    best: Dict[str, Dict[str, Any]] = {}
    rows = StoreInventory.objects.filter(store_id__in=list(near), product_id__in=list(product_ids), isAvailable=True, availableQuantity__gt=0).values_list('product_id', 'store_id')
    for pid, sid in rows:
        d, store = near[sid]
        if pid not in best or d < best[pid]['km']:
            best[pid] = {'store': short_store(store.name), 'km': round(d, 1), 'minutes': max(25, int(d * 3.2) + 15), 'phone': store.phone}
    return best


def near_info(product_id: str, loc: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return near_map([product_id], loc).get(product_id)


# ------------------------------------------------------------------ contact --

def seller_phone(p: Optional[Product]) -> str:
    if not p or not p.seller:
        return ''
    seller = Seller.objects.filter(Q(name=p.seller) | Q(companyName=p.seller)).exclude(phone='').first()
    if seller:
        return seller.phone
    store = Store.objects.filter(seller=p.seller).exclude(phone='').first()
    return store.phone if store else ''


def contact_card(product: Optional[Product] = None, loc: Optional[Dict[str, Any]] = None, title: str = 'Talk to a person') -> Dict[str, Any]:
    """Phone numbers for the shopper: AutoCart support, the product's store near them, and its seller."""
    lines = [{'label': 'AutoCart support', 'phone': SUPPORT_PHONE, 'note': SUPPORT_HOURS}]
    if product:
        near = near_info(product.id, loc)
        if near and near['phone']:
            lines.append({'label': near['store'], 'phone': near['phone'], 'note': f"Store with it, {near['km']} km from you"})
        phone = seller_phone(product)
        if phone and all(phone != ln['phone'] for ln in lines):
            lines.append({'label': product.seller, 'phone': phone, 'note': 'Seller of this product'})
    return {'type': 'contact', 'id': 'contact', 'title': title, 'lines': lines}


# ------------------------------------------------------------------ answers --

def _specs(p: Product) -> List[tuple]:
    specs = p.specifications if isinstance(p.specifications, dict) else {}
    return [(str(k), str(v)) for k, v in specs.items() if str(k).lower() not in HIDDEN_SPECS and v not in ('', None)]


def spec_answer(p: Product, aspect: str) -> Optional[str]:
    """What the product's own specifications (or, failing that, its description) say about one aspect."""
    keys = SPEC_KEYS.get(aspect, (aspect,))
    hits = [(k, v) for k, v in _specs(p) if any(w in k.lower() for w in keys)]
    if hits:
        return hits[0][1] if len(hits) == 1 else '; '.join(f'{k}: {v}' for k, v in hits[:3])
    for sentence in re.split(r'(?<=[.!?])\s+', p.description or ''):
        low = sentence.lower()
        if any(s in low for s in DESC_STEMS.get(aspect, keys)):
            return sentence.strip()
    return None


def _peers(p: Product) -> List[Product]:
    return list(Product.objects.filter(category=p.category).exclude(id=p.id)[:200])


def verdict(rating: float) -> str:
    return 'excellent' if rating >= 4.5 else 'very good' if rating >= 4.2 else 'good' if rating >= 3.8 else 'mixed' if rating >= 3.0 else 'poor'


def review_lines(p: Product) -> List[str]:
    """Rating, what written reviews praise or complain about (only when there are some), and how it compares with similar products."""
    lines: List[str] = []
    if p.reviewCount and p.rating:
        lines.append(f'Rated **{p.rating:.1f}★** from {p.reviewCount:,} reviews, which is {verdict(p.rating)}.')
        rated = [x.rating for x in _peers(p) if x.reviewCount and x.rating]
        if len(rated) >= 5:
            avg = statistics.mean(rated)
            if p.rating - avg >= 0.25:
                lines.append(f'That is above the usual {avg:.1f}★ for {p.category}.')
            elif avg - p.rating >= 0.25:
                lines.append(f'That is below the usual {avg:.1f}★ for {p.category}.')
    else:
        lines.append('It has no ratings yet, so there is nothing to go on beyond its details.')
    rows = list(Review.objects.filter(productId=p.id)[:60])
    if len(rows) >= 2:
        def themes(batch):
            text = ' '.join(f'{r.title} {r.body}' for r in batch).lower()
            return [t for t, rx in THEMES.items() if re.search(rx, text)]
        liked, disliked = themes([r for r in rows if r.rating >= 4]), themes([r for r in rows if r.rating <= 2])
        if liked:
            lines.append('Buyers like: ' + ', '.join(liked[:3]) + '.')
        if disliked:
            lines.append('Complaints mention: ' + ', '.join(disliked[:3]) + '.')
    elif p.reviewCount:
        lines.append('There are no written reviews on AutoCart yet, only star ratings.')
    return lines


def price_line(p: Product) -> str:
    bits = [f'{inr(p.price)}']
    if p.originalPrice and p.originalPrice > p.price:
        off = round((p.originalPrice - p.price) / p.originalPrice * 100)
        bits.append(f'{off}% off the {inr(p.originalPrice)} list price')
    prices = [x.price for x in _peers(p) if x.price]
    if len(prices) >= 5:
        mid = statistics.median(prices)
        if mid and p.price <= mid * 0.85:
            bits.append(f'cheaper than most {p.category} items (usual {inr(mid)})')
        elif mid and p.price >= mid * 1.25:
            bits.append(f'pricier than most {p.category} items (usual {inr(mid)})')
    return ', '.join(bits) + '.'


def stock_line(p: Product, loc: Optional[Dict[str, Any]]) -> str:
    if p.stock <= 0:
        return 'It is out of stock right now. I can look for something similar.'
    head = f'In stock ({p.stock} left).' if p.stock <= 10 else 'In stock.'
    stores = nearest_stores(p.id, loc, 2)
    if stores:
        s = stores[0]
        more = f' {len(stores) - 1} more store nearby has it too.' if len(stores) > 1 else ''
        return f"{head} Nearest store: **{short_store(s['storeName'])}**, {s['distanceKm']} km away, about {s['estimatedMinutes']} min to you.{more}"
    if loc:
        return f'{head} No store within 25 km of {loc.get("area") or "you"} has it right now, so delivery would come from further away.'
    return f'{head} Set your location (top of the page) and I will tell you the nearest store that has it.'


def delivery_line(p: Product, loc: Optional[Dict[str, Any]]) -> str:
    stores = nearest_stores(p.id, loc, 1)
    if stores:
        s = stores[0]
        fee = 'free delivery' if not s['deliveryFee'] else f"delivery {inr(s['deliveryFee'])}"
        return f"From **{short_store(s['storeName'])}** ({s['distanceKm']} km): about {s['estimatedMinutes']} minutes, {fee}. Or pick it up yourself."
    return 'Delivery time depends on the nearest store that has it. Set your location and I will give you the exact time, or pick it up from a store.'


def seller_line(p: Product, loc: Optional[Dict[str, Any]]) -> str:
    bits = [f'Sold by **{p.seller}**' if p.seller else 'Sold by a local store']
    if p.brand:
        bits.append(f'brand {p.brand}')
    near = near_info(p.id, loc)
    if near:
        bits.append(f"packed by {near['store']} near you")
    return ', '.join(bits) + '.'


def overview(p: Product, loc: Optional[Dict[str, Any]]) -> str:
    """A short, honest review: rating, value, stock, and the first spec that matters."""
    lines = [f'**{p.name}**' + (f' by {p.brand}' if p.brand else '') + '.']
    lines += review_lines(p)
    lines.append(f'Price: {price_line(p)}')
    lines.append(stock_line(p, loc))
    return '\n'.join(lines)


def answer_about(p: Product, asked: set, loc: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Reply for questions about one product. `missing` lists details we do not have, so the caller can offer a phone number."""
    parts: List[str] = []
    missing: List[str] = []
    for a in ANSWER_ORDER:
        if a not in asked:
            continue
        if a in SPEC_ASPECTS:
            found = spec_answer(p, a)
            if found:
                parts.append(f'**{LABEL[a]}:** {found}')
            else:
                missing.append(LABEL[a].lower())
        elif a == 'return':
            parts.append('**Returns:** delivered items can be returned within 7 days, unused and in original packaging.')
        elif a == 'stock':
            parts.append(stock_line(p, loc))
        elif a == 'delivery':
            parts.append(delivery_line(p, loc))
        elif a == 'price':
            parts.append(f'**Price:** {price_line(p)}')
        elif a == 'payment':
            parts.append('**Payment:** cash on delivery, UPI or card on delivery, pay at the store, or pay now with UPI to the seller.')
        elif a == 'seller':
            parts.append(seller_line(p, loc))
        elif a == 'reviews':
            parts.extend(review_lines(p))
    only_reviews = asked <= {'reviews'}
    if only_reviews or not (parts or missing):
        return {'reply': overview(p, loc), 'missing': []}
    reply = f'About **{p.name}**:\n' + '\n'.join(parts) if parts else f'About **{p.name}**:'
    if missing:
        reply += f"\nI do not have its {', '.join(missing)} listed, and I would rather not guess. The seller can tell you exactly, so call below."
    return {'reply': reply.strip(), 'missing': missing}


def compare(prods: List[Product]) -> str:
    """A side-by-side summary of up to three products and a pick, using price, rating, discount and stock."""
    prods = prods[:3]
    lines = ['**Side by side:**']
    for i, p in enumerate(prods, 1):
        off = f', {round((p.originalPrice - p.price) / p.originalPrice * 100)}% off' if p.originalPrice and p.originalPrice > p.price else ''
        rating = f'{p.rating:.1f}★ ({p.reviewCount:,})' if p.reviewCount else 'no ratings yet'
        stock = 'in stock' if p.stock > 0 else 'out of stock'
        lines.append(f'**{i}.** {p.name}: {inr(p.price)}{off}, {rating}, {stock}')
    live = [p for p in prods if p.stock > 0] or prods
    cheapest = min(live, key=lambda p: p.price)
    best = max(live, key=lambda p: ((p.rating or 0) * min(1.0, (p.reviewCount or 0) / 50 + 0.5), -p.price))
    if best.id == cheapest.id:
        lines.append(f'My pick: **{best.name}**. It is the cheapest and the best rated of these.')
    else:
        extra = best.price - cheapest.price
        lines.append(f'Cheapest: **{cheapest.name}**. Best rated: **{best.name}** ({inr(extra)} more). My pick: the best rated one if the extra {inr(extra)} is fine, else the cheapest.')
    return '\n'.join(lines)
