"""
Orders and payments.

Rules enforced on the server (the browser is never trusted for money):
- Prices, coupon discount, delivery fee and the total are worked out here from the database.
- Stock is checked and reduced inside one transaction, so two people cannot buy the last item.
- The order belongs to the signed-in user. Nobody else can see, track, return or cancel it.
- "Paid" only ever means a payment was verified. Cash on Delivery and Pay at Store stay "Pending".

Razorpay runs in TEST MODE only. With no keys in .env it runs a clearly labelled local demo of the
same flow (server-created order, signed result, server-side signature check). Live keys are refused.
"""

import datetime
import hashlib
import hmac
import os
import random
import uuid

import requests
from django.conf import settings
from django.db import transaction
from rest_framework import status as http
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .fulfillment_service import FulfillmentService
from .models import Coupon, InventoryReservation, Order, OrderFulfillment, Payment, Product, Store, User
from .serializers import OrderFulfillmentSerializer, OrderSerializer
from .views import get_user_from_token

ADMIN_ROLES = ('ADMIN', 'STAFF')
COD, STORE, RAZORPAY = 'Cash on Delivery', 'Pay at Store', 'Razorpay (Test Mode)'
PAYMENT_METHODS = (COD, STORE, RAZORPAY)
MAX_QTY = 20
CANCELLABLE = ('Pending', 'Confirmed', 'Processing')


# ---------------------------------------------------------------- helpers --

def _unauth():
    return Response({'detail': 'Please sign in to continue.'}, status=http.HTTP_401_UNAUTHORIZED)


def _order_for(request, order_id):
    """(order, user, error). Admins see any order; everyone else only their own. A stranger gets 404, not 403."""
    user = get_user_from_token(request)
    if not user:
        return None, None, _unauth()
    order = Order.objects.filter(id=order_id).first()
    if not order or (user.role not in ADMIN_ROLES and (order.customerEmail or '').lower() != user.email.lower()):
        return None, user, Response({'detail': 'Order not found.'}, status=http.HTTP_404_NOT_FOUND)
    return order, user, None


def coupon_discount(coupon: Coupon, subtotal: float) -> float:
    if coupon.discountType == 'Percentage':
        raw = subtotal * coupon.discountValue / 100.0
    else:
        raw = coupon.discountValue
    return round(min(raw, coupon.maxDiscount) if coupon.maxDiscount else raw)


def stock_label(stock: int) -> str:
    return 'Out of Stock' if stock <= 0 else ('Low Stock' if stock <= 10 else 'In Stock')


def delivery_fee(subtotal: float, coupon_code: str) -> float:
    if subtotal <= 0:
        return 0.0
    return 0.0 if subtotal > 499 or coupon_code == 'FREESHIP' else 40.0


# ------------------------------------------------------------ create order --

def create_order(request):
    user = get_user_from_token(request)
    if not user:
        return _unauth()
    data = request.data
    method = str(data.get('paymentMethod') or COD)
    if method not in PAYMENT_METHODS:
        return Response({'detail': f"Choose one of: {', '.join(PAYMENT_METHODS)}."}, status=http.HTTP_400_BAD_REQUEST)

    wanted = {}
    for row in data.get('items') or []:
        try:
            qty = int(row.get('quantity') or 1)
        except (TypeError, ValueError):
            qty = 0
        if not row.get('id') or not 1 <= qty <= MAX_QTY:
            return Response({'detail': f'Each item needs a valid quantity (1 to {MAX_QTY}).'}, status=http.HTTP_400_BAD_REQUEST)
        wanted[str(row['id'])] = wanted.get(str(row['id']), 0) + qty
    if not wanted:
        return Response({'detail': 'Your cart is empty.'}, status=http.HTTP_400_BAD_REQUEST)

    shipping = dict(data.get('shippingAddress') or {})
    store = Store.objects.filter(id=data.get('storeId') or shipping.get('storeId')).first()
    if store:
        shipping['storeId'], shipping['storeName'] = store.id, store.name
    if method == STORE and not store:
        return Response({'detail': 'Choose the store where you will pay and pick up.'}, status=http.HTTP_400_BAD_REQUEST)

    with transaction.atomic():
        products = {p.id: p for p in Product.objects.select_for_update().filter(id__in=wanted)}
        missing = [pid for pid in wanted if pid not in products]
        if missing:
            return Response({'detail': 'Some items are no longer available. Please review your cart.'}, status=http.HTTP_400_BAD_REQUEST)
        lines, subtotal = [], 0.0
        for pid, qty in wanted.items():
            p = products[pid]
            if p.stock < qty:
                msg = f'{p.name} is out of stock.' if p.stock <= 0 else f'Only {p.stock} of {p.name} left. Please lower the quantity.'
                return Response({'detail': msg}, status=http.HTTP_409_CONFLICT)
            lines.append({'id': p.id, 'name': p.name, 'brand': p.brand, 'category': p.category, 'price': p.price, 'quantity': qty,
                          'image': (p.images or [''])[0], 'images': p.images or []})
            subtotal += p.price * qty

        code = str(data.get('couponCode') or '').strip().upper()
        discount = 0.0
        if code:
            coupon = Coupon.objects.filter(code__iexact=code, status='Active').first()
            if not coupon or subtotal < coupon.minOrderAmount:
                return Response({'detail': 'That coupon is not valid for this order.'}, status=http.HTTP_400_BAD_REQUEST)
            discount = float(coupon_discount(coupon, subtotal))
        fee = delivery_fee(subtotal, code)
        total = max(0.0, subtotal - discount + fee)

        for pid, qty in wanted.items():
            p = products[pid]
            p.stock -= qty
            p.stockStatus = stock_label(p.stock)
            p.save(update_fields=['stock', 'stockStatus'])

        now = datetime.datetime.now()
        order_id = f"ORD-{now.year}-{random.randint(1000, 9999)}"
        while Order.objects.filter(id=order_id).exists():
            order_id = f"ORD-{now.year}-{random.randint(1000, 9999)}"
        timeline = [
            {'status': 'Order Placed', 'time': now.strftime('%I:%M %p'), 'completed': True},
            {'status': 'Confirmed' if method != RAZORPAY else 'Waiting for payment', 'time': now.strftime('%I:%M %p'), 'completed': method != RAZORPAY},
            {'status': 'Processing', 'time': '', 'completed': False},
            {'status': 'Out for Delivery' if method != STORE else 'Ready for pickup', 'time': '', 'completed': False},
            {'status': 'Delivered' if method != STORE else 'Picked up', 'time': '', 'completed': False},
        ]
        order = Order.objects.create(
            id=order_id, customerName=shipping.get('fullName') or user.name, customerEmail=user.email,
            customerPhone=shipping.get('phone') or user.phone, date=now.strftime('%Y-%m-%d'), totalAmount=total, subtotal=subtotal,
            tax=0.0, shippingFee=fee, discountAmount=discount, paymentMethod=method,
            paymentStatus='Awaiting Payment' if method == RAZORPAY else 'Pending',
            status='Pending' if method == RAZORPAY else 'Confirmed', shippingAddress=shipping, items=lines, timeline=timeline,
        )
        FulfillmentService.initiate_fulfillment(order, store=store, fulfillment_type='Store Pickup' if method == STORE else 'Store Delivery')
        user.ordersCount += 1
        user.totalSpent += total
        user.save(update_fields=['ordersCount', 'totalSpent'])

    body = OrderSerializer(order).data
    body['paymentRequired'] = method == RAZORPAY
    return Response(body, status=http.HTTP_201_CREATED)


# ------------------------------------------- tracking, return, cancellation --

@api_view(['GET'])
@permission_classes([AllowAny])
def order_tracking_view(request, order_id):
    order, _, err = _order_for(request, order_id)
    if err:
        return err
    fulfillment = OrderFulfillment.objects.filter(order=order).first() or FulfillmentService.initiate_fulfillment(order)
    data = OrderFulfillmentSerializer(fulfillment).data
    if fulfillment.store:
        data['storeLocation'] = {'name': fulfillment.store.name, 'address': fulfillment.store.address, 'latitude': fulfillment.store.latitude,
                                 'longitude': fulfillment.store.longitude, 'phone': fulfillment.store.phone}
    return Response(data)


@api_view(['POST'])
@permission_classes([AllowAny])
def order_return_view(request, order_id):
    order, _, err = _order_for(request, order_id)
    if err:
        return err
    if order.status not in ('Delivered', 'Completed'):
        return Response({'success': False, 'detail': f"Order {order.id} is '{order.status}'. Returns are only for delivered orders."},
                        status=http.HTTP_400_BAD_REQUEST)
    order.status = 'Return Requested'
    order.save(update_fields=['status'])
    return Response({'success': True, 'orderId': order.id, 'status': order.status,
                     'message': 'Return request accepted. Our team will contact you about pickup.',
                     'returnPolicy': '7-day window. Refunds are processed after inspection.'})


@api_view(['POST'])
@permission_classes([AllowAny])
def order_cancel_view(request, order_id):
    order, _, err = _order_for(request, order_id)
    if err:
        return err
    if order.status not in CANCELLABLE:
        return Response({'success': False, 'detail': f"Order {order.id} is '{order.status}' and can't be cancelled now."}, status=http.HTTP_400_BAD_REQUEST)
    with transaction.atomic():
        for line in order.items or []:  # put the stock back
            p = Product.objects.select_for_update().filter(id=line.get('id')).first()
            if p:
                p.stock += int(line.get('quantity') or 0)
                p.stockStatus = stock_label(p.stock)
                p.save(update_fields=['stock', 'stockStatus'])
        was_paid = order.paymentStatus == 'Paid'
        order.status = 'Cancelled'
        order.paymentStatus = 'Refund Pending' if was_paid else ('Cancelled' if order.paymentStatus in ('Awaiting Payment', 'Pending', 'Failed') else order.paymentStatus)
        order.save(update_fields=['status', 'paymentStatus'])
        for res in InventoryReservation.objects.filter(userEmail=order.customerEmail, status='Active'):
            FulfillmentService.release_stock_reservation(res.reservationToken, reason=f'Order {order.id} cancelled')
    return Response({'success': True, 'orderId': order.id, 'status': 'Cancelled',
                     'message': 'Your order is cancelled.' + (' Your payment will be refunded by our team.' if was_paid else '')})


# ---------------------------------------------------------------- Razorpay --

def _keys():
    return os.getenv('RAZORPAY_KEY_ID', '').strip(), os.getenv('RAZORPAY_KEY_SECRET', '').strip()


def _demo_mode() -> bool:
    key_id, secret = _keys()
    return not (key_id and secret)


def _secret() -> str:
    # In demo mode the server signs with a key derived from SECRET_KEY, so only this server can produce a valid signature.
    return _keys()[1] or hashlib.sha256(f'razorpay-demo:{settings.SECRET_KEY}'.encode()).hexdigest()


def _sign(razorpay_order_id: str, payment_id: str) -> str:
    return hmac.new(_secret().encode(), f'{razorpay_order_id}|{payment_id}'.encode(), hashlib.sha256).hexdigest()


@api_view(['GET'])
@permission_classes([AllowAny])
def payment_config_view(request):
    """Tells the checkout page which mode it is in. Never returns the secret."""
    key_id, _ = _keys()
    return Response({'provider': 'razorpay', 'mode': 'demo' if _demo_mode() else 'test', 'keyId': '' if _demo_mode() else key_id})


@api_view(['POST'])
@permission_classes([AllowAny])
def payment_create_view(request):
    order, _, err = _order_for(request, request.data.get('orderId'))
    if err:
        return err
    if order.paymentMethod != RAZORPAY or order.paymentStatus not in ('Awaiting Payment', 'Failed'):
        return Response({'detail': 'This order does not need an online payment.'}, status=http.HTTP_400_BAD_REQUEST)
    key_id, secret = _keys()
    if key_id.startswith('rzp_live_'):
        return Response({'detail': 'Live Razorpay keys are not allowed here. Use test keys (rzp_test_...).'}, status=http.HTTP_503_SERVICE_UNAVAILABLE)

    amount = int(round(order.totalAmount * 100))  # paise, always from the stored order
    if _demo_mode():
        rp_order, provider = f'order_demo_{uuid.uuid4().hex[:14]}', 'razorpay-demo'
    else:
        try:
            res = requests.post('https://api.razorpay.com/v1/orders', auth=(key_id, secret), timeout=15,
                                json={'amount': amount, 'currency': 'INR', 'receipt': order.id, 'notes': {'orderId': order.id}})
            res.raise_for_status()
            rp_order, provider = res.json()['id'], 'razorpay'
        except Exception:
            return Response({'detail': 'We could not reach the payment service. Please try again or choose another payment method.'},
                            status=http.HTTP_502_BAD_GATEWAY)
    Payment.objects.create(id=f'pay-{uuid.uuid4().hex[:10]}', orderId=order.id, provider=provider, providerOrderId=rp_order,
                           amount=order.totalAmount, status='CREATED')
    return Response({'orderId': order.id, 'razorpayOrderId': rp_order, 'amount': amount, 'currency': 'INR', 'keyId': '' if _demo_mode() else key_id,
                     'demo': _demo_mode(), 'name': 'AutoCart', 'description': f'Order {order.id}'})


@api_view(['POST'])
@permission_classes([AllowAny])
def payment_demo_sign_view(request):
    """Demo mode only: plays the part of the gateway and returns a signed result, as Razorpay's checkout would."""
    if not _demo_mode():
        return Response({'detail': 'Not available when Razorpay test keys are set.'}, status=http.HTTP_404_NOT_FOUND)
    order, _, err = _order_for(request, request.data.get('orderId'))
    if err:
        return err
    pay = Payment.objects.filter(orderId=order.id, providerOrderId=request.data.get('razorpayOrderId'), status='CREATED').first()
    if not pay:
        return Response({'detail': 'No pending payment for this order.'}, status=http.HTTP_400_BAD_REQUEST)
    if request.data.get('outcome') != 'success':
        return Response({'detail': 'The test payment was declined.', 'declined': True}, status=http.HTTP_402_PAYMENT_REQUIRED)
    payment_id = f'pay_demo_{uuid.uuid4().hex[:14]}'
    return Response({'razorpay_order_id': pay.providerOrderId, 'razorpay_payment_id': payment_id, 'razorpay_signature': _sign(pay.providerOrderId, payment_id)})


@api_view(['POST'])
@permission_classes([AllowAny])
def payment_verify_view(request):
    order, _, err = _order_for(request, request.data.get('orderId'))
    if err:
        return err
    rp_order = str(request.data.get('razorpay_order_id') or '')
    rp_payment = str(request.data.get('razorpay_payment_id') or '')
    signature = str(request.data.get('razorpay_signature') or '')
    pay = Payment.objects.filter(orderId=order.id, providerOrderId=rp_order, status='CREATED').first()
    if not pay:
        return Response({'detail': 'No pending payment found for this order.'}, status=http.HTTP_400_BAD_REQUEST)

    if not (rp_payment and signature and hmac.compare_digest(_sign(rp_order, rp_payment), signature)):
        pay.status = 'FAILED'
        pay.save(update_fields=['status'])
        order.paymentStatus = 'Failed'
        order.save(update_fields=['paymentStatus'])
        return Response({'detail': 'We could not confirm that payment. You have not been charged. Please try again.'}, status=http.HTTP_400_BAD_REQUEST)

    pay.status, pay.providerPaymentId = 'PAID', rp_payment
    pay.save(update_fields=['status', 'providerPaymentId'])
    order.paymentStatus, order.status = 'Paid', 'Confirmed'
    order.timeline = [({**t, 'status': 'Payment received', 'completed': True} if t.get('status') == 'Waiting for payment' else t) for t in (order.timeline or [])]
    order.save(update_fields=['paymentStatus', 'status', 'timeline'])
    return Response(OrderSerializer(order).data)


@api_view(['GET'])
@permission_classes([AllowAny])
def payment_admin_status_view(request):
    """Admin only: which Razorpay mode is on, whether Razorpay accepts the keys, and the latest payments. Never returns the secret."""
    user = get_user_from_token(request)
    if not user or user.role not in ADMIN_ROLES:
        return Response({'detail': 'Only an administrator can see this.'}, status=http.HTTP_403_FORBIDDEN)
    key_id, secret = _keys()
    live = key_id.startswith('rzp_live_')
    connection = None
    if key_id and secret and not live:
        try:
            res = requests.get('https://api.razorpay.com/v1/orders', params={'count': 1}, auth=(key_id, secret), timeout=10)
            if res.status_code == 200:
                connection = {'ok': True, 'message': 'Razorpay accepted your test keys.'}
            elif res.status_code in (401, 403):
                connection = {'ok': False, 'message': 'Razorpay rejected these keys. Check that the Key ID and Secret are a matching test pair.'}
            else:
                connection = {'ok': False, 'message': f'Razorpay answered with status {res.status_code}.'}
        except Exception:
            connection = {'ok': False, 'message': 'Could not reach Razorpay from this computer. Check your internet connection.'}
    recent = [{'id': p.id, 'orderId': p.orderId, 'provider': p.provider, 'amount': p.amount, 'status': p.status, 'createdAt': p.createdAt}
              for p in Payment.objects.order_by('-createdAt')[:20]]
    return Response({
        'mode': 'demo' if _demo_mode() else ('blocked' if live else 'test'),
        'keyIdHint': f'{key_id[:9]}...{key_id[-4:]}' if key_id and len(key_id) > 14 else '',
        'liveKeyBlocked': live, 'connection': connection, 'recent': recent,
    })
