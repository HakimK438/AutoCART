"""
Saathi's order desk: answers "where is my order", "track ORD-2026-12", "my orders", "cancel my order"
straight from the customer's own rows. It never falls back to a cart summary, and it never shows another person's order.
"""

import re
from typing import Any, Dict, Optional

from .models import Order, OrderFulfillment

TRACK_RE = re.compile(r"\b(track(ing)?|order status|status of|my orders?|mera order|delivery status|where('?s| is| are)\b.{0,25}\b(order|parcel|package|delivery|item|stuff)s?|"
                      r"kab (aayega|tak)|when will\b.{0,25}\b(arrive|come|reach|deliver|get here))\b", re.I)
ORDERS_RE = re.compile(r"\b(my orders?|orders? (list|history)|past orders?|previous orders?|mera order|all orders)\b", re.I)
RETURN_RE = re.compile(r"\b(return|refund|exchange|replace)\b", re.I)
CANCEL_RE = re.compile(r"\bcancel", re.I)
CART_RE = re.compile(r"\b(cart|subtotal|basket|bag)\b", re.I)
ORDER_ID_RE = re.compile(r"\bORD-\d{4}-\d{3,6}\b", re.I)

# A plain-language line for every order status.
STEP = {
    'Pending': 'It is waiting for payment or for the seller to confirm.',
    'Confirmed': 'The seller has confirmed it and is getting it ready.',
    'Processing': 'The seller is getting it ready.',
    'Packed': 'It is packed and ready to leave the store.',
    'Shipped': 'It is on its way to you.',
    'Ready for Pickup': 'It is ready for you to collect from the store.',
    'Out for Delivery': 'It is out for delivery and will reach you today.',
    'Delivered': 'It has been delivered.',
    'Cancelled': 'It was cancelled.',
    'Returned': 'It was returned.',
}


def wants_orders(text: str) -> Optional[str]:
    """'track', 'cancel', 'return' or None. Shopping phrases such as "order the iphone" are not order questions."""
    low = text.lower()
    if CART_RE.search(low) and not ORDER_ID_RE.search(text):
        return None
    if ORDER_ID_RE.search(text) or TRACK_RE.search(low) or ORDERS_RE.search(low):
        if re.search(r'\b(buy|purchase|add to)\b', low):
            return None
        return 'track'
    if (CANCEL_RE.search(low) or RETURN_RE.search(low)) and re.search(r'\b(my|the|this|last|latest|recent)\b.*\b(order|item|product|parcel)\b|\border\b|\ban? (item|product)\b', low):
        return 'cancel' if CANCEL_RE.search(low) else 'return'
    return None


def _card(o: Order) -> Dict[str, Any]:
    """What the chat shows for one order: its photo, items, status, the store packing it, the ETA and which actions are still open."""
    items = [i for i in (o.items or []) if isinstance(i, dict)]
    lines = [{'name': i.get('name') or '', 'image': i.get('image') or (i.get('images') or [''])[0], 'qty': int(i.get('quantity') or 1)} for i in items]
    first = lines[0]['name'] if lines else ''
    extra = f' + {len(lines) - 1} more' if len(lines) > 1 else ''
    ful = OrderFulfillment.objects.filter(order=o).select_related('store').first()
    store = ful.store if ful and ful.store else None
    done = o.status in ('Delivered', 'Cancelled', 'Returned')
    return {'type': 'order', 'id': o.id, 'status': o.status, 'date': o.date, 'total': o.totalAmount, 'payment': o.paymentStatus,
            'item': (first + extra).strip(), 'qty': lines[0]['qty'] if lines else 1, 'image': lines[0]['image'] if lines else '', 'items': lines[:3],
            'itemCount': len(lines), 'productId': str(items[0].get('id')) if items else '',
            'store': {'name': re.sub(r'^AutoCart\s+', '', store.name), 'phone': store.phone} if store else None,
            'etaMinutes': ful.estimatedDeliveryMinutes if ful and not done else None,
            'canCancel': o.status in ('Pending', 'Confirmed', 'Processing'), 'canReturn': o.status == 'Delivered'}


def _where(o: Order) -> str:
    """Which store has it, how far it still has to travel, and the courier step."""
    from .seller_orders import _km, drop_point, order_pickup
    try:
        pickup, drop = order_pickup(o), drop_point(o)
    except Exception:  # an order with no usable address still gets a status line
        return ''
    if not pickup:
        return ''
    text = f" It is with **{pickup['name']}**"
    if drop:
        text += f", about {_km((pickup['lat'], pickup['lng']), (drop['lat'], drop['lng'])):.1f} km from your delivery address"
    return text + '.'


def _courier(o: Order, email: str) -> str:
    from .agents import tools as tool_lib
    try:
        t = tool_lib.get_order_fulfillment_tracking(o.id, email)
    except Exception:
        return ''
    if t.get('error') or o.status in ('Delivered', 'Cancelled', 'Returned'):
        return ''
    bits = [f"Courier step: **{t['currentStatus']}**" if t.get('currentStatus') else '', f"about {int(t['estimatedMinutes'])} min away" if t.get('estimatedMinutes') else '']
    line = ', '.join(b for b in bits if b)
    return f' {line}.' if line else ''


def _describe(o: Order, email: str) -> str:
    return (f"Order **{o.id}** ({o.date}, ₹{o.totalAmount:,.0f}) is **{o.status}**. {STEP.get(o.status, '')}{_where(o)}{_courier(o, email)} "
            'Tap the order below to see the route on the map.')


def handle(kind: str, message: str, email: str, first_name: str = '') -> Dict[str, Any]:
    """Build the chat result for an order question. `email` is the signed-in customer; their orders only."""
    hello = f', {first_name}' if first_name else ''
    orders = list(Order.objects.filter(customerEmail__iexact=email).order_by('-date', '-id')[:10])
    if not orders:
        return {'agent': 'order-desk', 'reply': f"You have not placed any orders yet{hello}. When you do, I will track them here and show the route on a map. "
                                               'Want me to find something for you?',
                'cards': [], 'suggestedActions': ['Find a gift under ₹1,500', 'Show me popular products']}

    named = ORDER_ID_RE.search(message)
    chosen = next((o for o in orders if named and o.id.upper() == named.group(0).upper()), None)
    if named and not chosen:
        return {'agent': 'order-desk', 'reply': f"I could not find order {named.group(0).upper()} on your account. Here are your latest orders; pick one.",
                'cards': [_card(o) for o in orders[:3]], 'suggestedActions': [f'Track {o.id}' for o in orders[:3]]}

    open_orders = [o for o in orders if o.status not in ('Delivered', 'Cancelled', 'Returned')]
    if kind == 'cancel':
        target = chosen or (open_orders[0] if open_orders else None)
        if not target:
            return {'agent': 'order-desk', 'reply': 'None of your orders can be cancelled: they are all delivered, returned or already cancelled.',
                    'cards': [_card(orders[0])], 'suggestedActions': ['Return an item', 'Talk to a person']}
        ok = target.status in ('Pending', 'Confirmed', 'Processing')
        reply = (f"You can still cancel **{target.id}** because it has not left the store. Open it and press **Cancel order**: stock goes back and any online payment is marked for refund."
                 if ok else f"**{target.id}** is already out for delivery, so it can no longer be cancelled here. You can refuse it at the door, or I can bring in a person.")
        return {'agent': 'order-desk', 'reply': reply, 'cards': [_card(target)], 'suggestedActions': ['Talk to a person', 'Track my order']}

    if kind == 'return':
        delivered = [o for o in orders if o.status == 'Delivered']
        target = chosen or (delivered[0] if delivered else None)
        if not target:
            return {'agent': 'order-desk', 'reply': 'Returns open once an order is delivered, and you have 7 days after that. None of your orders are delivered yet.',
                    'cards': [_card(orders[0])], 'suggestedActions': ['Track my order', 'Talk to a person']}
        return {'agent': 'order-desk', 'reply': f"**{target.id}** was delivered, so you can return it within 7 days (unused, in original packaging). Open it and choose **Return**; refunds follow inspection.",
                'cards': [_card(target)], 'suggestedActions': ['Talk to a person', 'Track my order']}

    if chosen:
        return {'agent': 'order-desk', 'reply': _describe(chosen, email), 'cards': [_card(chosen)], 'suggestedActions': ['Track my order', 'Return an item', 'Talk to a person']}

    if ORDERS_RE.search(message) and len(orders) > 1:
        lines = '\n'.join(f"**{i}.** {o.id} · {o.status} · ₹{o.totalAmount:,.0f}" for i, o in enumerate(orders[:5], 1))
        return {'agent': 'order-desk', 'reply': f"Here are your latest orders{hello}:\n{lines}\n\nPick one below and I will show where it is.",
                'cards': [_card(o) for o in orders[:3]], 'suggestedActions': [f'Track {o.id}' for o in orders[:3]]}

    latest = (open_orders or orders)[0]
    extra = f"\n\nYou have {len(open_orders)} orders in progress. Say **my orders** to see them all." if len(open_orders) > 1 else ''
    return {'agent': 'order-desk', 'reply': _describe(latest, email) + extra, 'cards': [_card(latest)],
            'suggestedActions': ['My orders', 'Return an item', 'Talk to a person']}
