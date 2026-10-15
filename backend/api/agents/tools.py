"""
Predefined, parameterized backend tools for AutoCart agents.
All database access is through strict, safe, typed queries.
Never executes raw SQL or arbitrary generated code.
"""

import re
from typing import Dict, List, Any, Optional
from django.db.models import Q
from ..models import Product, Order, Seller, Coupon, Category


def product_to_dict(product: Product) -> Dict[str, Any]:
    return {
        'id': product.id,
        'name': product.name,
        'brand': product.brand,
        'category': product.category,
        'price': float(product.price),
        'originalPrice': float(product.originalPrice),
        'discount': int(product.discount),
        'rating': float(product.rating),
        'reviewCount': int(product.reviewCount),
        'stock': int(product.stock),
        'stockStatus': product.stockStatus,
        'description': product.description,
        'specifications': product.specifications or {},
        'seller': product.seller,
        'images': product.images or [],
    }


# =====================================================================
# AGENT A: DISCOVERY TOOLS
# =====================================================================

def search_products(
    query: str,
    category: Optional[str] = None,
    brand: Optional[str] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
    limit: int = 6
) -> Dict[str, Any]:
    """
    Search AutoCart product database by keyword, category, brand, budget, and minimum rating.
    """
    q_str = (query or '').strip()
    qs = Product.objects.all()

    if category and category.lower() != 'all':
        qs = qs.filter(Q(category__iexact=category) | Q(categoryId__iexact=category))

    if brand:
        qs = qs.filter(brand__iexact=brand.strip())

    if max_price is not None and max_price > 0:
        qs = qs.filter(price__lte=float(max_price))

    if min_rating is not None and min_rating > 0:
        qs = qs.filter(rating__gte=float(min_rating))

    # Also parse natural language budget expressions if present in query (e.g. "₹1,000 se ₹1,500", "under ₹3,000", "under 70k")
    range_match = re.search(
        r'(?:between|from)?\s*[₹rs\.]*\s*([0-9,]+)\s*(?:se|to|and|-)\s*[₹rs\.]*\s*([0-9,]+)\s*(?:ke beech)?',
        q_str.lower()
    )
    if range_match:
        try:
            min_v = float(range_match.group(1).replace(',', '').strip())
            max_v = float(range_match.group(2).replace(',', '').strip())
            if min_v > max_v:
                min_v, max_v = max_v, min_v
            qs = qs.filter(price__gte=min_v, price__lte=max_v)
        except (ValueError, TypeError):
            pass
    else:
        budget_match = re.search(
            r'(?:under|below|less than|within|upto|up to|budget(?: of)?)\s*[₹rs\.]*\s*([0-9,]+(?:\.[0-9]+)?)\s*(k|thousand|lakh)?',
            q_str.lower()
        )
        if budget_match and (max_price is None or max_price <= 0):
            try:
                val_str = budget_match.group(1).replace(',', '').strip()
                val = float(val_str)
                unit = budget_match.group(2) or ''
                if unit in ('k', 'thousand'):
                    val *= 1000
                elif unit == 'lakh':
                    val *= 100000
                qs = qs.filter(price__lte=val)
            except (ValueError, TypeError):
                pass

    # Intelligent Relevance-Ranked Keyword Search
    terms = [t for t in re.findall(r'[a-zA-Z]+', q_str.lower()) if len(t) > 2]
    stop_words = {
        'the', 'and', 'for', 'with', 'under', 'below', 'best', 'good', 'show',
        'find', 'want', 'need', 'please', 'give', 'some', 'what', 'are', 'your',
        'today', 'top', 'rated', 'trending', 'most', 'popular', 'any', 'tell',
        'can', 'you', 'recommend', 'suggest', 'looking'
    }
    search_terms = [t for t in terms if t not in stop_words]

    category_aliases = {
        'electronics': ['Electronics'],
        'gadgets': ['Electronics'],
        'laptop': ['Electronics'],
        'laptops': ['Electronics'],
        'phone': ['Electronics'],
        'mobile': ['Electronics'],
        'shoes': ['Fashion', 'Sports & Fitness'],
        'running': ['Fashion', 'Sports & Fitness'],
        'sneakers': ['Fashion', 'Sports & Fitness'],
        'clothing': ['Fashion'],
        'clothes': ['Fashion'],
        'bottle': ['Home & Kitchen', 'Sports & Fitness'],
        'bottles': ['Home & Kitchen', 'Sports & Fitness'],
    }

    def score_product(p):
        name_l = p.name.lower()
        desc_l = (p.description or '').lower()
        brand_l = (p.brand or '').lower()
        cat_l = (p.category or '').lower()

        # Strict exclusion of mismatched accessories:
        # 1. Searching for Laptop: eliminate backpacks, bags, sleeves, stands, skins, coolers, and fashion apparel
        if any(w in search_terms for w in ['laptop', 'laptops', 'notebook']):
            if any(acc in name_l for acc in ['backpack', 'bag', 'sleeve', 'stand', 'cooler', 'skin', 'case', 'cover']) or cat_l in ['fashion', 'apparel']:
                return -9999.0

        # 2. Searching for Earbuds / Headphones: eliminate mice, keyboards, cables, covers, phones
        if any(w in search_terms for w in ['earbuds', 'earphone', 'headphones', 'tws', 'airpods']):
            if any(acc in name_l for acc in ['mouse', 'keyboard', 'cable', 'cover', 'strap', 'laptop', 'charger', 'backpack']):
                return -9999.0
            if 'phone' in name_l and 'buds' not in name_l and 'ear' not in name_l:
                return -9999.0

        # 3. Searching for Shoes / Footwear: eliminate t-shirts, shirts, jeans, pants, kurtas, bags
        if any(w in search_terms for w in ['shoes', 'sneakers', 'running', 'footwear']):
            if any(acc in name_l for acc in ['t-shirt', 'shirt', 'jeans', 'pant', 'kurta', 'dress', 'backpack', 'bottle', 'watch']):
                return -9999.0

        # 4. Searching for Water Bottles: eliminate backpacks, apparel, cosmetics
        if any(w in search_terms for w in ['bottle', 'bottles', 'flask', 'sipper']):
            if any(acc in name_l for acc in ['t-shirt', 'shirt', 'backpack', 'shoes', 'mascara', 'cosmetic']):
                return -9999.0

        score = float(p.rating or 4.0) * 2.0
        # Reward term occurrences
        for term in search_terms:
            if term in name_l:
                score += 15
            elif term in brand_l:
                score += 10
            elif term in cat_l:
                score += 8
            elif term in desc_l:
                score += 4

        return score

    if search_terms:
        # Build candidate pool from name, brand, category, or description
        name_expr = Q()
        for term in search_terms[:5]:
            name_expr |= Q(name__icontains=term) | Q(brand__icontains=term)
        
        candidates = list(qs.filter(name_expr)[:limit * 4])
        
        # If pool is small, check category aliases (only for general category queries, not specific hardware/items)
        specific_items = {'laptop', 'laptops', 'notebook', 'shoes', 'running', 'sneakers', 'earbuds', 'headphones', 'bottle', 'bottles'}
        is_specific = any(w in search_terms for w in specific_items)
        
        if len(candidates) < limit and not is_specific:
            cat_expr = Q()
            for term in search_terms:
                if term in category_aliases:
                    for target_c in category_aliases[term]:
                        cat_expr |= Q(category__iexact=target_c)
            if cat_expr:
                more_cat = list(qs.filter(cat_expr)[:limit * 3])
                for item in more_cat:
                    if item not in candidates:
                        candidates.append(item)

        if not candidates:
            desc_expr = Q()
            for term in search_terms[:5]:
                desc_expr |= Q(category__icontains=term) | Q(description__icontains=term)
            candidates = list(qs.filter(desc_expr)[:limit * 3])

        # Rank candidates by relevance score and discard disqualified items
        valid_candidates = [c for c in candidates if score_product(c) > 0]
        valid_candidates.sort(key=score_product, reverse=True)
        results = valid_candidates[:limit]
    else:
        results = list(qs.order_by('-rating', '-reviewCount')[:limit])

    return {
        'count': len(results),
        'products': [product_to_dict(p) for p in results]
    }


def get_product_details(product_id: str) -> Dict[str, Any]:
    """
    Get full catalog details, specifications, price, and stock status for a specific product ID.
    """
    pid = (product_id or '').strip()
    p = Product.objects.filter(Q(id=pid) | Q(slug=pid)).first()
    if not p:
        return {'found': False, 'error': f'Product "{product_id}" not found in catalog'}
    return {
        'found': True,
        'product': product_to_dict(p)
    }


def compare_products(product_ids: List[str]) -> Dict[str, Any]:
    """
    Compare multiple products side by side using their IDs from the database.
    Returns specs, prices, ratings, and stock status.
    """
    clean_ids = [str(pid).strip() for pid in product_ids if pid]
    products = list(Product.objects.filter(id__in=clean_ids))
    return {
        'count': len(products),
        'comparison': [product_to_dict(p) for p in products]
    }


def filter_products_by_budget(max_budget: float, category: Optional[str] = None) -> Dict[str, Any]:
    """
    Find top rated products strictly within a budget ceiling (INR), optionally by category.
    """
    qs = Product.objects.filter(price__lte=float(max_budget), stock__gt=0)
    if category and category.lower() != 'all':
        qs = qs.filter(Q(category__iexact=category) | Q(categoryId__iexact=category))
    results = list(qs.order_by('-rating', '-reviewCount')[:6])
    return {
        'budget_ceiling': max_budget,
        'count': len(results),
        'products': [product_to_dict(p) for p in results]
    }


def check_product_availability(product_id: str) -> Dict[str, Any]:
    """
    Check real-time stock levels, stock status, and seller information for a product.
    If out of stock, suggests available in-stock alternatives in the same category.
    """
    p = Product.objects.filter(id=product_id.strip()).first()
    if not p:
        return {'found': False, 'error': 'Product not found'}
    
    is_in_stock = p.stock > 0 and p.stockStatus != 'Out of Stock'
    alternatives = []
    if not is_in_stock:
        alt_qs = Product.objects.filter(category=p.category, stock__gt=0).exclude(id=p.id).order_by('-rating')[:3]
        alternatives = [product_to_dict(alt) for alt in alt_qs]

    return {
        'found': True,
        'id': p.id,
        'name': p.name,
        'stock': p.stock,
        'stockStatus': p.stockStatus,
        'isAvailable': is_in_stock,
        'seller': p.seller,
        'alternatives': alternatives
    }


# =====================================================================
# AGENT B: CUSTOMER ENGAGEMENT TOOLS
# =====================================================================

def get_my_orders(customer_email: str, limit: int = 5) -> Dict[str, Any]:
    """
    Retrieve order history and current status for the verified authenticated customer.
    SECURITY: customer_email is enforced by backend session/JWT.
    """
    if not customer_email:
        return {'error': 'Authentication required. No verified customer email provided.', 'orders': []}
    
    orders = list(Order.objects.filter(customerEmail__iexact=customer_email).order_by('-id')[:limit])
    return {
        'email': customer_email,
        'orders_count': len(orders),
        'orders': [
            {
                'id': o.id,
                'date': o.date,
                'totalAmount': float(o.totalAmount),
                'status': o.status,
                'paymentMethod': o.paymentMethod,
                'paymentStatus': o.paymentStatus,
                'itemsCount': len(o.items or []),
                'items': o.items,
                'shippingAddress': o.shippingAddress,
            }
            for o in orders
        ]
    }


def get_my_order_details(order_id: str, customer_email: str) -> Dict[str, Any]:
    """
    Get detailed timeline, shipping address, and tracking info for an order belonging to the customer.
    SECURITY: Verifies that the order strictly belongs to customer_email.
    """
    if not customer_email:
        return {'error': 'Authentication required.'}
    
    order = Order.objects.filter(id=order_id.strip()).first()
    if not order:
        return {'error': f'Order {order_id} not found.'}
    
    if order.customerEmail.lower() != customer_email.lower():
        # Prevent customer data leakage!
        return {'error': 'Access denied: You are not authorized to view this order.'}

    return {
        'id': order.id,
        'date': order.date,
        'totalAmount': float(order.totalAmount),
        'subtotal': float(order.subtotal),
        'tax': float(order.tax),
        'shippingFee': float(order.shippingFee),
        'discountAmount': float(order.discountAmount),
        'paymentMethod': order.paymentMethod,
        'paymentStatus': order.paymentStatus,
        'status': order.status,
        'shippingAddress': order.shippingAddress,
        'items': order.items,
        'timeline': order.timeline,
    }


def get_cart_summary(cart_items: List[Dict[str, Any]], coupon_code: Optional[str] = None) -> Dict[str, Any]:
    """
    Calculate cart pricing breakdown, delivery fee, and applicable coupon savings.
    """
    subtotal = sum(float(item.get('price', 0)) * int(item.get('quantity', 1)) for item in cart_items)
    delivery_fee = 0.0 if (subtotal > 499 or subtotal == 0) else 40.0
    discount_amount = 0.0
    applied_coupon = None

    if coupon_code:
        coupon = Coupon.objects.filter(code__iexact=coupon_code.strip(), status='Active').first()
        if coupon and subtotal >= coupon.minOrderAmount:
            if coupon.discountType == 'Percentage':
                discount_amount = min((subtotal * coupon.discountValue) / 100.0, coupon.maxDiscount)
            else:
                discount_amount = min(coupon.discountValue, coupon.maxDiscount)
            applied_coupon = coupon.code

    final_total = max(0.0, subtotal - discount_amount + delivery_fee)
    return {
        'subtotal': round(subtotal, 2),
        'deliveryFee': delivery_fee,
        'discountAmount': round(discount_amount, 2),
        'finalTotal': round(final_total, 2),
        'appliedCoupon': applied_coupon,
        'freeShippingEligible': subtotal > 499
    }


def get_shipping_policy() -> Dict[str, Any]:
    """
    Returns actual configured shipping policies and delivery timelines for AutoCart.
    """
    return {
        'standardDeliveryDays': '3 to 5 business days',
        'expressDeliveryDays': '1 to 2 business days (metro areas)',
        'freeShippingThreshold': 'Orders above ₹499 qualify for free standard shipping',
        'standardShippingFee': '₹40 for orders under ₹499',
        'deliveryPartners': ['Blue Dart', 'Delhivery', 'Shadowfax'],
        'tracking': 'Real-time tracking available under customer Orders tab once shipped'
    }


def get_return_policy() -> Dict[str, Any]:
    """
    Returns actual configured return and refund rules for AutoCart.
    """
    return {
        'returnWindowDays': 7,
        'conditions': 'Items must be unused, in original packaging with tags and warranty seals intact.',
        'nonReturnableCategories': ['Perishable groceries', 'Personal hygiene products', 'Opened software'],
        'refundMethod': 'Original payment method within 5-7 business days after pickup inspection',
        'exchangeOption': 'Free size/color replacement available for apparel and footwear'
    }


# =====================================================================
# AGENT C: SELLER ONBOARDING & ADMIN TOOLS
# =====================================================================

def validate_seller_application(application_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates seller submission fields against marketplace business rules and computes a compliance score.
    """
    data = application_data or {}
    required = ['name', 'companyName', 'email', 'phone', 'city', 'businessType', 'productCategories']
    missing = [f for f in required if not str(data.get(f) or '').strip()]
    
    risk_points = 0
    checklist = []

    # Email
    email = str(data.get('email', '')).strip()
    if not email or '@' not in email:
        risk_points += 20
        checklist.append({'item': 'Valid business email', 'complete': False, 'priority': 'High'})
    else:
        checklist.append({'item': 'Valid business email', 'complete': True, 'priority': 'High'})

    # Phone
    phone = str(data.get('phone', '')).strip()
    if not phone or len(phone) < 10:
        risk_points += 15
        checklist.append({'item': 'Contact telephone number', 'complete': False, 'priority': 'High'})
    else:
        checklist.append({'item': 'Contact telephone number', 'complete': True, 'priority': 'High'})

    # GSTIN
    gstin = str(data.get('gstin', '')).strip()
    if not gstin or len(gstin) < 15:
        risk_points += 15
        checklist.append({'item': 'GSTIN tax identifier verification', 'complete': False, 'priority': 'High'})
    else:
        checklist.append({'item': 'GSTIN tax identifier verification', 'complete': True, 'priority': 'High'})

    # Identity / KYC
    id_verified = bool(data.get('identityVerified'))
    if not id_verified:
        risk_points += 15
        checklist.append({'item': 'Government Identity / KYC proof', 'complete': False, 'priority': 'High'})
    else:
        checklist.append({'item': 'Government Identity / KYC proof', 'complete': True, 'priority': 'High'})

    # Bank verification
    bank_verified = bool(data.get('bankVerified'))
    if not bank_verified:
        risk_points += 15
        checklist.append({'item': 'Commercial bank account verification', 'complete': False, 'priority': 'High'})
    else:
        checklist.append({'item': 'Commercial bank account verification', 'complete': True, 'priority': 'High'})

    # Business proof document
    biz_proof = bool(data.get('businessProofUploaded'))
    if not biz_proof:
        risk_points += 10
        checklist.append({'item': 'Business incorporation / trade license proof', 'complete': False, 'priority': 'Medium'})
    else:
        checklist.append({'item': 'Business incorporation / trade license proof', 'complete': True, 'priority': 'Medium'})

    # Categories
    cats = data.get('productCategories') or []
    if not cats:
        risk_points += 10
        checklist.append({'item': 'Declared product category alignment', 'complete': False, 'priority': 'Medium'})
    else:
        checklist.append({'item': 'Declared product category alignment', 'complete': True, 'priority': 'Medium'})

    risk_score = min(100, risk_points)
    status_label = (
        'Ready for review' if not missing and risk_score <= 30
        else ('Needs verification' if risk_score <= 55 else 'High verification required')
    )

    return {
        'isValid': len(missing) == 0 and risk_score <= 40,
        'missingFields': missing,
        'riskScore': risk_score,
        'preliminaryStatus': status_label,
        'checklist': checklist,
        'recommendation': 'Submit for administrator human review once documents are uploaded.'
    }


def get_pending_seller_applications(user_role: str) -> Dict[str, Any]:
    """
    List pending seller applications from the database.
    SECURITY: Only accessible to users with ADMIN or STAFF role.
    """
    if user_role not in ('ADMIN', 'STAFF'):
        return {'error': 'Access denied: Administrator permissions required to review seller applications.'}

    pending_sellers = list(Seller.objects.filter(status='Pending'))
    return {
        'count': len(pending_sellers),
        'pendingSellers': [
            {
                'id': s.id,
                'name': s.name,
                'companyName': s.companyName,
                'email': s.email,
                'phone': s.phone,
                'city': s.city,
                'status': s.status,
                'joinedDate': s.joinedDate,
            }
            for s in pending_sellers
        ]
    }


def get_seller_application_status(seller_id: str) -> Dict[str, Any]:
    """
    Retrieve current verification status for a specific seller by ID.
    """
    s = Seller.objects.filter(id=seller_id.strip()).first()
    if not s:
        return {'error': f'Seller with ID {seller_id} not found.'}
    return {
        'id': s.id,
        'name': s.name,
        'companyName': s.companyName,
        'status': s.status,
        'city': s.city,
        'joinedDate': s.joinedDate,
    }


def summarize_seller_application(application_data: Dict[str, Any], user_role: str) -> Dict[str, Any]:
    """
    Creates an executive structured summary of a seller application for human administrators.
    SECURITY: Enforces administrator authorization.
    """
    if user_role not in ('ADMIN', 'STAFF'):
        return {'error': 'Access denied: Administrator permissions required.'}

    validation = validate_seller_application(application_data)
    name = application_data.get('name', 'N/A')
    company = application_data.get('companyName', 'N/A')
    city = application_data.get('city', 'N/A')
    categories = application_data.get('productCategories', [])

    return {
        'sellerOverview': f"{name} ({company}) - {city}",
        'categoryFocus': categories,
        'riskScore': validation['riskScore'],
        'preliminaryStatus': validation['preliminaryStatus'],
        'missingFields': validation['missingFields'],
        'checklist': validation['checklist'],
        'humanAdminActionRequired': 'Final approval or rejection must be confirmed manually by an authorized marketplace administrator in the Sellers dashboard.'
    }


# =====================================================================
# AGENT C: LOCATION & FULFILLMENT TOOLS
# =====================================================================

def find_nearby_stores_for_product(
    product_id: Optional[str] = None,
    lat: float = 12.9716,
    lng: float = 77.5946,
    radius_km: float = 20.0,
    required_quantity: int = 1
) -> Dict[str, Any]:
    """
    Finds real nearby physical partner stores holding actual inventory within customer radius.
    """
    from ..location_service import find_nearby_stores_with_inventory
    stores = find_nearby_stores_with_inventory(
        product_id=product_id,
        customer_lat=float(lat),
        customer_lng=float(lng),
        max_radius_km=float(radius_km),
        required_quantity=int(required_quantity)
    )
    return {
        'productId': product_id,
        'customerLocation': {'lat': lat, 'lng': lng},
        'searchRadiusKm': radius_km,
        'storesFoundCount': len(stores),
        'stores': stores
    }


def check_store_inventory_availability(store_id: str, product_id: str, quantity: int = 1) -> Dict[str, Any]:
    """
    Queries exact real-time physical store inventory for a product SKU.
    """
    from ..models import StoreInventory
    inv = StoreInventory.objects.filter(store_id=store_id.strip(), product_id=product_id.strip()).first()
    if not inv:
        return {'available': False, 'message': 'Product is not stocked at this location.'}

    is_sufficient = inv.availableQuantity >= int(quantity)
    return {
        'storeId': inv.store.id,
        'storeName': inv.store.name,
        'productId': inv.product.id,
        'productName': inv.product.name,
        'availableQuantity': inv.availableQuantity,
        'reservedQuantity': inv.reservedQuantity,
        'storePrice': inv.storePrice,
        'isSufficientStock': is_sufficient,
        'requestedQuantity': quantity
    }


def calculate_fulfillment_quote(
    product_id: str,
    quantity: int = 1,
    store_id: Optional[str] = None,
    lat: float = 12.9716,
    lng: float = 77.5946
) -> Dict[str, Any]:
    """
    Calculates exact checkout quote: item subtotal, distance delivery charge, tax, total, and delivery ETA.
    """
    from ..fulfillment_service import FulfillmentService
    return FulfillmentService.generate_checkout_quote(
        product_id=product_id,
        quantity=int(quantity),
        store_id=store_id,
        customer_lat=float(lat),
        customer_lng=float(lng)
    )


def reserve_store_stock(
    store_id: str,
    product_id: str,
    quantity: int = 1,
    user_email: str = 'customer@example.com'
) -> Dict[str, Any]:
    """
    Atomically reserves store stock for 15 minutes to guarantee item availability during checkout.
    """
    from ..fulfillment_service import FulfillmentService
    return FulfillmentService.create_stock_reservation(
        store_id=store_id,
        product_id=product_id,
        quantity=int(quantity),
        user_email=user_email
    )


# =====================================================================
# AGENT B: CUSTOMER POST-PURCHASE & SUPPORT TOOLS
# =====================================================================

def get_order_fulfillment_tracking(order_id: str, customer_email: str) -> Dict[str, Any]:
    """
    Retrieves live fulfillment progress, courier dispatch status, and road tracking ETA for an order.
    """
    from ..models import OrderFulfillment, Order
    clean_id = order_id.strip()
    order = Order.objects.filter(id=clean_id).first()
    if not order:
        return {'error': f"Order {clean_id} not found."}

    if customer_email and order.customerEmail.lower() != customer_email.lower():
        return {'error': 'Unauthorized: You can only view tracking records for your own orders.'}

    ful = OrderFulfillment.objects.filter(order=order).first()
    if not ful:
        from ..fulfillment_service import FulfillmentService
        ful = FulfillmentService.initiate_fulfillment(order)

    return {
        'orderId': order.id,
        'trackingNumber': ful.trackingNumber,
        'deliveryPartner': ful.deliveryPartner,
        'currentStatus': ful.currentStatus,
        'distanceKm': ful.distanceKm,
        'estimatedMinutes': ful.estimatedDeliveryMinutes,
        'storeName': ful.store.name if ful.store else 'AutoCart Fulfillment Hub',
        'timeline': ful.timeline
    }


def check_order_return_eligibility(order_id: str, customer_email: str) -> Dict[str, Any]:
    """
    Evaluates backend policy rules to determine if an order is eligible for return/refund.
    """
    from ..models import Order
    order = Order.objects.filter(id=order_id.strip()).first()
    if not order:
        return {'eligible': False, 'reason': f"Order {order_id} not found."}

    if customer_email and order.customerEmail.lower() != customer_email.lower():
        return {'eligible': False, 'reason': 'Unauthorized access.'}

    if order.status not in ('Delivered', 'Confirmed', 'Processing'):
        return {'eligible': False, 'reason': f"Order is currently in '{order.status}' status."}

    return {
        'orderId': order.id,
        'eligible': True,
        'returnWindowDays': 7,
        'orderDate': order.date,
        'refundAmount': float(order.totalAmount),
        'conditions': 'Items must be intact with original packaging, tags, and accessories.',
        'nextStep': 'Initiate return request with reason to receive instant pickup scheduling.'
    }


def request_order_cancellation(order_id: str, reason: str, customer_email: str) -> Dict[str, Any]:
    """
    Cancels an order if it has not yet been shipped, releasing any reserved stock.
    """
    from ..models import Order
    order = Order.objects.filter(id=order_id.strip()).first()
    if not order:
        return {'success': False, 'error': f"Order {order_id} not found."}

    if customer_email and order.customerEmail.lower() != customer_email.lower():
        return {'success': False, 'error': 'Unauthorized.'}

    if order.status in ('Shipped', 'Out for Delivery', 'Delivered'):
        return {
            'success': False,
            'error': f"Order cannot be cancelled directly as it is already {order.status}. You may initiate a free return upon delivery."
        }

    order.status = 'Cancelled'
    order.save()
    return {
        'success': True,
        'orderId': order.id,
        'status': 'Cancelled',
        'refundStatus': 'Initiated to original payment method',
        'cancellationReason': reason
    }


# =====================================================================
# AGENT E: SELLER BUSINESS ASSISTANT TOOLS
# =====================================================================

def generate_seller_product_listing(
    title: str,
    category: str,
    raw_specs: Optional[str] = None,
    seller_name: str = 'Official Partner'
) -> Dict[str, Any]:
    """
    Autonomous listing copilot: drafts SEO-optimized product titles, category tags,
    bullet points, specifications, and suggested competitive price range based on catalog data.
    """
    clean_title = (title or 'Product').strip()
    clean_cat = (category or 'Electronics').strip()

    # Find benchmark products in the same category
    benchmarks = list(Product.objects.filter(category__icontains=clean_cat).order_by('-rating')[:3])
    avg_price = (sum(p.price for p in benchmarks) / len(benchmarks)) if benchmarks else 1999.0

    return {
        'suggestedTitle': f"{clean_title} — Premium Edition",
        'category': clean_cat,
        'recommendedPrice': round(avg_price * 0.95, 2),
        'suggestedMSRP': round(avg_price * 1.3, 2),
        'estimatedDiscount': '25%',
        'draftDescription': (
            f"Experience superior quality and reliable everyday performance with {clean_title}. "
            f"Engineered to meet the highest market standards for {clean_cat.lower()} enthusiasts."
        ),
        'keyFeatures': [
            f"High-durability build designed for everyday {clean_cat.lower()} use",
            "Certified multi-vendor quality check with manufacturer warranty",
            "Fast dispatch ready with AutoCart Hyperlocal store fulfillment"
        ],
        'requiresConfirmation': 'Draft listing prepared. Seller confirmation required before publishing to live marketplace.'
    }


def analyze_seller_inventory_and_pricing(seller_id: str) -> Dict[str, Any]:
    """
    Analyzes live stock health, low inventory warnings, and pricing opportunities for a seller.
    """
    from ..models import StoreInventory, Store
    stores = Store.objects.filter(sellerId=seller_id)
    if not stores.exists():
        stores = Store.objects.filter(seller__icontains='Appario') # Default benchmark demo

    low_stock = []
    healthy_stock = []

    for store in stores:
        invs = StoreInventory.objects.filter(store=store).select_related('product')[:20]
        for inv in invs:
            item_data = {
                'productId': inv.product.id,
                'name': inv.product.name,
                'available': inv.availableQuantity,
                'store': store.name,
                'price': inv.storePrice
            }
            if inv.availableQuantity <= 5:
                low_stock.append(item_data)
            else:
                healthy_stock.append(item_data)

    return {
        'sellerId': seller_id,
        'storesCount': stores.count(),
        'lowStockAlertCount': len(low_stock),
        'lowStockItems': low_stock[:6],
        'healthyStockItemsCount': len(healthy_stock),
        'actionableRecommendations': [
            f"Replenish {len(low_stock)} low-stock items at nearby fulfillment hubs to prevent lost sales.",
            "Enable AutoCart Hyperlocal Same-Day Dispatch for higher ranking.",
            "Review competitive pricing benchmarks for top-moving catalog SKUs."
        ]
    }


# =====================================================================
# AGENT F: ADMIN MARKETPLACE ASSISTANT TOOLS
# =====================================================================

def audit_seller_applications_state(user_role: str) -> Dict[str, Any]:
    """
    Summarizes all pending seller applications across state machine stages for administrator review.
    """
    from ..models import SellerApplication
    if user_role not in ('ADMIN', 'STAFF'):
        return {'error': 'Access denied: Admin permissions required.'}

    apps = list(SellerApplication.objects.all().order_by('-createdAt'))
    state_breakdown = {}
    for a in apps:
        state_breakdown[a.status] = state_breakdown.get(a.status, 0) + 1

    high_risk = [
        {
            'id': a.id,
            'companyName': a.companyName,
            'applicant': a.applicantName,
            'riskScore': a.riskScore,
            'status': a.status,
            'missing': a.missingFields
        }
        for a in apps if a.riskScore >= 50
    ]

    return {
        'totalApplications': len(apps),
        'stateBreakdown': state_breakdown,
        'highRiskApplicationsCount': len(high_risk),
        'highRiskFlagged': high_risk,
        'requiresAdminAction': 'Authorized administrators must execute final decision via the Admin Seller Onboarding workspace.'
    }

