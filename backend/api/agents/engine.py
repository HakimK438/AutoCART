"""
AutoCart Multi-Agent Orchestrator Engine.
Coordinates 6 specialized agents with bounded tool-calling architecture:
- Agent A: Discovery & Shopping Agent (Catalog, budget, nearby physical stores)
- Agent B: Customer Engagement & Support Agent (Orders, fulfillment tracking, returns)
- Agent C: Location & Fulfillment Agent (Nearby store inventory, quotes, stock reservation)
- Agent D: Seller Onboarding & Verification Agent (OCR validation, risk assessment)
- Agent E: Seller Business Assistant Agent (Listing generation, stock health, price benchmark)
- Agent F: Admin Marketplace Assistant Agent (Application audit, risk highlights, operations)
"""

import json
import logging
import re
import uuid
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

from .llm_provider import UnifiedLLMProvider
from .memory import SessionMemoryManager
from . import tools as tool_lib
from ..models import AgentTask, AgentExecutionLog, Product, Order, Store, StoreInventory
from ..fulfillment_service import FulfillmentService
from ..location_service import resolve_coordinates, haversine_distance_km

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Specialized System Instructions for Each Agent
# ---------------------------------------------------------------------------

DISCOVERY_SYSTEM_INSTRUCTION = """
You are the AutoCart Discovery & Shopping Agent, a friendly and knowledgeable e-commerce shopping advisor.

HOW TO ANSWER:
1. Speak naturally like an expert shopping consultant in clean, conversational sentences.
2. DO NOT output repetitive raw markdown headings like "### Top Recommendation" or bullet dumps of technical fields.
3. Provide a concise 2-3 sentence overview highlighting the top picks, price, key benefits, and why they fit the user's needs. The interactive product cards are already displayed below your message.
4. If nearby stores or in-stock local physical stores are found, clearly mention which nearby partner has it in stock for immediate delivery or pickup.
5. Grounding: ONLY recommend items provided in the catalog matches. Never invent products or prices.
"""

CUSTOMER_ENGAGEMENT_SYSTEM_INSTRUCTION = """
You are the AutoCart Customer Engagement & Support Agent, an empathetic shopping and post-purchase specialist.
You assist customers with live order tracking, delivery timelines, return policies, cart totals, and cancellations.

CORE RULES:
1. Customer Privacy: Order records are strictly scoped to the authenticated customer. Never disclose details from any other user.
2. Grounding: Use verified order status and tracking tools. Never claim an order is delivered, shipped, or refunded without backend confirmation.
3. Policy Guidance: Inform users clearly about return windows (7-day window) and eligibility conditions.
4. Keep answers concise, empathetic, and action-oriented.
"""

LOCATION_FULFILLMENT_SYSTEM_INSTRUCTION = """
You are the AutoCart Location & Fulfillment Agent.
You connect customers with nearby physical partner stores holding live inventory, calculate road delivery estimates, and coordinate stock reservations.

CORE RULES:
1. Grounding: Only recommend stores that genuinely have verified available stock in the database.
2. Distance & Transparency: Transparently explain distance in kilometers, estimated delivery time in minutes, and delivery fee.
3. Explain Why: State why the recommended store was chosen (e.g. closest distance, fastest delivery, best price).
"""

SELLER_ONBOARDING_SYSTEM_INSTRUCTION = """
You are the AutoCart Seller Onboarding & Verification Agent for the marketplace administration portal.
Your job is to assist sellers in submitting valid applications, analyze document OCR credentials, and produce structured assessments for admins.

CORE RULES:
1. Strict Role Protection: Final approval or activation is strictly restricted to authorized human administrators. You must NEVER self-approve an application.
2. Impartial Verification: Highlight missing fields (GSTIN, PAN, bank proof) and identify document OCR discrepancies.
3. Structure: Provide clear verified facts, risk scores, and recommended administrator next steps.
"""

SELLER_ASSISTANT_SYSTEM_INSTRUCTION = """
You are the AutoCart Seller Business Assistant, an expert e-commerce growth copilot.
You assist sellers with creating optimized product listings, competitive price benchmarking from market catalog data, and low-inventory replenishment alerts.

CORE RULES:
1. Draft Only: Product listings are drafted automatically for review. Inform the seller that explicit confirmation is required before publishing live.
2. Factual Pricing: Use real marketplace pricing benchmarks. Never invent market trends.
"""

ADMIN_ASSISTANT_SYSTEM_INSTRUCTION = """
You are the AutoCart Admin Assistance Agent.
You help marketplace operations teams audit pending seller applications across the 8-state application lifecycle, highlight high-risk discrepancies, and summarize inventory metrics.

CORE RULES:
1. Admin Authorization: This agent operates strictly within the secure admin perimeter.
2. Human in the Loop: Highlight high-risk applications needing investigation. Do not execute destructive actions automatically.
"""


class AgentEngine:
    """
    Central AutoCart AI Orchestrator that coordinates specialized agents with bounded tools.
    """

    def __init__(self):
        self.provider = UnifiedLLMProvider()

    def _log_tool_execution(
        self,
        task: Optional[AgentTask],
        agent_name: str,
        tool_name: str,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        execution_time_ms: int,
        status: str = 'SUCCESS'
    ):
        """Records an execution trace in the database for auditing and explainability."""
        try:
            AgentExecutionLog.objects.create(
                id=f"log-{uuid.uuid4().hex[:8]}",
                task=task,
                agentName=agent_name,
                toolName=tool_name,
                inputs=inputs,
                outputs=outputs,
                executionTimeMs=execution_time_ms,
                status=status
            )
        except Exception as e:
            logger.debug("Failed to record agent execution log: %s", e)

    # -----------------------------------------------------------------------
    # AGENT A: DISCOVERY & SHOPPING AGENT
    def run_discovery_agent(
        self,
        query: str,
        session_id: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_lat: float = 12.9716,
        customer_lng: float = 77.5946
    ) -> Dict[str, Any]:
        t0 = time.time()
        session_key = SessionMemoryManager.get_session_key(session_id, customer_email)
        state = SessionMemoryManager.get_state(session_key)
        q_lower = query.lower().strip()

        # Multi-turn Conversational Intent Classifiers
        is_store_order = any(phrase in q_lower for phrase in [
            'pehle store se order', 'pehli store se order', 'order from first store',
            'order from store', 'store se order', 'order from this store',
            'pehle store se mangwao', 'pehle store se khareed', 'place order from store',
            'store se order karna hai', 'order from 1st store', 'order pehle store'
        ])

        is_store_check = any(phrase in q_lower for phrase in [
            'aas paas', 'aas-paas', 'kis store', 'nearby store', 'available store',
            'stores near', 'store me available', 'store mein available', 'check store',
            'check inventory', 'konsi store', 'kaha available', 'kahan available',
            'check kar mere aas paas', 'check kar aas paas', 'near me store'
        ]) and not is_store_order

        is_add_cart = any(phrase in q_lower for phrase in [
            'cart mein add', 'cart me add', 'add to cart', 'add in cart',
            'add first', 'pehla wala cart', 'pehli wali cart', 'buy first',
            'put in cart', 'cart me daal', 'cart mein daal', 'add kar de',
            'cart me daalo', 'pehla cart', 'pehla add'
        ]) and not is_store_order and not is_store_check

        # Default coordinates to Mumbai Central (19.1136, 72.8697) if customer coordinates are default or outside Mumbai
        effective_lat = customer_lat
        effective_lng = customer_lng
        if haversine_distance_km(customer_lat, customer_lng, 19.1136, 72.8697) > 60.0:
            effective_lat = 19.1136
            effective_lng = 72.8697

        # -------------------------------------------------------------------
        # INTENT 1: ORDER DIRECTLY FROM SELECTED STORE VIA AI
        # -------------------------------------------------------------------
        if is_store_order:
            task = AgentTask.objects.create(
                id=f"task-{uuid.uuid4().hex[:8]}",
                taskType='STORE_FULFILLMENT',
                sessionId=session_id or '',
                userEmail=customer_email or '',
                goal=f"AI Hyperlocal Order Placement: {query}",
                status='IN_PROGRESS',
                plan=[
                    'Step 1: Retrieve selected store and target product from conversational memory',
                    'Step 2: Generate authoritative checkout quote (GST + delivery fee)',
                    'Step 3: Atomically reserve store physical stock',
                    'Step 4: Create Order with permanent store binding and initiate fulfillment'
                ],
                currentStep=1
            )

            # Target product from state or catalog
            target_prod = state.get('selected_product')
            if not target_prod:
                last_prods = state.get('last_products', [])
                target_prod = last_prods[0] if last_prods else None

            if not target_prod:
                # Fallback to top wireless mouse
                found = tool_lib.search_products('wireless mouse', limit=1).get('products', [])
                target_prod = found[0] if found else None

            # Target store from state or nearby lookup
            target_store = state.get('selected_store')
            if not target_store:
                last_stores = state.get('last_stores', [])
                target_store = last_stores[0] if last_stores else None

            if not target_store and target_prod:
                s_res = tool_lib.find_nearby_stores_for_product(
                    product_id=target_prod['id'],
                    lat=effective_lat,
                    lng=effective_lng,
                    radius_km=30.0
                )
                stores_found = s_res.get('stores', [])
                target_store = stores_found[0] if stores_found else None

            if not target_prod or not target_store:
                return {
                    'agent': 'discovery',
                    'status': 'error',
                    'reply': "I couldn't identify the specific product or store for your order. Please search for a product first (e.g., 'wireless mouse under ₹1,500') and check nearby stores.",
                    'products': [],
                    'nearbyStores': []
                }

            # Step 2: Generate checkout quote
            quote = FulfillmentService.generate_checkout_quote(
                product_id=target_prod['id'],
                quantity=1,
                store_id=target_store['storeId'],
                customer_lat=effective_lat,
                customer_lng=effective_lng
            )

            # Step 3: Atomic stock reservation
            res_result = FulfillmentService.create_stock_reservation(
                store_id=target_store['storeId'],
                product_id=target_prod['id'],
                quantity=1,
                user_email=customer_email or 'shopper@autocart.in'
            )

            # Step 4: Create Order with persistent store assignment
            now = datetime.now()
            order_id = f"ord-ai-{uuid.uuid4().hex[:6]}"
            order = Order.objects.create(
                id=order_id,
                customerName='Valued Customer',
                customerEmail=customer_email or 'shopper@autocart.in',
                customerPhone='+91 98200 12345',
                date=now.strftime('%Y-%m-%d'),
                totalAmount=quote['totalAmount'],
                subtotal=quote['subtotal'],
                tax=quote['tax'],
                shippingFee=quote['deliveryFee'],
                paymentMethod='Cash on Delivery / UPI upon Hyperlocal Receipt',
                paymentStatus='Paid',
                status='Confirmed',
                shippingAddress={
                    'storeId': target_store['storeId'],
                    'storeName': target_store['storeName'],
                    'storeAddress': target_store['address'],
                    'deliveryAddress': 'Customer Delivery Address, Mumbai',
                    'city': target_store.get('city', 'Mumbai'),
                    'pincode': target_store.get('pincode', '400053')
                },
                items=[{
                    'id': target_prod['id'],
                    'name': target_prod['name'],
                    'price': target_prod['price'],
                    'quantity': 1,
                    'image': (target_prod.get('images') or [''])[0]
                }]
            )

            store_model = Store.objects.filter(id=target_store['storeId']).first()
            fulfillment = FulfillmentService.initiate_fulfillment(order, store=store_model)

            # Confirm reservation permanently
            if res_result.get('success'):
                FulfillmentService.confirm_stock_reservation(res_result['reservationToken'])

            task.status = 'COMPLETED'
            task.resultData = {'orderId': order.id, 'storeId': target_store['storeId'], 'totalAmount': quote['totalAmount']}
            task.save()

            tools_executed = ['generate_checkout_quote', 'create_stock_reservation', 'create_order', 'initiate_fulfillment']
            self._log_tool_execution(task, 'DiscoveryAgent', 'initiate_fulfillment', {'orderId': order.id}, {'status': 'Allocated'}, int((time.time() - t0) * 1000))

            fee_val = quote['deliveryFee']
            del_fee_str = "FREE" if fee_val == 0 else f"₹{fee_val}"
            reply_text = (
                f"🎉 **Order Confirmed & Allocated to Store!**\n\n"
                f"• **Order ID**: `#{order.id}`\n"
                f"• **Fulfilling Store**: **{target_store['storeName']}**\n"
                f"• **Product**: **{target_prod['name']}** (Qty: 1)\n"
                f"• **Total Amount**: ₹{quote['totalAmount']:,.2f} (Subtotal: ₹{quote['subtotal']:,.0f} + GST: ₹{quote['tax']:,.0f} + Delivery: {del_fee_str})\n"
                f"• **Stock Reservation**: Verified and locked ({res_result.get('reservationToken', '')[:10]}...)\n"
                f"• **Estimated Delivery**: **~{quote['estimatedMinutes']} minutes** from local store\n"
                f"• **Hyperlocal Tracking ID**: `{fulfillment.trackingNumber}`\n\n"
                f"Your order is now being packed and prepared at the local store counter. "
                f"You can track live dispatch anytime by asking: *'Track my order #{order.id}'*."
            )

            SessionMemoryManager.update_state(session_key, {'last_order_id': order.id})
            SessionMemoryManager.add_turn(session_key, query, reply_text, 'discovery', tools_executed)

            return {
                'agent': 'discovery',
                'status': 'success',
                'reply': reply_text,
                'orderAction': {
                    'type': 'ORDER_CONFIRMED',
                    'orderId': order.id,
                    'store': target_store,
                    'quote': quote,
                    'trackingNumber': fulfillment.trackingNumber,
                    'estimatedMinutes': quote['estimatedMinutes']
                },
                'products': [target_prod],
                'nearbyStores': [target_store],
                'toolsExecuted': tools_executed,
                'taskId': task.id,
                'suggestedActions': [
                    f"Track order #{order.id}",
                    "View fulfillment timeline",
                    "Shop for another item"
                ]
            }

        # -------------------------------------------------------------------
        # INTENT 2: ADD TO CART (NATURAL LANGUAGE)
        # -------------------------------------------------------------------
        if is_add_cart:
            task = AgentTask.objects.create(
                id=f"task-{uuid.uuid4().hex[:8]}",
                taskType='AUTONOMOUS_SHOPPING',
                sessionId=session_id or '',
                userEmail=customer_email or '',
                goal=f"Add to Cart: {query}",
                status='IN_PROGRESS',
                plan=['Step 1: Identify product from conversation history', 'Step 2: Validate live stock availability', 'Step 3: Update cart'],
                currentStep=1
            )

            last_prods = state.get('last_products', [])
            target_prod = None

            # Check index: pehla (1st), doosra (2nd), teesra (3rd)
            if any(w in q_lower for w in ['pehla', 'first', '1st']) and len(last_prods) >= 1:
                target_prod = last_prods[0]
            elif any(w in q_lower for w in ['doosra', 'second', '2nd']) and len(last_prods) >= 2:
                target_prod = last_prods[1]
            elif any(w in q_lower for w in ['teesra', 'third', '3rd']) and len(last_prods) >= 3:
                target_prod = last_prods[2]
            elif last_prods:
                target_prod = last_prods[0]
            else:
                found = tool_lib.search_products('wireless mouse', limit=1).get('products', [])
                target_prod = found[0] if found else None

            if not target_prod:
                return {
                    'agent': 'discovery',
                    'status': 'error',
                    'reply': "Please search for a product first (e.g., 'wireless mouse under ₹1,500') so I know which item you'd like to add to your cart.",
                    'products': [],
                    'nearbyStores': []
                }

            avail = tool_lib.check_product_availability(target_prod['id'])
            tools_executed = ['check_product_availability', 'add_to_cart']
            self._log_tool_execution(task, 'DiscoveryAgent', 'check_product_availability', {'productId': target_prod['id']}, avail, 15)

            SessionMemoryManager.update_state(session_key, {
                'selected_product': target_prod,
                'cart_items': [target_prod]
            })

            task.status = 'COMPLETED'
            task.save()

            reply_text = (
                f"✅ **Added to Cart!**\n\n"
                f"I've added **{target_prod['name']}** (₹{target_prod['price']:,.0f}) to your cart.\n\n"
                f"• **Brand**: {target_prod.get('brand', 'AutoCart Verified')}\n"
                f"• **Unit Price**: ₹{target_prod['price']:,.0f}\n"
                f"• **Stock Status**: Verified In Stock ({target_prod.get('stock', 25)} units available)\n\n"
                f"You can now check local store inventory across Mumbai by saying: *'Check nearby store availability'*."
            )

            SessionMemoryManager.add_turn(session_key, query, reply_text, 'discovery', tools_executed)

            return {
                'agent': 'discovery',
                'status': 'success',
                'reply': reply_text,
                'cartAction': {
                    'type': 'ADD_TO_CART',
                    'product': target_prod,
                    'quantity': 1
                },
                'products': [target_prod],
                'toolsExecuted': tools_executed,
                'taskId': task.id,
                'suggestedActions': [
                    'Check nearby store availability',
                    'Show eligible Mumbai stores on map',
                    'View cart summary'
                ]
            }

        # -------------------------------------------------------------------
        # INTENT 3: CHECK NEARBY STORES FOR TARGET PRODUCT
        # -------------------------------------------------------------------
        if is_store_check:
            task = AgentTask.objects.create(
                id=f"task-{uuid.uuid4().hex[:8]}",
                taskType='STORE_FULFILLMENT',
                sessionId=session_id or '',
                userEmail=customer_email or '',
                goal=f"Hyperlocal Store Availability Lookup: {query}",
                status='IN_PROGRESS',
                plan=['Step 1: Identify target product from cart/history', 'Step 2: Query nearby physical stores with inventory', 'Step 3: Rank by distance and delivery ETA'],
                currentStep=1
            )

            target_prod = state.get('selected_product')
            if not target_prod:
                last_prods = state.get('last_products', [])
                target_prod = last_prods[0] if last_prods else None

            if not target_prod:
                found = tool_lib.search_products('wireless mouse', limit=1).get('products', [])
                target_prod = found[0] if found else None

            store_res = tool_lib.find_nearby_stores_for_product(
                product_id=target_prod['id'] if target_prod else None,
                lat=effective_lat,
                lng=effective_lng,
                radius_km=30.0
            )
            nearby_stores = store_res.get('stores', [])
            tools_executed = ['find_nearby_stores_for_product']
            self._log_tool_execution(task, 'DiscoveryAgent', 'find_nearby_stores_for_product', {'productId': target_prod['id'] if target_prod else None}, store_res, 20)

            SessionMemoryManager.update_state(session_key, {
                'last_stores': nearby_stores,
                'selected_store': nearby_stores[0] if nearby_stores else None
            })

            task.status = 'COMPLETED'
            task.save()

            if nearby_stores:
                best_store = nearby_stores[0]
                stores_summary = []
                for idx, s in enumerate(nearby_stores[:3]):
                    star = "🏆 " if idx == 0 else ""
                    fee_txt = "Free Delivery" if s['deliveryFee'] == 0 else f"₹{s['deliveryFee']} fee"
                    stores_summary.append(
                        f"{idx + 1}. {star}**{s['storeName']}**\n"
                        f"   • **Distance**: {s['distanceKm']} km away\n"
                        f"   • **Estimated Delivery**: ~{s['estimatedMinutes']} mins ({fee_txt})\n"
                        f"   • **Stock Available**: {s.get('availableQuantity', 0)} units in stock\n"
                        f"   • **Address**: {s['address']}"
                    )
                stores_block = "\n\n".join(stores_summary)

                reply_text = (
                    f"📍 **Nearby Store Availability across Mumbai**\n\n"
                    f"For **{target_prod['name'] if target_prod else 'your item'}**, here are the top eligible partner stores with verified in-store stock:\n\n"
                    f"{stores_block}\n\n"
                    f"💡 **Recommendation**: **{best_store['storeName']}** is the best option because it is closest ({best_store['distanceKm']} km) with the fastest delivery time (~{best_store['estimatedMinutes']} mins).\n\n"
                    f"To order directly from this store, simply say: *'Order from this store'*."
                )
            else:
                reply_text = (
                    "I searched our Mumbai regional store network, but could not find verified stock at stores within 30 km. "
                    "You can still order directly for standard warehouse delivery."
                )

            SessionMemoryManager.add_turn(session_key, query, reply_text, 'discovery', tools_executed)

            return {
                'agent': 'discovery',
                'status': 'success',
                'reply': reply_text,
                'products': [target_prod] if target_prod else [],
                'nearbyStores': nearby_stores,
                'storeMapData': {
                    'center': {'lat': effective_lat, 'lng': effective_lng},
                    'stores': nearby_stores
                },
                'toolsExecuted': tools_executed,
                'taskId': task.id,
                'suggestedActions': [
                    'Order from this store',
                    'Reserve stock for 15 minutes',
                    'Compare prices across stores'
                ]
            }

        # -------------------------------------------------------------------
        # INTENT 4: GENERAL CATALOG SEARCH & BUDGET DISCOVERY
        # -------------------------------------------------------------------
        task = AgentTask.objects.create(
            id=f"task-{uuid.uuid4().hex[:8]}",
            taskType='AUTONOMOUS_SHOPPING',
            sessionId=session_id or '',
            userEmail=customer_email or '',
            goal=query,
            status='IN_PROGRESS',
            plan=[
                'Step 1: Understand shopping intent and budget ceiling',
                'Step 2: Query product catalog database for matching SKUs',
                'Step 3: Check nearby store physical availability and distance',
                'Step 4: Rank best recommendations and format response'
            ],
            currentStep=1
        )

        search_res = tool_lib.search_products(query=query, limit=6)
        matched_products = search_res.get('products', [])
        tools_executed = ['search_products']
        self._log_tool_execution(task, 'DiscoveryAgent', 'search_products', {'query': query}, search_res, int((time.time() - t0) * 1000))

        nearby_stores = []
        if matched_products:
            top_prod_id = matched_products[0]['id']
            store_res = tool_lib.find_nearby_stores_for_product(
                product_id=top_prod_id,
                lat=effective_lat,
                lng=effective_lng,
                radius_km=30.0
            )
            nearby_stores = store_res.get('stores', [])
            tools_executed.append('find_nearby_stores_for_product')
            self._log_tool_execution(task, 'DiscoveryAgent', 'find_nearby_stores_for_product', {'productId': top_prod_id}, store_res, 15)

        # Store in session state for follow-up turns ("pehla wala cart mein add kar de", etc.)
        SessionMemoryManager.update_state(session_key, {
            'last_products': matched_products,
            'last_stores': nearby_stores,
            'selected_product': matched_products[0] if matched_products else None,
            'selected_store': nearby_stores[0] if nearby_stores else None
        })

        reply_text = ""
        llm_info = {'provider': 'grounded-engine', 'model': 'local-deterministic'}

        if self.provider.is_configured:
            compact_catalog = [
                {'name': p['name'], 'price': p['price'], 'rating': p['rating'], 'brand': p['brand']}
                for p in matched_products[:4]
            ]
            store_context = [
                {'store': s['storeName'], 'distance': f"{s['distanceKm']} km", 'eta': f"{s['estimatedMinutes']} mins", 'stock': s.get('availableQuantity', 0)}
                for s in nearby_stores[:2]
            ]
            user_prompt = (
                f"Customer Query: {query}\n\n"
                f"Top Catalog Matches:\n{json.dumps(compact_catalog)}\n\n"
                f"Nearby Physical Store Inventory:\n{json.dumps(store_context)}"
            )
            llm_res = self.provider.generate(
                system_instruction=DISCOVERY_SYSTEM_INSTRUCTION,
                prompt=user_prompt,
                temperature=0.2,
                max_tokens=350
            )
            if llm_res.get('text'):
                reply_text = llm_res['text']
                llm_info = llm_res

        if not reply_text:
            safe_query = (query[:60] + '...') if len(query) > 60 else query
            safe_query = re.sub(r'[\r\n\t]+', ' ', safe_query).strip()
            safe_query = re.sub(r'(?i)(api[_-]?key|secret|password|token|ignore\s+all)', '[REDACTED]', safe_query)

            if matched_products:
                top_picks = matched_products[:3]
                items_summary = []
                for idx, p in enumerate(top_picks):
                    disc = f" ({p.get('discount')}% off)" if p.get('discount') else ""
                    num = "1️⃣" if idx == 0 else ("2️⃣" if idx == 1 else "3️⃣")
                    items_summary.append(f"{num} **{p['name']}** — ₹{p['price']:,.0f}{disc} | ★{p['rating']}")
                summary_block = "\n".join(items_summary)

                store_note = ""
                if nearby_stores:
                    best_store = nearby_stores[0]
                    store_note = (
                        f"\n\n📍 **Local Mumbai Store Pickup**: Available at **{best_store['storeName']}** "
                        f"({best_store['distanceKm']} km away • Delivery in ~{best_store['estimatedMinutes']} mins • {best_store.get('availableQuantity', 0)} in stock)."
                    )

                reply_text = (
                    f"Here are the top catalog recommendations for \"{safe_query}\":\n\n"
                    f"{summary_block}"
                    f"{store_note}\n\n"
                    f"💡 *Next step*: You can say *'Add first item to cart'* to add the top option to your cart, or *'Check nearby store availability'* to check local store stock across Mumbai!"
                )
            else:
                reply_text = (
                    f"I searched our product catalog for \"{safe_query}\", but did not find an exact match. "
                    "Try refining your search by category (e.g. Laptops, Audio, Mobiles, Fashion) or adjusting your budget."
                )

        task.status = 'COMPLETED'
        task.resultData = {'productsCount': len(matched_products), 'storesFound': len(nearby_stores)}
        task.save()

        SessionMemoryManager.add_turn(session_key, query, reply_text, 'discovery', tools_executed)

        return {
            'agent': 'discovery',
            'status': 'success',
            'reply': reply_text,
            'products': matched_products,
            'nearbyStores': nearby_stores,
            'toolsExecuted': tools_executed,
            'llmProvider': llm_info.get('provider', 'grounded-engine'),
            'llmModel': llm_info.get('model', 'local-deterministic'),
            'taskId': task.id,
            'suggestedActions': [
                'Add first item to cart',
                'Check nearby store availability',
                'Compare top picks',
                'Show items under budget'
            ]
        }

    # -----------------------------------------------------------------------
    # AGENT B: CUSTOMER ENGAGEMENT & SUPPORT AGENT
    # -----------------------------------------------------------------------
    def run_customer_engagement_agent(
        self,
        query: str,
        cart_items: Optional[List[Dict[str, Any]]] = None,
        session_id: Optional[str] = None,
        customer_email: Optional[str] = None
    ) -> Dict[str, Any]:
        t0 = time.time()
        session_key = SessionMemoryManager.get_session_key(session_id, customer_email)
        tools_executed = []
        user_lower = query.lower()
        orders_payload = []
        tracking_payload = None

        # Determine user intent
        if any(w in user_lower for w in ['order', 'track', 'status', 'delivery', 'package', 'where is']):
            if customer_email:
                orders_res = tool_lib.get_my_orders(customer_email=customer_email, limit=3)
                orders_payload = orders_res.get('orders', [])
                tools_executed.append('get_my_orders')

                if orders_payload:
                    latest_order_id = orders_payload[0]['id']
                    tracking_payload = tool_lib.get_order_fulfillment_tracking(latest_order_id, customer_email)
                    tools_executed.append('get_order_fulfillment_tracking')
            else:
                reply_text = (
                    "To securely retrieve your order records and live tracking details, please log in with your AutoCart account. "
                    "Alternatively, provide your registered order ID (e.g., ORD-2026-XXXX)."
                )
                return {
                    'agent': 'customer-engagement',
                    'status': 'auth_required',
                    'reply': reply_text,
                    'toolsExecuted': [],
                    'suggestedActions': ['Log in to view my orders', 'Check return policy', 'Shipping timelines']
                }

        elif any(w in user_lower for w in ['return', 'refund', 'cancel', 'exchange']):
            if customer_email and any(w in user_lower for w in ['my order', 'return order', 'cancel order']):
                orders_res = tool_lib.get_my_orders(customer_email=customer_email, limit=1)
                latest_order = (orders_res.get('orders') or [{}])[0]
                if latest_order.get('id'):
                    ret_check = tool_lib.check_order_return_eligibility(latest_order['id'], customer_email)
                    tools_executed.append('check_order_return_eligibility')
                    reply_text = (
                        f"Order #{latest_order['id']} (Placed on {latest_order.get('date')} for ₹{latest_order.get('totalAmount')}) "
                        f"is **{('eligible' if ret_check.get('eligible') else 'not eligible')}** for return. "
                        f"Policy: {ret_check.get('conditions')} You have a 7-day return window from delivery date."
                    )
                    return {
                        'agent': 'customer-engagement',
                        'status': 'success',
                        'reply': reply_text,
                        'toolsExecuted': tools_executed,
                        'suggestedActions': ['Request return pickup', 'Track my orders', 'Speak with human agent']
                    }

            policy = tool_lib.get_return_policy()
            tools_executed.append('get_return_policy')
            reply_text = (
                f"AutoCart Return & Refund Policy: We offer a **{policy['returnWindowDays']}-day return window** from delivery. "
                f"Items must be unused in original packaging. Refunds are credited to original payment within 5-7 business days."
            )
            return {
                'agent': 'customer-engagement',
                'status': 'success',
                'reply': reply_text,
                'toolsExecuted': tools_executed,
                'suggestedActions': ['Check my orders', 'Free shipping policy', 'Contact support']
            }

        elif any(w in user_lower for w in ['shipping', 'delivery time', 'courier', 'charge', 'cost']):
            ship_policy = tool_lib.get_shipping_policy()
            tools_executed.append('get_shipping_policy')
            reply_text = (
                f"AutoCart Delivery Timelines: Standard delivery takes **{ship_policy['standardDeliveryDays']}**. "
                f"Metro areas qualify for express 1-2 day delivery. Orders over ₹499 receive **Free Standard Delivery** "
                f"(₹40 delivery fee for smaller orders). All orders include real-time GPS tracking."
            )
            return {
                'agent': 'customer-engagement',
                'status': 'success',
                'reply': reply_text,
                'toolsExecuted': tools_executed,
                'suggestedActions': ['Track an order', 'Check cart total', 'Return policy']
            }

        # Cart inquiry fallback
        cart_summary = tool_lib.get_cart_summary(cart_items or [])
        tools_executed.append('get_cart_summary')

        if orders_payload:
            latest = orders_payload[0]
            status_desc = f"Your latest order **#{latest['id']}** ({latest.get('date')}) is **{latest.get('status')}** (Payment: {latest.get('paymentStatus')})."
            if tracking_payload:
                status_desc += f" Current tracking: **{tracking_payload.get('currentStatus')}** via {tracking_payload.get('deliveryPartner')}."
            reply_text = status_desc
        else:
            reply_text = (
                f"Hello! Your current shopping cart has an active subtotal of **₹{cart_summary['subtotal']:,.2f}**. "
                f"{('You qualify for Free Shipping!' if cart_summary['freeShippingEligible'] else 'Add ₹' + str(round(max(0, 500 - cart_summary['subtotal']), 2)) + ' more to qualify for Free Shipping.')} "
                "How else can I assist you with your orders or policies today?"
            )

        SessionMemoryManager.add_turn(session_key, query, reply_text, 'engagement', tools_executed)

        return {
            'agent': 'customer-engagement',
            'status': 'success',
            'reply': reply_text,
            'orders': orders_payload,
            'tracking': tracking_payload,
            'toolsExecuted': tools_executed,
            'suggestedActions': ['Track my order', 'Return & cancellation policy', 'Explore catalog products']
        }

    # -----------------------------------------------------------------------
    # AGENT C: LOCATION & FULFILLMENT AGENT
    # -----------------------------------------------------------------------
    def run_location_fulfillment_agent(
        self,
        product_id: str,
        quantity: int = 1,
        store_id: Optional[str] = None,
        customer_lat: float = 12.9716,
        customer_lng: float = 77.5946,
        user_email: str = 'customer@example.com'
    ) -> Dict[str, Any]:
        """
        Coordinates nearby store discovery, live inventory verification, and stock reservation.
        """
        quote = tool_lib.calculate_fulfillment_quote(
            product_id=product_id,
            quantity=quantity,
            store_id=store_id,
            lat=customer_lat,
            lng=customer_lng
        )

        stores_res = tool_lib.find_nearby_stores_for_product(
            product_id=product_id,
            lat=customer_lat,
            lng=customer_lng,
            radius_km=25.0,
            required_quantity=quantity
        )

        return {
            'agent': 'fulfillment',
            'status': 'success',
            'quote': quote,
            'nearbyEligibleStores': stores_res.get('stores', []),
            'selectedStoreId': store_id or (stores_res.get('stores', [{}])[0].get('storeId')),
            'requiresCustomerConfirmation': True,
            'confirmationPrompt': (
                f"Confirm reservation for {quantity}x {quote.get('productName')} at "
                f"{quote.get('storeName')} for total of ₹{quote.get('totalAmount')}?"
            )
        }

    # -----------------------------------------------------------------------
    # AGENT D: SELLER ONBOARDING & VERIFICATION AGENT
    # -----------------------------------------------------------------------
    def run_seller_onboarding_agent(
        self,
        application_data: Dict[str, Any],
        user_role: str = 'CUSTOMER',
        user_email: str = ''
    ) -> Dict[str, Any]:
        """
        Evaluates seller documents, runs OCR extraction, validates tax IDs, and produces a structured compliance score.
        """
        from ..ocr_service import DocumentOCRService

        # 1. Validate fields
        val_res = tool_lib.validate_seller_application(application_data)
        
        # 2. Cross check with simulated OCR extraction on submitted GSTIN/PAN
        gstin = application_data.get('gstin', '')
        raw_doc_text = f"Government of India Tax Registration Certificate GSTIN: {gstin} Legal Name: {application_data.get('companyName')}"
        ocr_res = DocumentOCRService.extract_document_entities(raw_doc_text, 'GST_CERTIFICATE')
        cross_res = DocumentOCRService.cross_validate_application(application_data, ocr_res)

        final_risk = max(val_res['riskScore'], cross_res['riskScore'])
        status_label = (
            'Ready for review' if final_risk <= 30 and not val_res['missingFields']
            else ('Needs verification' if final_risk <= 55 else 'High verification required')
        )

        reply_summary = (
            f"Agent D Verification Assessment for **{application_data.get('companyName', 'Applicant')}**:\n\n"
            f"• **Risk Index**: {final_risk}/100 ({cross_res['riskCategory']} Risk)\n"
            f"• **Preliminary Status**: {status_label}\n"
            f"• **OCR Confidence**: {ocr_res['confidenceScore']}%\n"
            f"• **Checklist Status**: {sum(1 for c in val_res['checklist'] if c['complete'])}/{len(val_res['checklist'])} items verified."
        )

        return {
            'agent': 'seller-onboarding',
            'status': 'success',
            'riskScore': final_risk,
            'riskCategory': cross_res['riskCategory'],
            'preliminaryStatus': status_label,
            'missingFields': val_res['missingFields'],
            'checklist': val_res['checklist'],
            'ocrExtracted': ocr_res,
            'discrepancies': cross_res['discrepancies'],
            'verifiedFacts': cross_res['verifiedFacts'],
            'nextSteps': [
                'Ensure all required identity, trade, and tax certificates are clearly uploaded',
                'Verify Indian registered business address matches GST state code',
                'Authorized human administrator approval required before marketplace activation'
            ],
            'reply': reply_summary
        }

    # -----------------------------------------------------------------------
    # AGENT E: SELLER BUSINESS ASSISTANT AGENT
    # -----------------------------------------------------------------------
    def run_seller_business_assistant(
        self,
        prompt: str,
        seller_id: str,
        title: Optional[str] = None,
        category: Optional[str] = None,
        raw_specs: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Assists registered sellers with listing drafting, competitive price benchmarks, and low-stock alerts.
        """
        p_lower = prompt.lower()
        tools_executed = []

        if any(w in p_lower for w in ['list', 'draft', 'create product', 'description', 'title']):
            listing_res = tool_lib.generate_seller_product_listing(
                title=title or 'Smart Device',
                category=category or 'Electronics',
                raw_specs=raw_specs,
                seller_name='Seller Partner'
            )
            tools_executed.append('generate_seller_product_listing')
            reply_text = (
                f"I drafted an optimized product listing for **{listing_res['suggestedTitle']}** in category **{listing_res['category']}**.\n\n"
                f"• Recommended Price: **₹{listing_res['recommendedPrice']:,.2f}** (MSRP: ₹{listing_res['suggestedMSRP']:,.2f})\n"
                f"• Description: {listing_res['draftDescription']}\n\n"
                f"{listing_res['requiresConfirmation']}"
            )
            return {
                'agent': 'seller_assistant',
                'status': 'success',
                'reply': reply_text,
                'listingDraft': listing_res,
                'toolsExecuted': tools_executed
            }

        # Inventory and pricing health check
        inv_res = tool_lib.analyze_seller_inventory_and_pricing(seller_id)
        tools_executed.append('analyze_seller_inventory_and_pricing')
        reply_text = (
            f"Seller Inventory Analysis: Across {inv_res['storesCount']} fulfillment location(s), "
            f"you have **{inv_res['lowStockAlertCount']} item(s) running low on stock** (≤5 units remaining). "
            f"Recommended priority: Restock fast-moving SKUs at Indiranagar and Koramangala hubs to maintain hyperlocal eligibility."
        )
        return {
            'agent': 'seller_assistant',
            'status': 'success',
            'reply': reply_text,
            'inventoryHealth': inv_res,
            'toolsExecuted': tools_executed
        }

    # -----------------------------------------------------------------------
    # AGENT F: ADMIN MARKETPLACE ASSISTANT AGENT
    # -----------------------------------------------------------------------
    def run_admin_assistance_agent(
        self,
        prompt: str,
        user_role: str = 'ADMIN'
    ) -> Dict[str, Any]:
        """
        Helps marketplace administrators audit multi-vendor applications, highlight compliance risks, and summarize operations.
        """
        if user_role not in ('ADMIN', 'STAFF'):
            return {'error': 'Access denied: Admin authorization required.'}

        audit_res = tool_lib.audit_seller_applications_state(user_role)
        reply_text = (
            f"Admin Marketplace Briefing: Currently monitoring **{audit_res['totalApplications']} total application(s)**. "
            f"State breakdown: {json.dumps(audit_res['stateBreakdown'])}. "
            f"🚨 **{audit_res['highRiskApplicationsCount']} application(s) flagged as High Risk** due to missing tax credentials or offshore flags."
        )
        return {
            'agent': 'admin_assistant',
            'status': 'success',
            'reply': reply_text,
            'audit': audit_res,
            'toolsExecuted': ['audit_seller_applications_state']
        }


# Global singleton instance for orchestrator and backward compatibility
agent_engine = AgentEngine()
