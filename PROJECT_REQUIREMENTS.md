# AutoCart: What This Project Is, What It Needs, and How to Run It

A plain-language guide to the AutoCart project. Read this first if you are new to the code.

---

## 1. The project in one paragraph

AutoCart is an **online shopping website (like a small Amazon/Flipkart) with AI assistants built in**.
Customers can browse products, add them to a cart, check out, and track orders.
Sellers can apply to sell on the marketplace. Admins manage products, orders, users and seller applications.
The special part is the **AI agents**: a chat assistant that understands requests like
"show me a wireless mouse under ₹1500" or "where is my order?", answers using **real data from the database**,
and can find **nearby physical stores in Mumbai** that have the item in stock.

---

## 2. What the project owner actually wants (the requirements)

### 2.1 Core goal
Build a **portfolio-ready, production-style e-commerce platform** that shows off a real
**multi-agent AI system**, not just a chatbot glued onto a shop.

### 2.2 Must-have requirements

| # | Requirement | What it means in simple words |
|---|---|---|
| 1 | Full shopping flow | Home → products → product details → cart → coupon → checkout → order success → order tracking |
| 2 | User accounts | Register, login, profile, roles: **Customer**, **Seller**, **Admin** |
| 3 | Admin portal | Dashboard, products, categories, orders, users, sellers, inventory, coupons, reviews, analytics, settings |
| 4 | Seller marketplace | Sellers apply online, upload documents, and admins approve or reject them |
| 5 | AI agents grounded in data | The AI must **never invent** products, prices, ratings or order status. It only uses what the database says |
| 6 | Privacy and security | A customer can only see **their own** orders. Identity comes from the login token, not from what the user types |
| 7 | Human in the loop | The AI can score and summarise a seller application, but **only a human admin can approve it** |
| 8 | Works without an AI key | If no Gemini/Groq key is set, the site must still work using a built-in rule-based ("deterministic") engine |
| 9 | Hyperlocal delivery (Mumbai) | Find nearby partner stores with stock, show distance, delivery time and fee, and reserve stock |
| 10 | Tests | Automated tests prove the agents, data isolation, prompt-injection resistance and cart maths work |

### 2.3 The AI agents (the heart of the project)

The README lists 3 agents; the code (`backend/api/agents/engine.py`) actually has **6**:

| Agent | Who uses it | What it does |
|---|---|---|
| **A. Discovery & Shopping** | Customer | Searches products, filters by budget, compares items, checks nearby store stock. Understands English **and Hinglish** ("aas paas store", "cart mein add") |
| **B. Customer Engagement & Support** | Customer | Order tracking, return/refund policy (7-day window), cart total, cancellations |
| **C. Location & Fulfillment** | Customer | Picks the best nearby store, gives a delivery quote, reserves stock |
| **D. Seller Onboarding & Verification** | Seller / Admin | Checks GSTIN, PAN, bank details, reads documents (OCR), gives a risk score |
| **E. Seller Business Assistant** | Seller | Drafts product listings, compares prices, warns about low stock |
| **F. Admin Marketplace Assistant** | Admin | Summarises pending applications, highlights high-risk ones |

How one AI request flows:

```
User message
   → login check (JWT token)
   → pick the right agent
   → agent decides which "tools" to call (e.g. search_products, get_my_orders)
   → tools read the real database
   → LLM (Groq or Gemini) writes a friendly answer from those results
     (if no LLM is available, a rule-based answer is used instead)
   → every tool call is saved in AgentExecutionLog for auditing
```

---

## 3. What is needed to build and run it

### 3.1 Tech stack (what is already used)

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 6, Tailwind CSS, React Router, Framer Motion, Recharts, Axios |
| Backend | Python, Django 5, Django REST Framework, PyJWT, django-cors-headers |
| Database | SQLite (`backend/db.sqlite3`), fine for development |
| AI | Groq (Llama 3.3) first, Google Gemini second, rule-based fallback last |

### 3.2 Software you need on your computer

- **Python 3.10+** (this machine has 3.12)
- **Node.js 18+ and npm** (this machine has Node 24)
- Optional: a **Gemini API key** (free at <https://aistudio.google.com/app/apikey>) or a **Groq API key**

### 3.3 Configuration (`.env` in the project root)

```bash
VITE_API_BASE_URL=http://localhost:8000/api
GEMINI_API_KEY=your_key_here      # optional
GEMINI_MODEL=gemini-2.5-flash
GEMINI_TIMEOUT=30
# GROQ_API_KEY=your_key_here      # optional, used before Gemini if set
```

### 3.4 Project map

```
AutoCart_Agentic_AI_Production/
├── .env / .env.example        settings and API keys
├── package.json, vite.config.js   frontend config
├── src/                       React frontend
│   ├── pages/customer/        shop pages (Home, Products, Cart, Checkout, Orders...)
│   ├── pages/admin/           admin portal pages
│   ├── pages/seller/          seller apply + dashboard
│   ├── components/            reusable UI (navbar, product cards, AI drawer, map...)
│   ├── context/               global state (auth, cart, wishlist, location, theme)
│   └── services/              API calls to the backend
└── backend/                   Django backend
    ├── autocart_core/         Django settings and root URLs
    ├── api/models.py          database tables (User, Product, Order, Store, SellerApplication...)
    ├── api/views.py           REST API endpoints
    ├── api/agents/            the AI system: engine (6 agents), tools, LLM provider, memory
    ├── api/location_service.py    distance + nearby store search
    ├── api/fulfillment_service.py stock reservation + delivery quotes
    ├── api/ocr_service.py     seller document reading and checks
    ├── api/tests.py, test_marketplace_features.py   automated tests
    └── seed_*.py              scripts that fill the database with demo data
```

### 3.5 Main API endpoints (all under `http://localhost:8000/api/`)

| Area | Endpoints |
|---|---|
| Auth | `auth/login`, `auth/register`, `auth/me` |
| Catalog | `products`, `categories`, `coupons`, `coupons/apply` |
| Orders | `orders`, `orders/quote`, `orders/reserve-stock`, `orders/<id>/tracking`, `orders/<id>/return`, `orders/<id>/cancel` |
| Stores | `stores/nearby`, `stores/zones`, `stores/<id>/inventory` |
| AI agents | `ai/discovery`, `ai/customer-engagement`, `ai/seller-onboarding`, `ai/seller-assistant`, `ai/admin-assistant`, `ai/recommendations`, `ai/compare`, `ai/shopping-assistant` |
| Sellers / Admin | `seller/applications`, `admin/seller-applications/<id>/action`, `admin/stats`, `admin/analytics`, `sellers`, `users` |

---

## 4. How to run it (step by step, Windows)

Open **two terminals**.

**Terminal 1: backend**
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python seed_db.py                 # demo products, categories, coupons, users
python seed_mumbai_network.py     # optional: Mumbai stores + inventory
python manage.py test             # run the tests
python manage.py runserver 127.0.0.1:8000
```

**Terminal 2: frontend**
```bash
npm install
npm run dev
```

Then open **http://localhost:5173**.

| Role | Email | Password |
|---|---|---|
| Customer | `customer@example.com` | `password` |
| Admin | `admin@auracart.com` | `admin123` |

Admin portal: <http://localhost:5173/admin>

---

## 5. Things to know / gaps to fix before calling it "production"

These are honest observations from reading the code. None of them stop the project from running locally.

**Security (important before going live)**
1. **Login backdoor:** `login_view` in `backend/api/views.py` accepts any of `password`, `admin123`, `password123`, `admin`, `123456` for **any** account, and lets users with no password log in with anything. Fine for a demo, dangerous in production.
2. `SECRET_KEY` is hard-coded in `settings.py`, `DEBUG = True`, `ALLOWED_HOSTS = ['*']`, and `CORS_ALLOW_ALL_ORIGINS = True`. Move these to `.env` for production.
3. All endpoints default to `AllowAny` permission. Each view checks the token by hand, so a missed check would be an open endpoint.

**Mismatches between docs and code**
4. The README says 3 agents; the code has 6.
5. The README only mentions Gemini; the code also supports Groq and **prefers Groq** if `GROQ_API_KEY` is set.
6. The README and `.env.example` say `gemini-2.5-flash`, but the code default **and the current `.env`** use `gemini-3.8-flash`. When the project was run, a Gemini reply came back as broken text (`").\n * Strict grounding to provided items and"`) while the product cards were correct. Check the model name and the reply parsing in `engine.py`. This also makes `test_discovery_agent_workflow` fail (21/22 tests pass): the reply is cut off mid-sentence. A likely cause is that the `max_output_tokens` limit in `llm_provider.py` gets used up before the answer finishes. The tests also take about 7 minutes because they call the live Gemini API.
7. `package.json` is named `auracart-ecommerce` and the admin email is `@auracart.com`. The project was renamed from "AuraCart" to "AutoCart" and some old names are still there.

**Production gaps**
8. SQLite and in-memory chat memory: chat history is lost when the server restarts, and SQLite won't handle many users at once. Use PostgreSQL + Redis for production.
9. No Docker setup, no CI pipeline, no deployment config.
10. Some frontend components still import mock data files (`src/data/mock*.js`), even though `USE_MOCK_API = false`.

---

## 6. How to make the project clearer (suggestions)

1. **Update the README** to list all 6 agents, both LLM providers, and the seed scripts (in the order to run them).
2. **Add one architecture diagram** (frontend → Django API → agent engine → tools → database / LLM).
3. **Write one short "demo script"**: 5 example chat messages that show off each agent.
4. **Remove the login backdoor** behind a `DEMO_MODE=true` setting so it is obvious and easy to turn off.
5. **Delete unused duplicate files.** For example, there are both `src/pages/HomePage.jsx` and `src/pages/customer/Home.jsx`, and two `MainLayout.jsx` and two `Footer.jsx` files.
6. **Add a single start command** (for example a `start.bat` or `docker-compose.yml`) so the backend and frontend start together.

---

## 7. Startup vision: turning AutoCart into a real business

This section treats AutoCart as a startup launching tomorrow: real customers, real sellers, real local stores, real money. It covers what must change, how to compete with much bigger players, and how to build the best customer support and engagement in the market.

### 7.1 Who it is for

| User | What they want | What AutoCart must give them |
|---|---|---|
| **Shoppers** (anyone with a phone) | Find the right product fast, trust it, get it quickly, return it easily | Honest AI help, real photos and reviews, same-day local delivery, refunds in hours, not weeks |
| **Local store owners** (electronics, fashion, grocery, pharmacy shops) | More customers without building their own website | Free onboarding, a simple stock app, fast payouts, fair commission |
| **Brands and online sellers** | A new sales channel | Bulk listing tools, analytics, ads |
| **Delivery partners** | Steady work | Clear routes, fair pay per km |

### 7.2 How to compete with Amazon, Flipkart, Blinkit, Zepto and others

Don't try to beat them at everything on day one. Win with something they don't do well, then expand.

**The wedge: "Your neighbourhood shops, online, delivered in under an hour."**
The code already has the hard part: 67 Mumbai stores with live stock, distance-based delivery quotes, and stock reservation. Quick-commerce apps mostly use their own dark stores and focus on groceries. Marketplaces deliver from far-away warehouses in 1–3 days. AutoCart can deliver **electronics, fashion, gifts, pharmacy and hardware** from real local shops the same day, and let people **walk in and pick up**.

| Advantage | Why the big players can't easily copy it |
|---|---|
| Real local stores as the warehouse | Almost no inventory cost; shops are already stocked and staffed |
| See it before you buy it | Reserve online, try in store, pay only if you like it |
| AI shopping help in Hinglish, Hindi and Marathi | Feels like talking to a helpful shopkeeper, not a search box |
| Fast, fair seller onboarding | AI checks GSTIN/PAN in minutes; small shops are live in a day |
| Support that actually solves the problem | See section 7.4. This is where most big apps disappoint |

**Expansion path:** one city (Mumbai) → 3–5 metros → more categories → brands and ads → other cities.

### 7.3 What must change to go from demo to real product

**Must-have before the first real customer**

| Area | What to build | Current state in code |
|---|---|---|
| **Real login** | OTP login by phone (most Indian users prefer it), Google sign-in, secure password reset, remove the demo password backdoor | Demo backdoor in `login_view` |
| **Payments** | UPI, cards, net banking, wallets and Cash on Delivery through a payment gateway (e.g. Razorpay, Cashfree, PhonePe PG); webhooks to confirm payment; automatic refunds | Payment method is only a text field on `Order` |
| **Seller payouts** | Split payments, commission, weekly or daily payouts to the seller's bank account, invoices | Not built |
| **Real delivery** | Integrate a hyperlocal delivery partner API (e.g. Porter, Shadowfax) and a courier aggregator for longer distances (e.g. Shiprocket, Delhivery); live rider tracking | Delivery is simulated (`AutoCart Hyperlocal Express (Dev)`) |
| **Real seller onboarding** | Live GSTIN and PAN verification APIs, bank account penny-drop check, signed seller agreement | OCR and checks exist but are rule-based |
| **Store stock sync** | A simple seller app or a link to the store's billing/POS software, so online stock matches the shelf | Stock is seeded once |
| **Notifications** | SMS, email, WhatsApp and push for order confirmed, out for delivery, delivered, refund done | Not built |
| **Invoices and GST** | Auto GST invoice per order, TCS collection for sellers as required for marketplaces | Tax is calculated but no invoice |
| **Infrastructure** | PostgreSQL, Redis (sessions, chat memory, cache), cloud hosting, CDN for images, backups, monitoring, error tracking | SQLite, in-memory chat memory |
| **Security** | Secrets in environment, HTTPS, rate limiting, proper permission classes, audit logs, regular security review | See section 5 |

**Legal and compliance in India (talk to a lawyer and a CA)**
- **Consumer Protection (E-Commerce) Rules, 2020:** show seller details, return/refund/exchange policy, country of origin, total price including all charges; appoint a **grievance officer** and acknowledge complaints within 48 hours and resolve them within one month.
- **Digital Personal Data Protection (DPDP) Act, 2023:** clear consent for personal data, a privacy policy, let users see and delete their data, report data breaches.
- **GST:** register the marketplace, collect TCS from sellers, file returns.
- **Terms of use, seller agreement, privacy policy, return policy, shipping policy** published on the site.
- Category-specific rules (for example, medicines need a licensed pharmacy partner and prescription checks).

**Needed to compete (first 3–6 months after launch)**
- Fast search with typo tolerance, filters and Hindi/Hinglish support (e.g. Meilisearch, Typesense or Elasticsearch)
- Real product reviews and ratings with photos, and "verified buyer" badges
- Personalised home page and recommendations
- A mobile app (React Native or a Progressive Web App first), since most Indian shoppers buy on phones
- Offers engine: coupons, bank offers, first-order discount, free delivery thresholds
- Seller app: orders, stock, payouts, AI listing helper (Agent E already exists)
- Admin tools: fraud checks, fake-review detection, refund abuse detection, dispute resolution
- Analytics: conversion funnel, cart abandonment, repeat rate, delivery time, refund time

### 7.4 World-class customer support and engagement

**Goal: a customer should never feel stuck.** Every question is answered in seconds, every problem is fixed in one conversation, and a real human is always one tap away.

#### A. Before buying: helping people see and understand the product

| Feature | How it works | Builds on |
|---|---|---|
| **Ask anything about this product** | A chat box on every product page. The AI answers from the product's real specs, reviews and seller Q&A ("Will this charger work with iPhone 15?", "Is this cotton?"). If it doesn't know, it says so and forwards the question to the seller | Agent A, `get_product_details` |
| **Rich product view** | Multiple real photos, zoom, 360° view, short videos, size charts, "what's in the box" | `Product.images` |
| **Live video shopping** | One tap to start a short video call with the local store's staff, who show the actual item on camera | New feature; local stores make this possible |
| **See it in store** | "Available at 3 stores near you." Reserve now, try it in person, pay only if you like it. Directions and store hours shown | `find_nearby_stores_for_product`, `reserve_store_stock` |
| **Compare and decide** | AI comparison of 2–4 products in plain words: "Pick A if you travel a lot, B if you game" | `compare_products` |
| **Budget and need-based help** | "I need a laptop for college under ₹50,000." The AI asks 2–3 short questions, then recommends | Agent A, `filter_products_by_budget` |
| **Community Q&A and photo reviews** | Questions answered by buyers and sellers; reviews with real customer photos | New `Review` and `Question` models |
| **Honest stock and delivery promise** | "Arrives today by 7 PM from Andheri store" shown before checkout, based on real stock | `calculate_fulfillment_quote` |

#### B. During checkout

- **Cart helper:** explains the total (price, GST, delivery fee, coupon) line by line. *Builds on `get_cart_summary`.*
- **Best coupon applied automatically**, so the customer never has to search for codes.
- **Payment failure rescue:** if a UPI payment fails, instantly offer to retry, switch method, or choose Cash on Delivery, and confirm that no money was taken (or that it will be refunded automatically).
- **Abandoned cart reminder** (one gentle WhatsApp or push message, not spam).

#### C. After buying: proactive support

**The best support is the question the customer never had to ask.**

- **Proactive updates** on WhatsApp, SMS and push: confirmed → packed → out for delivery (live rider map) → delivered.
- **Delay alert before the customer notices:** "Your order is running 20 minutes late because of rain. Here is a ₹50 voucher." *Builds on `OrderFulfillment.timeline`.*
- **One-tap returns:** check eligibility instantly, pick a return reason, schedule a pickup or drop at the nearest store. *Builds on `check_order_return_eligibility`.*
- **Photo-based damage claims:** upload a photo of the damaged or wrong item, and the AI checks it and approves a refund or replacement on the spot for low-value orders.
- **Instant refunds** to UPI or wallet for trusted customers, before the item is even picked up.
- **Easy cancellation** before dispatch, with no questions asked. *Builds on `request_order_cancellation`.*
- **Post-delivery check-in:** "Is everything OK with your headphones?" plus a review request after a few days.

#### D. Support channels and the human handoff

| Channel | Why |
|---|---|
| **In-app and website AI chat** (24/7) | Instant answers for most questions |
| **WhatsApp support** (WhatsApp Business API) | Where Indian customers already are |
| **Voice support** (call or voice note, AI first, then human) | For people who prefer talking or can't type easily |
| **Email** | For invoices, formal complaints |
| **Store walk-in** | Partner stores can handle returns and exchanges in person |

**Languages:** English, Hindi, Hinglish and Marathi first (the discovery agent already understands Hinglish), more languages per city.

**Smart human handoff (must-have):**
1. The AI hands over to a human agent when the customer asks, is upset, a refund is above a set limit, the AI is unsure, or the same issue repeats.
2. The human sees the **full context**: chat history, order, payment, delivery timeline, and what the AI already tried. The customer never repeats themselves.
3. Every conversation becomes a **support ticket** with a status, priority, owner and deadline (SLA).
4. Unresolved tickets move automatically to the grievance officer, as the law requires.

*New models needed:* `SupportTicket`, `TicketMessage`, `Escalation`, plus an agent dashboard in the admin portal. Chat memory must move from in-memory to Redis/PostgreSQL so no conversation is lost.

**Service promises to publish and measure**

| Promise | Target |
|---|---|
| First reply (AI) | Under 5 seconds, 24/7 |
| First reply (human, when escalated) | Under 2 minutes in working hours |
| Problem solved in the first conversation | 80% or more |
| Refund credited after approval | Within 2 hours for UPI/wallet |
| Customer satisfaction (CSAT) after each chat | 4.5 / 5 or higher |

#### E. Engagement: bringing people back

- **Wishlist alerts:** price drop and back-in-stock notifications. *Builds on the existing wishlist.*
- **Personal recommendations** based on what the person browsed and bought, never creepy, always explainable ("because you bought a laptop").
- **Loyalty programme:** coins on every order, free delivery tier, birthday offers.
- **Referral rewards:** both friends get credit.
- **Local deals:** "Flash sale at your nearest store today."
- **Order again** in one tap for repeat purchases.
- **Respect the customer:** limit messages, easy unsubscribe, and the AI is always labelled as AI.

#### F. Trust and safety (needed for any of the above to work)

- AI must stay **grounded**: only real products, prices, stock and order data (already a core rule in the code).
- Verified sellers only, with ratings visible; repeat-offender sellers removed.
- Fake review detection; "verified purchase" labels.
- Fraud checks on refunds and Cash on Delivery orders.
- Clear, short policies written in plain language and shown before payment.

### 7.5 Suggested launch roadmap

| Phase | Time (rough) | Focus |
|---|---|---|
| **0. Fix the foundation** | 2–4 weeks | Security fixes from section 5, PostgreSQL + Redis, fix the broken Gemini replies, Docker, CI, monitoring |
| **1. Real transactions** | 4–6 weeks | OTP login, payment gateway, seller payouts, GST invoices, real delivery partner, notifications, legal pages |
| **2. Pilot in one area** | 4–8 weeks | 20–50 real stores in 2–3 Mumbai neighbourhoods, real customers, support tickets and human handoff, WhatsApp support |
| **3. Best-in-class support** | ongoing | Product Q&A chat, photo damage claims, instant refunds, live video shopping, voice support, proactive delay alerts |
| **4. Grow** | after the pilot proves repeat customers | Mobile app, loyalty and referrals, more categories, more Mumbai areas, then other metros |

### 7.6 Numbers that show the business is working

| Metric | What it tells you |
|---|---|
| Repeat purchase rate (30 / 90 days) | Do people come back? The most important number |
| Average delivery time | Is the "under an hour" promise real? |
| Conversion rate (visit → order) | Is the shopping experience good? |
| Cart abandonment rate | Is checkout or pricing a problem? |
| CSAT and first-contact resolution | Is support actually good? |
| Refund time | Do customers trust you with their money? |
| Seller retention and monthly sales per store | Are stores making money with you? |
| Contribution margin per order | Do you make money after delivery, discounts and payment fees? |

---

## AI agents by role: requirements and honest status (updated)

Goal: a customer, seller and admin experience that is useful in real life, using free tools only (Groq/Gemini free tiers with a rule-based fallback, local OCR, OpenStreetMap, Razorpay TEST mode only).

Rules for every agent: answer only from data in our database; never invent products, prices, reviews or stock; say "I don't know" and offer a human; show why a suggestion was made; no personal documents sent to any LLM.

| Role | Agent / feature | Requirement | Status |
|---|---|---|---|
| Customer | Shopping assistant (chat) | Find products by need and budget, show product cards with Add to cart, compare, check nearby store stock, hand off to a person | Built |
| Customer | Instant product answers | "Quick answers" and a comparison table computed from product data, no waiting for a seller | Built |
| Customer | Support tickets | Chat can open a ticket; customer sees "My tickets" | Built |
| Customer | Curiosity and sales signals | Deal of the day with countdown, real ratings/review counts, "almost gone" from real stock, savings from real MRP | Built (real signals only) |
| Customer | Personalised "picked for you" | Based on browsing history | Planned, not built |
| Seller | Onboarding agent | Masked Aadhaar/PAN/GST upload, local OCR, form-vs-document check, risk score | Built |
| Seller | Seller centre | Own products, price/stock edit, own orders (share only), customer questions, AI answer drafts, restock tips | Built |
| Seller | Order status updates | Seller moves orders through packed/shipped/delivered | Planned, not built |
| Admin | Attention panel and daily briefing | Counts of pending seller applications, tickets, enquiries, low stock, payment mode, in plain language | Built |
| Admin | Application review | Risk summary, approve/reject/request info/suspend with audit trail | Built |
| Admin | Fraud/anomaly detection | Unusual orders or refunds | Planned, not built |

Visibility rules (built and browser-tested): customers never see admin or seller links or data; sellers see only their own products and order share; admin tools live behind /admin/login, seller tools behind /seller/login.

Known gaps: PostgreSQL/Redis/Docker not used yet (SQLite); some sample products have wrong photos or an absurd price in seed data; real Razorpay test checkout and Gmail sending need your own keys in .env; legal pages missing.

### Assistants and seller business model (updated)

- **Saathi** (customer assistant): greets the signed-in customer by first name, remembers only categories, a usual budget and the last few searches (table `UserMemory`), and the customer can see and delete this from the chat ("What Saathi remembers" and "Forget everything"). Answers use real catalogue and the customer's own orders. Gemini is used when available; a database-grounded engine is the fallback.
- **Munim** (seller assistant): separate bot inside the Seller centre. The database computes the numbers; Gemini only words the answer from those facts; if Gemini is unavailable the plain database answer is shown. It can only see the signed-in seller's own products and orders.
- The old "Advanced assistant" drawer was removed from the chat.
- **Seller dashboard**: revenue-per-day chart, best sellers chart, and an earnings breakdown (item total, commission, what the seller keeps), each with a plain-language headline.
- **Business model** (`backend/api/commission.py`, public at `/api/commission`): free to join, list and no monthly fee; commission only on a sale, by category (Electronics 5%, Fashion 10%, Home & Kitchen 8%, Beauty 8%, Sports 7%, Books 4%, Grocery 3%, Toys 7%, default 6%); online payments add the payment provider charge (about 2%) at cost. These are proposed launch rates modelled on how large Indian marketplaces charge referral fees, not a signed price list or exact copies of any company's rates.
