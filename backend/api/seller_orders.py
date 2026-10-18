"""
Seller order handling. An order moves one step at a time: Confirm & pack -> Out for delivery (or Ready for pickup) -> Delivered.
Every step updates the customer's tracking and sends them a notification. The pickup-to-doorstep route is here too.

A seller only ever acts on orders that contain their own products. The pickup point is the seller's own store location
(from their approved application, or their store row), and the drop point is the location the customer shared at checkout.
"""

import math

from django.utils import timezone
from rest_framework import status as http
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Order, OrderFulfillment, Product, SellerApplication, Store
from .notifications import push
from .notify import send_email
from .role_views import _seller_or_error

PACKABLE = ('Confirmed', 'Processing', 'Pending', 'Order Placed')


def _km(a, b):
    """Straight-line distance in km between two (lat, lng) points."""
    r = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _num(v):
    try:
        f = float(v)
        return f if f else None
    except (TypeError, ValueError):
        return None


def pickup_for_company(company):
    """The pickup point of a seller found by company name (used when a customer looks at their own order)."""
    app = SellerApplication.objects.filter(companyName=company, status='APPROVED').first()
    if app and _num(app.storeLatitude) and _num(app.storeLongitude):
        return {'name': app.storeName or company, 'address': app.address or '', 'lat': app.storeLatitude, 'lng': app.storeLongitude}
    store = Store.objects.filter(seller=company).first()
    if store and store.latitude:
        return {'name': store.name, 'address': store.address, 'lat': store.latitude, 'lng': store.longitude}
    return None


def order_pickup(order):
    """Where this order is packed: the store it was allocated to, else where the first seller in it packs from."""
    ful = OrderFulfillment.objects.filter(order=order).select_related('store').first()
    if ful and ful.store and _num(ful.store.latitude):
        return {'name': ful.store.name, 'address': ful.store.address, 'lat': ful.store.latitude, 'lng': ful.store.longitude}
    for i in order.items or []:
        p = Product.objects.filter(id=str(i.get('id'))).first()
        if p and p.seller:
            found = pickup_for_company(p.seller)
            if found:
                return found
    return None


def pickup_point(user, company):
    """Where this seller packs from: their application's store pin, else a store row carrying their name."""
    app = SellerApplication.objects.filter(ownerUserId=user.id, status='APPROVED').first()
    if app and _num(app.storeLatitude) and _num(app.storeLongitude):
        return {'name': app.storeName or company, 'address': app.address or '', 'lat': app.storeLatitude, 'lng': app.storeLongitude}
    store = Store.objects.filter(seller=company).first()
    if store and store.latitude:
        return {'name': store.name, 'address': store.address, 'lat': store.latitude, 'lng': store.longitude}
    return None


def drop_point(order):
    """Where the order goes. Uses the pin the customer shared; without one, the centre of their PIN code or city, so a map can always be drawn."""
    from .location_service import resolve_coordinates
    a = order.shippingAddress or {}
    lat, lng = _num(a.get('latitude')), _num(a.get('longitude'))
    text = ', '.join(x for x in (a.get('addressLine'), a.get('city'), a.get('pinCode') or a.get('pincode')) if x)
    approx = False
    if not (lat and lng):
        hit = resolve_coordinates(str(a.get('pinCode') or a.get('pincode') or '')) or resolve_coordinates(str(a.get('city') or ''))
        if not hit:
            return None
        lat, lng, approx = hit[0], hit[1], True
    return {'name': order.customerName.split()[0] if order.customerName else 'Customer', 'address': text, 'lat': lat, 'lng': lng, 'approximate': approx}


def _my_order(company, order_id):
    order = Order.objects.filter(id=order_id).first()
    if not order:
        return None
    mine = set(Product.objects.filter(seller=company).values_list('id', flat=True))
    return order if any(str(i.get('id')) in mine for i in (order.items or [])) else None


def _tick(ful, word):
    """Mark the courier step whose name contains `word` as done, stamped with the time."""
    if not ful:
        return
    now = timezone.now().strftime('%I:%M %p')
    ful.timeline = [({**s, 'completed': True, 'time': now} if word.lower() in str(s.get('status')).lower() and not s.get('completed') else s) for s in (ful.timeline or [])]


def _advance(order, status, label, courier_status, words, title, body):
    """Move an order to its next stage: its status and timeline, the courier record, and a notification for the customer."""
    order.status = status
    order.timeline = list(order.timeline or []) + [{'status': label, 'time': timezone.now().strftime('%d %b %I:%M %p'), 'completed': True}]
    order.save(update_fields=['status', 'timeline', 'paymentStatus'])
    ful = OrderFulfillment.objects.filter(order=order).first()
    if ful:
        ful.currentStatus = courier_status
        for w in words:
            _tick(ful, w)
        ful.save(update_fields=['currentStatus', 'timeline'])
    push(order.customerEmail, title, body, order.id)
    return ful


def _is_pickup(order):
    a = order.shippingAddress or {}
    return bool(a.get('storeName')) and not a.get('addressLine')


@api_view(['POST'])
@permission_classes([AllowAny])
def seller_pack_order_view(request, order_id):
    """Step 1: the seller confirms the order is packed and ready. The customer's tracking updates and they get a notification."""
    user, company, err = _seller_or_error(request)
    if err:
        return err
    order = _my_order(company, order_id)
    if not order:
        return Response({'detail': 'Order not found.'}, status=http.HTTP_404_NOT_FOUND)
    if order.paymentMethod in ('UPI (Scan & Pay)', 'Razorpay (Test Mode)') and order.paymentStatus != 'Paid':
        return Response({'detail': 'This order is paid online and the payment has not arrived yet. For UPI, confirm the payment first.'}, status=http.HTTP_400_BAD_REQUEST)
    if order.status not in PACKABLE:
        return Response({'detail': f"This order is '{order.status}', so it cannot be marked packed now."}, status=http.HTTP_400_BAD_REQUEST)
    _advance(order, 'Packed', f'Packed by {company}', 'Packed, ready for pickup', ['Packing'], 'Your order is packed',
             f'{company} has packed order {order.id}. It will be sent out shortly.')
    return Response({'id': order.id, 'status': order.status})


@api_view(['POST'])
@permission_classes([AllowAny])
def seller_dispatch_order_view(request, order_id):
    """Step 2: the packed order leaves the store (out for delivery), or is ready for the customer to collect."""
    user, company, err = _seller_or_error(request)
    if err:
        return err
    order = _my_order(company, order_id)
    if not order:
        return Response({'detail': 'Order not found.'}, status=http.HTTP_404_NOT_FOUND)
    if order.status != 'Packed':
        return Response({'detail': f"This order is '{order.status}'. Pack it first, then send it out." if order.status in PACKABLE else f"This order is '{order.status}', so it cannot be sent out now."},
                        status=http.HTTP_400_BAD_REQUEST)
    ful = OrderFulfillment.objects.filter(order=order).first()
    if _is_pickup(order):
        _advance(order, 'Ready for Pickup', f'Ready for pickup at {company}', 'Ready for pickup', ['Out for'], 'Your order is ready to collect',
                 f'Order {order.id} is waiting for you at {company}. Bring your order number.')
    else:
        minutes = f' It should reach you in about {ful.estimatedDeliveryMinutes} minutes.' if ful and ful.estimatedDeliveryMinutes else ''
        _advance(order, 'Out for Delivery', f'Out for delivery from {company}', 'Out for Delivery', ['Out for'], 'Your order is on its way', f'Order {order.id} has left the store.{minutes}')
    return Response({'id': order.id, 'status': order.status})


@api_view(['POST'])
@permission_classes([AllowAny])
def seller_deliver_order_view(request, order_id):
    """Step 3: the order has reached the customer (or was collected). The sale is complete, cash is recorded as collected, and the customer is told."""
    user, company, err = _seller_or_error(request)
    if err:
        return err
    order = _my_order(company, order_id)
    if not order:
        return Response({'detail': 'Order not found.'}, status=http.HTTP_404_NOT_FOUND)
    if order.status not in ('Out for Delivery', 'Ready for Pickup'):
        return Response({'detail': f"This order is '{order.status}'. Send it out first, then mark it delivered."}, status=http.HTTP_400_BAD_REQUEST)
    pickup = _is_pickup(order)
    if order.paymentStatus == 'Pending':  # cash, pay at store, UPI or card on delivery: the money is collected at the door
        order.paymentStatus = 'Paid'
    names = ', '.join(str(i.get('name')) for i in (order.items or [])[:2] if isinstance(i, dict))
    _advance(order, 'Delivered', 'Collected by the customer' if pickup else f'Delivered by {company}', 'Delivered', ['Out for', 'Delivered'],
             'Your product has reached you' if not pickup else 'Thanks for collecting your order',
             f'{names or "Your order"} (order {order.id}) has {"been collected" if pickup else "been delivered"}. We hope you love it. If something is not right, you can return it within 7 days from the order page.')
    send_email(order.customerEmail, f'Your AutoCart order {order.id} has reached you', f'Hi {(order.customerName or "there").split()[0]},\n\nYour order {order.id} ({names}) has been delivered. Thank you for shopping local.\n\nIf something is not right, you can return it within 7 days from your orders page.')
    return Response({'id': order.id, 'status': order.status, 'paymentStatus': order.paymentStatus})


@api_view(['GET'])
@permission_classes([AllowAny])
def seller_order_route_view(request, order_id):
    """Pickup and drop points with the straight-line distance. The browser asks a free routing service for the road route."""
    user, company, err = _seller_or_error(request)
    if err:
        return err
    order = _my_order(company, order_id)
    if not order:
        return Response({'detail': 'Order not found.'}, status=http.HTTP_404_NOT_FOUND)
    pickup, drop = pickup_point(user, company), drop_point(order)
    km = round(_km((pickup['lat'], pickup['lng']), (drop['lat'], drop['lng'])), 1) if pickup and drop else None
    note = '' if pickup and drop else ('Add your store location in your seller profile.' if not pickup else 'The customer did not share a map location for this order.')
    return Response({'orderId': order.id, 'status': order.status, 'pickup': pickup, 'drop': drop, 'straightLineKm': km, 'note': note})
