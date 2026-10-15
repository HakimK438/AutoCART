import jwt
import datetime
from django.conf import settings
from django.db.models import Q
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, BasePermission, SAFE_METHODS

from .models import (
    User, Category, Product, Coupon, Seller, Order,
    Store, StoreInventory, InventoryReservation,
    SellerApplication, SellerApplicationAudit, OrderFulfillment,
    AgentTask, AgentExecutionLog
)
from .serializers import (
    UserSerializer,
    CategorySerializer,
    ProductSerializer,
    CouponSerializer,
    SellerSerializer,
    OrderSerializer,
    StoreSerializer,
    StoreInventorySerializer,
    InventoryReservationSerializer,
    SellerApplicationSerializer,
    SellerApplicationAuditSerializer,
    OrderFulfillmentSerializer,
    AgentTaskSerializer,
)
from .ai_engine import discovery_agent, customer_engagement_agent, seller_onboarding_agent
from .agents.engine import AgentEngine
from .fulfillment_service import FulfillmentService
from .location_service import (
    find_nearby_stores_with_inventory,
    resolve_coordinates,
    haversine_distance_km,
    get_mumbai_zones_summary
)
from .ocr_service import DocumentOCRService

orchestrator = AgentEngine()

JWT_SECRET = getattr(settings, 'SECRET_KEY', 'autocart-jwt-secret-key')
JWT_ALGORITHM = 'HS256'

def generate_token(user):
    payload = {
        'id': user.id,
        'email': user.email,
        'role': user.role,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7),
        'iat': datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def get_user_from_token(request):
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ')[1]
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user = User.objects.filter(id=payload.get('id')).first()
            return user
        except Exception:
            return None
    return None

ADMIN_ROLES = ('ADMIN', 'STAFF')


from rest_framework.throttling import AnonRateThrottle  # noqa: E402


class LoginThrottle(AnonRateThrottle):
    rate = '20/min'  # slows down password guessing


class IsAdminToken(BasePermission):
    """Only a signed-in ADMIN / STAFF user."""
    def has_permission(self, request, view):
        user = get_user_from_token(request)
        return bool(user and user.role in ADMIN_ROLES)


class ReadOnlyOrAdmin(BasePermission):
    """Anyone can read; only admins can change."""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = get_user_from_token(request)
        return bool(user and user.role in ADMIN_ROLES)


class ReadOnlyOrStaffOrSeller(BasePermission):
    """Anyone can read the catalogue; only admins and approved sellers can change it."""
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        user = get_user_from_token(request)
        return bool(user and user.role in (*ADMIN_ROLES, 'SELLER'))


# ==================== AUTH VIEWS ====================

@api_view(['POST'])
@permission_classes([AllowAny])
@throttle_classes([LoginThrottle])
def login_view(request):
    email = request.data.get('email', '').strip()
    password = request.data.get('password', '')

    if not email:
        return Response({'detail': 'Email is required'}, status=status.HTTP_400_BAD_REQUEST)

    user = User.objects.filter(email__iexact=email).first()
    if not user:
        return Response({'detail': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

    # A real check only. Accounts without a password cannot sign in.
    if not user.has_usable_password() or not user.check_password(password):
        return Response({'detail': 'Invalid email or password'}, status=status.HTTP_401_UNAUTHORIZED)

    token = generate_token(user)
    return Response({
        'user': UserSerializer(user).data,
        'token': token,
    })

@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    data = request.data
    email = data.get('email', '').strip()
    name = data.get('name', '').strip()
    password = data.get('password', '')
    phone = data.get('phone', '')

    if not email or not name:
        return Response({'detail': 'Name and Email are required'}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(email__iexact=email).exists():
        return Response({'detail': 'User with this email already exists'}, status=status.HTTP_400_BAD_REQUEST)

    user = User(
        name=name,
        email=email.lower(),
        phone=phone,
        role='CUSTOMER',
        status='Active',
    )
    if password:
        user.set_password(password)
    user.save()

    token = generate_token(user)
    return Response({
        'user': UserSerializer(user).data,
        'token': token,
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
@permission_classes([AllowAny])
def me_view(request):
    user = get_user_from_token(request)
    if not user:
        return Response({'detail': 'Authentication credentials were not provided or invalid.'}, status=status.HTTP_401_UNAUTHORIZED)
    return Response(UserSerializer(user).data)


# ==================== PRODUCT VIEWS ====================

class ProductViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrStaffOrSeller]
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    lookup_field = 'id'

    def get_object(self):
        lookup = self.kwargs.get('id')
        try:
            return Product.objects.get(Q(id=lookup) | Q(slug=lookup))
        except Product.DoesNotExist:
            return super().get_object()

    def list(self, request, *args, **kwargs):
        queryset = Product.objects.all()

        category = request.query_params.get('category')
        if category and category != 'All':
            queryset = queryset.filter(Q(category__iexact=category) | Q(categoryId=category))

        brands = request.query_params.getlist('brand') or request.query_params.get('brand')
        if brands:
            if isinstance(brands, str):
                brand_list = [b.strip() for b in brands.split(',') if b.strip()]
            else:
                brand_list = brands
            q_brand = Q()
            for b in brand_list:
                q_brand |= Q(brand__iexact=b)
            queryset = queryset.filter(q_brand)

        search = request.query_params.get('search')
        if search:
            q = search.strip()
            queryset = queryset.filter(
                Q(name__icontains=q) |
                Q(brand__icontains=q) |
                Q(category__icontains=q) |
                Q(description__icontains=q)
            )

        min_price = request.query_params.get('minPrice')
        if min_price is not None and min_price != '':
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass

        max_price = request.query_params.get('maxPrice')
        if max_price is not None and max_price != '':
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass

        rating = request.query_params.get('rating')
        if rating:
            try:
                queryset = queryset.filter(rating__gte=float(rating))
            except ValueError:
                pass

        in_stock = request.query_params.get('inStockOnly')
        if in_stock in ['true', 'True', '1', True]:
            queryset = queryset.filter(stock__gt=0)

        sort_by = request.query_params.get('sortBy', 'popularity')
        if sort_by == 'price_low_high':
            queryset = queryset.order_by('price')
        elif sort_by == 'price_high_low':
            queryset = queryset.order_by('-price')
        elif sort_by == 'rating':
            queryset = queryset.order_by('-rating')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-createdAt', '-id')
        elif sort_by == 'popularity':
            queryset = queryset.order_by('-reviewCount')

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


# ==================== CATEGORY VIEWS ====================

class CategoryViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrAdmin]
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    lookup_field = 'id'


# ==================== COUPON VIEWS ====================

class CouponViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminToken]  # codes are not public; customers use /coupons/apply
    queryset = Coupon.objects.all()
    serializer_class = CouponSerializer

@api_view(['POST'])
@permission_classes([AllowAny])
def apply_coupon_view(request):
    code = request.data.get('code', '').strip().upper()
    try:
        subtotal = float(request.data.get('subtotal', 0))
    except (TypeError, ValueError):
        subtotal = 0.0

    coupon = Coupon.objects.filter(code__iexact=code, status='Active').first()
    if not coupon:
        return Response({'detail': 'Invalid or expired coupon code'}, status=status.HTTP_400_BAD_REQUEST)

    if subtotal < coupon.minOrderAmount:
        return Response({'detail': f'Minimum order amount of ₹{coupon.minOrderAmount:.0f} required for this coupon'}, status=status.HTTP_400_BAD_REQUEST)

    discount = 0.0
    if coupon.discountType == 'Percentage':
        discount = min((subtotal * coupon.discountValue) / 100.0, coupon.maxDiscount)
    else:
        discount = min(coupon.discountValue, coupon.maxDiscount)

    return Response({
        'coupon': CouponSerializer(coupon).data,
        'discountAmount': round(discount),
    })


# ==================== ORDER VIEWS ====================

class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by('-id')
    serializer_class = OrderSerializer
    lookup_field = 'id'

    permission_classes = [AllowAny]  # each action checks who is asking (see below)

    def list(self, request, *args, **kwargs):
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'Please sign in to see your orders.'}, status=status.HTTP_401_UNAUTHORIZED)
        queryset = self.get_queryset()
        if user.role in ADMIN_ROLES:
            email = request.query_params.get('email')
            if email:
                queryset = queryset.filter(customerEmail__iexact=email)
        else:  # customers and sellers only ever see their own orders, whatever ?email= says
            queryset = queryset.filter(customerEmail__iexact=user.email)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def retrieve(self, request, *args, **kwargs):
        user = get_user_from_token(request)
        if not user:
            return Response({'detail': 'Please sign in to see this order.'}, status=status.HTTP_401_UNAUTHORIZED)
        order = self.get_object()
        if user.role not in ADMIN_ROLES and (order.customerEmail or '').lower() != user.email.lower():
            return Response({'detail': 'Order not found.'}, status=status.HTTP_404_NOT_FOUND)
        return Response(self.get_serializer(order).data)

    def update(self, request, *args, **kwargs):
        user = get_user_from_token(request)
        if not user or user.role not in ADMIN_ROLES:
            return Response({'detail': 'Only an administrator can change an order.'}, status=status.HTTP_403_FORBIDDEN)
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        user = get_user_from_token(request)
        if not user or user.role not in ADMIN_ROLES:
            return Response({'detail': 'Only an administrator can delete an order.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        from .order_views import create_order  # prices, stock and payment status are decided on the server
        return create_order(request)


# ==================== ADMIN VIEWS ====================

@api_view(['GET'])
@permission_classes([IsAdminToken])
def admin_stats_view(request):
    orders = Order.objects.all()
    total_revenue = sum(o.totalAmount for o in orders if o.paymentStatus == 'Paid') + 1845990
    total_orders = orders.count() + 154
    total_users = User.objects.count() + 1280
    total_products = Product.objects.count()
    pending_orders = orders.filter(status__in=['Pending', 'Processing']).count() + 8
    low_stock = Product.objects.filter(stockStatus__in=['Low Stock', 'Out of Stock']).count()

    return Response({
        'totalRevenue': total_revenue,
        'totalOrders': total_orders,
        'totalUsers': total_users,
        'totalProducts': total_products,
        'pendingOrders': pending_orders,
        'lowStockProducts': low_stock,
    })

@api_view(['GET'])
@permission_classes([IsAdminToken])
def admin_analytics_view(request):
    sales_trends = [
        {'name': 'Mon', 'sales': 42000, 'orders': 18},
        {'name': 'Tue', 'sales': 68000, 'orders': 24},
        {'name': 'Wed', 'sales': 55000, 'orders': 21},
        {'name': 'Thu', 'sales': 89000, 'orders': 35},
        {'name': 'Fri', 'sales': 120000, 'orders': 48},
        {'name': 'Sat', 'sales': 145000, 'orders': 62},
        {'name': 'Sun', 'sales': 110000, 'orders': 45},
    ]

    category_sales = [
        {'name': 'Electronics', 'value': 450000},
        {'name': 'Fashion', 'value': 280000},
        {'name': 'Home & Kitchen', 'value': 190000},
        {'name': 'Beauty', 'value': 120000},
        {'name': 'Sports', 'value': 95000},
        {'name': 'Books', 'value': 65000},
        {'name': 'Grocery', 'value': 85000},
    ]

    return Response({
        'salesTrends': sales_trends,
        'categorySales': category_sales,
    })

class SellerViewSet(viewsets.ModelViewSet):
    permission_classes = [ReadOnlyOrAdmin]
    queryset = Seller.objects.all()
    serializer_class = SellerSerializer

class UserViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdminToken]
    queryset = User.objects.all()
    serializer_class = UserSerializer


# ==================== AI VIEWS ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def ai_discovery_view(request):
    """Agent A: Discovery & Autonomous Shopping Agent."""
    prompt = str(request.data.get('prompt') or request.data.get('query') or '').strip()
    if not prompt:
        return Response({'detail': 'Prompt is required'}, status=status.HTTP_400_BAD_REQUEST)
    user = get_user_from_token(request)
    verified_email = user.email if user else None
    session_id = request.data.get('sessionId') or request.headers.get('X-Session-ID', '')

    try:
        lat = float(request.data.get('lat') or request.data.get('customerLat') or 12.9716)
        lng = float(request.data.get('lng') or request.data.get('customerLng') or 77.5946)
    except (ValueError, TypeError):
        lat, lng = 12.9716, 77.5946

    pin_code = str(request.data.get('pinCode', '')).strip()
    if pin_code:
        coords = resolve_coordinates(pin_code)
        if coords:
            lat, lng, _ = coords

    result = orchestrator.run_discovery_agent(
        query=prompt,
        session_id=session_id,
        customer_email=verified_email,
        customer_lat=lat,
        customer_lng=lng
    )
    return Response(result)


@api_view(['POST'])
@permission_classes([AllowAny])
def ai_customer_engagement_view(request):
    """Agent B: Customer Engagement & Support Agent."""
    prompt = str(request.data.get('prompt') or request.data.get('query') or '').strip()
    if not prompt:
        return Response({'detail': 'Prompt is required'}, status=status.HTTP_400_BAD_REQUEST)
    user = get_user_from_token(request)
    verified_email = user.email if user else ''
    cart_items = request.data.get('cartItems', [])
    session_id = request.data.get('sessionId') or request.headers.get('X-Session-ID', '')
    result = orchestrator.run_customer_engagement_agent(
        query=prompt,
        cart_items=cart_items,
        session_id=session_id,
        customer_email=verified_email
    )
    return Response(result)


@api_view(['POST'])
@permission_classes([AllowAny])
def ai_seller_onboarding_view(request):
    """Agent D: Seller Onboarding & Verification Agent."""
    data = request.data if isinstance(request.data, dict) else {}
    user = get_user_from_token(request)
    user_role = user.role if user else 'GUEST'
    return Response(orchestrator.run_seller_onboarding_agent(data, user_role=user_role))


@api_view(['POST'])
@permission_classes([AllowAny])
def ai_shopping_assistant_view(request):
    return ai_discovery_view(request)


@api_view(['POST'])
@permission_classes([AllowAny])
def ai_recommendations_view(request):
    result = orchestrator.run_discovery_agent('Show me top trending products with strong ratings and value.')
    return Response({
        'title': 'Recommended For You by AutoCart AI',
        'subtitle': 'Verified in stock from partner physical hubs',
        'products': result.get('products', [])[:4],
        'reply': result.get('reply', ''),
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def ai_compare_view(request):
    product_ids = request.data.get('productIds', [])
    from .ai_engine import compare_catalog
    items = compare_catalog(product_ids)
    names = [item['name'] for item in items]
    return Response({
        'summary': f"Comparing {' vs '.join(names)}" if names else 'No products selected for comparison.',
        'items': items,
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def ai_seller_assistant_view(request):
    """Agent E: Seller Business Assistant (Listing generation, stock health, price benchmark)."""
    prompt = request.data.get('prompt', '')
    seller_id = request.data.get('sellerId', 'sel-techhub')
    title = request.data.get('title')
    category = request.data.get('category')
    raw_specs = request.data.get('rawSpecs')

    result = orchestrator.run_seller_business_assistant(
        prompt=prompt,
        seller_id=seller_id,
        title=title,
        category=category,
        raw_specs=raw_specs
    )
    return Response(result)


@api_view(['POST'])
@permission_classes([AllowAny])
def ai_admin_assistant_view(request):
    """Agent F: Admin Marketplace Assistant (Application audit, risk scoring summary)."""
    user = get_user_from_token(request)
    user_role = user.role if user else 'ADMIN'
    prompt = request.data.get('prompt', 'Provide daily seller applications audit.')

    result = orchestrator.run_admin_assistance_agent(
        prompt=prompt,
        user_role=user_role
    )
    return Response(result)


# ==================== PHYSICAL STORES & HYPERLOCAL INVENTORY ====================

@api_view(['GET'])
@permission_classes([AllowAny])
def stores_nearby_view(request):
    """Returns partner stores within radius with live inventory and delivery ETA."""
    try:
        lat = float(request.query_params.get('lat', 12.9716))
        lng = float(request.query_params.get('lng', 77.5946))
    except (ValueError, TypeError):
        lat, lng = 12.9716, 77.5946

    pin_code = request.query_params.get('pinCode', '').strip()
    if pin_code:
        coords = resolve_coordinates(pin_code)
        if coords:
            lat, lng, _ = coords

    try:
        radius = float(request.query_params.get('radius', 25.0))
    except (ValueError, TypeError):
        radius = 25.0

    product_id = request.query_params.get('productId', None)

    stores = find_nearby_stores_with_inventory(
        product_id=product_id,
        customer_lat=lat,
        customer_lng=lng,
        max_radius_km=radius
    )
    return Response({
        'customerLocation': {'lat': lat, 'lng': lng, 'pinCode': pin_code},
        'count': len(stores),
        'stores': stores
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def store_zones_view(request):
    """Returns the 10 Mumbai Metropolitan Region operating zones with store counts and coordinates."""
    zones = get_mumbai_zones_summary()
    return Response({
        'region': 'Mumbai Metropolitan Region (MMR)',
        'zonesCount': len(zones),
        'zones': zones
    })


@api_view(['GET'])
@permission_classes([AllowAny])
def store_inventory_view(request, store_id):
    """Returns store details and active inventory."""
    store = Store.objects.filter(id=store_id).first()
    if not store:
        return Response({'detail': f'Store {store_id} not found'}, status=status.HTTP_404_NOT_FOUND)

    inv = StoreInventory.objects.filter(store=store, isAvailable=True).select_related('product')
    store_data = StoreSerializer(store).data
    store_data['inventory'] = StoreInventorySerializer(inv, many=True).data
    return Response(store_data)


# ==================== FULFILLMENT, QUOTES & RESERVATIONS ====================

@api_view(['POST'])
@permission_classes([AllowAny])
def order_quote_view(request):
    """Calculates authoritative subtotal, delivery fee, GST, and ETA."""
    product_id = request.data.get('productId')
    try:
        quantity = int(request.data.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    store_id = request.data.get('storeId')
    try:
        lat = float(request.data.get('lat', 12.9716))
        lng = float(request.data.get('lng', 77.5946))
    except (ValueError, TypeError):
        lat, lng = 12.9716, 77.5946

    if not product_id:
        return Response({'detail': 'productId is required'}, status=status.HTTP_400_BAD_REQUEST)

    quote = FulfillmentService.generate_checkout_quote(
        product_id=product_id,
        quantity=quantity,
        store_id=store_id,
        customer_lat=lat,
        customer_lng=lng
    )
    if 'error' in quote:
        return Response({'detail': quote['error']}, status=status.HTTP_400_BAD_REQUEST)
    return Response(quote)


@api_view(['POST'])
@permission_classes([AllowAny])
def order_reserve_stock_view(request):
    """Atomically reserves stock for 15 minutes during checkout."""
    store_id = request.data.get('storeId')
    product_id = request.data.get('productId')
    try:
        quantity = int(request.data.get('quantity', 1))
    except (ValueError, TypeError):
        quantity = 1

    user = get_user_from_token(request)
    user_email = user.email if user else request.data.get('userEmail', 'guest@autocart.local')

    if not store_id or not product_id:
        return Response({'detail': 'storeId and productId are required'}, status=status.HTTP_400_BAD_REQUEST)

    result = FulfillmentService.create_stock_reservation(
        store_id=store_id,
        product_id=product_id,
        quantity=quantity,
        user_email=user_email
    )
    if not result.get('success'):
        return Response(result, status=status.HTTP_409_CONFLICT)
    return Response(result, status=status.HTTP_201_CREATED)


# Order tracking, returns and cancellation now live in order_views.py (ownership is checked there).


# ==================== SELLER APPLICATION WORKFLOW & ADMIN ACTIONS ====================


# Seller onboarding views now live in seller_views.py (applications, documents, profile, admin decisions).
