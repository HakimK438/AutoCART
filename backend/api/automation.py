"""
Autopilot: the routine work the platform does by itself, so nobody repeats it by hand.

  Sellers   "Pack new orders for me": a payable order is confirmed and packed the moment it exists (or the moment its payment
            arrives). Stock is already reserved at checkout, so packing is the only thing left to click. Auto-restock lives in stock_rules.py.
  Admins    The application autopilot in triage.py prepares the routine decisions; what it ran is listed here too.
  Everyone  Every automatic action is written to AutomationEvent, so it can always be seen, and turned off.

Autopilot never moves an order past "Packed": sending it out and marking it delivered describe things that happen in the real world.
"""

from rest_framework import status as http
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import AutomationEvent, Order, Product, SellerApplication, StockLog
from .role_views import _seller_or_error
from .views import get_user_from_token

ONLINE = ('UPI (Scan & Pay)', 'Razorpay (Test Mode)')   # these are paid before packing
PACKABLE = ('Confirmed', 'Processing', 'Pending', 'Order Placed')


def record(scope: str, owner_id: str, kind: str, summary: str, ref: str = '') -> None:
    """Write one autopilot event. Never raises: a failed log line must not break the order or stock change that caused it."""
    try:
        AutomationEvent.objects.create(scope=scope, ownerId=owner_id or '', kind=kind, summary=summary[:300], refId=ref)
    except Exception:  # pragma: no cover
        pass


def owner_of(company: str) -> str:
    """The user id of the approved seller who trades as `company` ('' when unknown)."""
    app = SellerApplication.objects.filter(companyName=company, status='APPROVED').exclude(ownerUserId='').first()
    return app.ownerUserId if app else ''


def payable(order) -> bool:
    """Can this order be packed right now? Online payments must have arrived first."""
    return order.status in PACKABLE and (order.paymentMethod not in ONLINE or order.paymentStatus == 'Paid')


def _item_ids(order) -> list:
    return [str(i.get('id')) for i in (order.items or []) if isinstance(i, dict)]


def _companies(order) -> set:
    return {c for c in Product.objects.filter(id__in=_item_ids(order)).values_list('seller', flat=True) if c}


def _pack(order, name: str, how: str) -> None:
    from .seller_orders import _advance   # imported here to avoid a circular import with the views
    _advance(order, 'Packed', f'Packed {how} for {name}', 'Packed, ready for pickup', ['Packing'], 'Your order is packed',
             f'{name} has packed order {order.id}. It will be sent out shortly.')


def try_auto_pack(order) -> bool:
    """Pack `order` if every seller in it has turned on 'pack new orders for me'. Returns True when it did."""
    if not payable(order):
        return False
    companies = _companies(order)
    apps = {a.companyName: a for a in SellerApplication.objects.filter(companyName__in=companies, status='APPROVED')}
    if not companies or set(apps) != companies or not all(a.autoPackOrders for a in apps.values()):
        return False
    _pack(order, ' & '.join(sorted(companies)), 'automatically')
    for a in apps.values():
        record('seller', a.ownerUserId, 'auto_pack', f'Order {order.id} packed automatically ({order.paymentMethod}).', order.id)
    return True


def sweep() -> int:
    """Catch up: auto-pack every waiting order whose sellers have autopilot on. Run by `manage.py run_autopilot` (a scheduled job)."""
    return sum(try_auto_pack(o) for o in Order.objects.filter(status__in=PACKABLE).order_by('date', 'id'))


def _mine(company):
    """Orders waiting to be packed that contain this seller's products."""
    mine = set(Product.objects.filter(seller=company).values_list('id', flat=True))
    return [o for o in Order.objects.filter(status__in=PACKABLE).order_by('date', 'id') if payable(o) and mine.intersection(_item_ids(o))]


def pack_all(user, company) -> int:
    """One click for a seller: pack every one of their orders that is ready. Returns how many were packed."""
    orders = _mine(company)
    for o in orders:
        _pack(o, company, 'by')
    if orders:
        record('seller', user.id, 'pack_all', f'{len(orders)} order{"s" if len(orders) != 1 else ""} confirmed and packed with one click.')
    return len(orders)


def _row(e: AutomationEvent) -> dict:
    return {'id': e.id, 'kind': e.kind, 'summary': e.summary, 'refId': e.refId, 'createdAt': e.createdAt.isoformat()}


@api_view(['GET', 'PUT'])
@permission_classes([AllowAny])
def seller_automation_view(request):
    """A seller's autopilot: the on/off switch, what is waiting, and what it has already done for them."""
    user, company, err = _seller_or_error(request)
    if err:
        return err
    app = SellerApplication.objects.filter(ownerUserId=user.id, status='APPROVED').first()
    packed_now = 0
    if request.method == 'PUT' and app:
        app.autoPackOrders = bool(request.data.get('autoPackOrders'))
        app.save(update_fields=['autoPackOrders'])
        if app.autoPackOrders:  # switching it on also clears what is already waiting
            packed_now = pack_all(user, company)
    return Response({
        'autoPackOrders': bool(app and app.autoPackOrders),
        'autoRestockProducts': Product.objects.filter(seller=company, autoRestock=True).count(),
        'waitingToPack': len(_mine(company)),
        'packedNow': packed_now,
        'events': [_row(e) for e in AutomationEvent.objects.filter(scope='seller', ownerId=user.id)[:20]],
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def seller_pack_all_view(request):
    """Pack every ready order in one click."""
    user, company, err = _seller_or_error(request)
    if err:
        return err
    return Response({'packed': pack_all(user, company)})


@api_view(['GET'])
@permission_classes([AllowAny])
def admin_automation_view(request):
    """What autopilot has done across the marketplace, for the admin."""
    user = get_user_from_token(request)
    if not user or user.role not in ('ADMIN', 'STAFF'):
        return Response({'detail': 'Only an administrator can see this.'}, status=http.HTTP_403_FORBIDDEN)
    totals = {}
    for kind in AutomationEvent.objects.values_list('kind', flat=True):
        totals[kind] = totals.get(kind, 0) + 1
    return Response({
        'sellersOnAutopilot': SellerApplication.objects.filter(status='APPROVED', autoPackOrders=True).count(),
        'restocks': StockLog.objects.filter(reason='auto-restock').count(),
        'totals': totals,
        'events': [_row(e) for e in AutomationEvent.objects.all()[:30]],
    })
