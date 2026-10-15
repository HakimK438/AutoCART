# AutoCart: Complete Plan (Free Stack)

The full plan to take AutoCart from a working demo to a real marketplace that real shoppers, real local stores and real sellers can use, **using only free tools**.

Related files:
- [PROJECT_REQUIREMENTS.md](PROJECT_REQUIREMENTS.md): what the project is and why
- [README_FREE_STACK.md](README_FREE_STACK.md): short summary of the free tools and seller onboarding
- [PROMPTS.md](PROMPTS.md): copy-paste prompts to build each phase

> Status today: shop, cart, orders, admin portal, 6 AI agents, Mumbai store map and tests exist. Seller onboarding is partly broken and there is no real login security, payments, notifications or support system. Everything below marked **(new)** is not built yet.

---

## 1. Product in one page

**What:** an online marketplace where nearby local shops sell to nearby shoppers, with same-day delivery or pickup, and AI help that only tells the truth.

**Who uses it**

| User | Wants | AutoCart gives |
|---|---|---|
| Shopper | Find the right product, trust it, get it fast, return it easily | Honest AI help, nearby stock, clear delivery time, easy returns |
| Seller (local shop) | Customers without building a website | Free signup, simple stock and order screens, fair rules |
| Admin | Keep the marketplace safe | Seller review, order and complaint tools, reports |
| Support agent (human) | Solve problems fast | Ticket inbox with full chat and order history |

**How we compete with bigger players:** not by copying them. We win on "your neighbourhood shops, online, same day": real stock from real shops, try before you pay (reserve and pick up), AI help in English, Hindi, Hinglish and Marathi, and support that really solves the problem.

---

## 2. Free stack (nothing paid)

| Need | Free choice now | Paid, later only |
|---|---|---|
| Frontend | React 18, Vite, Tailwind, Framer Motion, Recharts (already used) | |
| Backend | Django 5 + Django REST Framework (already used) | |
| Database | SQLite now; PostgreSQL in Docker before the pilot | Managed database |
| Cache / chat memory | Redis in Docker (free), added in phase 0 | |
| Login | Email + password, email OTP (Gmail SMTP), Google sign-in | SMS OTP |
| Payments | Cash on Delivery, pay at store | Payment gateway |
| Notifications | Email (Gmail SMTP), in-app, browser push (Firebase Cloud Messaging) | WhatsApp, SMS |
| Delivery | Store's own staff or customer pickup | Courier / hyperlocal APIs |
| AI replies | Gemini and Groq free tiers + built-in rule-based fallback | Paid LLM plan |
| OCR | Tesseract (local) | Cloud OCR |
| Maps | Leaflet + OpenStreetMap | Google Maps |
| Address to location | Nominatim (1 request per second, set a User-Agent) | Paid geocoding |
| Video call with store | Jitsi Meet embed | |
| Voice input | Browser Web Speech API | |
| Search | Database search now; Meilisearch (open source) in phase 6 | |
| Images | Local storage now; Cloudinary free tier later | |
| Errors / logs | Python logging + admin log page | Sentry paid plans |
| Hosting | Local / Docker on your machine; free tiers (Render, Vercel, Neon) for a demo | Paid hosting |

Free tiers have limits and rules that change. Check each provider's current terms before relying on it. Free tools do not remove legal duties (section 10).

---

## 3. Architecture

```
 Browser (React)
   shopper / seller / admin / support screens
        │  HTTPS, JWT
        ▼
 Django REST API ──► Auth, permissions, rate limits, request log
   │  │  │  │
   │  │  │  └─► Notification service ──► Gmail SMTP / in-app / Firebase push
   │  │  └────► Seller documents ──► private storage ──► Tesseract OCR
   │  └───────► AI agent engine (6 agents) ──► tools ──► database
   │                                  └─► Gemini / Groq  (fallback: rule-based)
   ▼
 Database (SQLite → PostgreSQL)      Redis (sessions, chat memory, cache)
```

Rules that never change:
1. The AI **only reads real data** through tools. It never invents products, prices, stock or order status.
2. A customer sees **only their own** orders and tickets.
3. A **human admin** makes the final decision on sellers and large refunds.
4. Anything the AI is unsure about is passed to a human.

---

## 4. Roles and permissions

| Action | Guest | Customer | Seller | Support | Admin |
|---|---|---|---|---|---|
| Browse, search, ask AI | yes | yes | yes | yes | yes |
| Cart and checkout | no | yes | yes | no | no |
| See own orders | no | yes | yes | no | all |
| Apply to become a seller | no | yes | n/a | no | no |
| Manage own products, stock, orders | no | no | yes | no | all |
| Reply to tickets | no | own | own | all | all |
| Approve / reject / suspend sellers | no | no | no | no | yes |
| Refund above the limit | no | no | no | request | yes |

All of this is enforced **on the server**, not just hidden in the screens.

---

## 5. Data model

**Exists today:** User, Category, Product, Coupon, Seller, Order, Store, StoreInventory, InventoryReservation, SellerApplication, SellerApplicationAudit, OrderFulfillment, AgentTask, AgentExecutionLog.

**To add (new)**

| Model | Phase | Purpose |
|---|---|---|
| SellerDocument | 1 | Uploaded document, OCR status, masked extracted fields |
| (fields on SellerApplication) | 1 | Store name and location, planned products, masked identity, Aadhaar last 4 |
| Review, ProductQuestion | 4 | Photo reviews, product Q&A |
| Notification | 3 | In-app and push messages |
| SupportTicket, TicketMessage, Escalation | 5 | Support inbox with SLA and history |
| ChatSession, ChatMessage | 5 | Persist AI chat (replaces in-memory) |
| ReturnRequest, Refund | 3 | Returns with photos, reasons, status |
| LoyaltyAccount, LoyaltyEntry | 6 | Points and rewards |
| AuditLog | 0 | Who did what, for admin actions |

All schema changes are **new Django migrations**. Existing migrations are never edited.

---

## 6. Seller onboarding (full design)

### 6.1 Seller steps
1. Log in, open **Become a seller**.
2. **Business details:** store name, contact person, email, phone, business type.
3. **Tax and location:** GSTIN, PAN, store address, PIN code, a **pin on the map** for the exact location.
4. **Products you sell:** categories plus 3–10 sample products (name, category, approximate price).
5. **Upload documents** (the system reads each one and shows what it found straight away):

| Document | Required |
|---|---|
| Aadhaar (masked copy from myAadhaar) | yes |
| PAN card | yes |
| GST certificate | yes |
| Store address proof | yes |
| Bank proof (cancelled cheque or passbook) | yes |
| Store photo | yes |

6. Review and submit. A status page shows progress and any admin message.

### 6.2 What the system checks
- File type and size (images and PDF, up to 10 MB).
- Aadhaar: reads name, date of birth, gender, address, last 4 digits. **Rejects** any file showing all 12 digits.
- PAN: reads PAN, name, date of birth.
- Compares document values with the form: PAN, name, PIN code, and the PAN hidden inside the GSTIN.
- Produces a risk score and a checklist.
- If Tesseract is missing or a file is unreadable, the application goes to manual review. It never crashes.

### 6.3 What the admin sees
One **seller profile**: identity (masked), business details, **store location map**, **products sold**, each document (viewable), form-vs-document comparison, risk score, checklist, full history. Buttons: **Approve**, **Reject** (reason required), **Request more information**, **Suspend**.

### 6.4 Status flow
```
Submit ► DOCUMENT_PROCESSING
   ├─ missing docs ───────► NEEDS_MORE_INFORMATION ─(seller uploads)─► DOCUMENT_PROCESSING
   ├─ unreadable/mismatch ► NEEDS_MANUAL_REVIEW
   └─ all good ───────────► PENDING_ADMIN_APPROVAL
Admin: APPROVE ► APPROVED   REJECT ► REJECTED   REQUEST_INFO ► NEEDS_MORE_INFORMATION   SUSPEND ► SUSPENDED
```
On **APPROVE**: create the Seller, create a Store on the map, set the user's role to SELLER, notify the seller. Every step is written to the history. **The AI never approves anyone.**

### 6.5 Aadhaar and privacy
- Accept only masked Aadhaar; store only the last 4 digits; remove the number from saved text.
- Documents are saved in a private folder and are only served to the owner and admins.
- Show a plain-language consent notice before upload and let sellers request deletion after leaving.

---

## 7. Customer support and engagement (full design)

**Goal:** the customer is never stuck. Fast answers, one-conversation fixes, a human always one tap away.

### 7.1 Before buying
- **Ask about this product:** chat on every product page, answers from real specs, reviews and seller Q&A; says "I don't know" and asks the seller when unsure.
- **See it first:** reserve at a nearby store, try it, pay at the store.
- **Video call with the store** (Jitsi) to see the real item.
- **Compare** 2–4 products in plain words. **Budget help** ("laptop for college under ₹50,000").
- **Reviews with photos** and a "verified buyer" label.
- **Honest delivery promise** based on real stock and distance.

### 7.2 Checkout
- Line-by-line total (price, GST, delivery fee, coupon).
- Best coupon applied automatically.
- Choose Cash on Delivery or pay at store.

### 7.3 After buying
- Status updates by email, in-app and push: confirmed, packed, out for delivery, delivered.
- **Delay alert** before the customer notices.
- **One-tap return or cancel** with eligibility shown instantly.
- **Photo-based damage claim**: low-value cases approved automatically, others go to a human.

### 7.4 Human handoff
The AI passes the chat to a human when the customer asks, is upset, the refund is above the limit, the AI is unsure, or the issue repeats. The human sees the full chat, order and timeline, so the customer never repeats themselves. Every case is a **ticket** with owner, priority and deadline.

### 7.5 Channels (free)
In-app chat, email, store walk-in, Jitsi video. Languages: English, Hindi, Hinglish, Marathi.

### 7.6 Targets
| Promise | Target |
|---|---|
| First AI reply | under 5 seconds |
| First human reply (working hours) | under 2 minutes in chat, 24 hours by email |
| Solved in first conversation | 80%+ |
| Refund decision | within 24 hours |
| Satisfaction (CSAT) | 4.5 / 5 |

### 7.7 Engagement
Price-drop and back-in-stock alerts, explainable recommendations, loyalty points, referrals, local deals, one-tap reorder. Limit messages and always allow unsubscribe. Always label the AI as AI.

---

## 8. Build phases

Each phase has a **done-when** check. Do not start the next phase until it passes.

### Phase 0: Fix the foundation (2–3 weeks)
- Remove the login backdoor in `login_view` (any account accepts `password`, `admin123` and similar).
- Move `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS` and CORS to `.env`; lock CORS to the real frontend.
- Replace `AllowAny` with proper permission classes and a role check helper.
- Fix the cut-off AI replies (Gemini output limit) and make tests fast (mock the AI in tests).
- Add Redis for chat memory; add an `AuditLog` for admin actions.
- Add rate limiting, basic request logging and a `/health` endpoint.
- Docker Compose for backend, frontend and Redis; one command to start.
- Remove duplicate files (two `MainLayout`, two `Footer`, old `HomePage`) and the unused mock data.
- **Done when:** all tests pass in under a minute, no login backdoor, one command starts everything.

### Phase 1: Seller onboarding (3–4 weeks)
Build everything in section 6: new models and migration, fixed endpoints, document upload, Tesseract OCR, Aadhaar masking rules, seller profile endpoint, 5-step apply wizard with map picker, admin profile review screen.
- **Done when:** a test seller applies with sample documents, the admin sees the full profile and approves, the store appears on the nearby-store map, and a rejected application shows the reason to the seller. Tests in section 11 pass.

### Phase 2: Real accounts (1–2 weeks)
Email verification and email OTP login, Google sign-in, password reset, profile and saved addresses, session expiry.
- **Done when:** a new user can sign up, verify email, log in, reset a password and log out everywhere.

### Phase 3: Orders without payment gateways (3 weeks)
Cash on Delivery and pay-at-store checkout, order state machine, seller order screen (accept, pack, hand to delivery), delivery status with the store's own rider or customer pickup, return and refund requests with photos, notifications (email, in-app, push), GST invoice as a downloadable PDF.
- **Done when:** a customer places an order, the seller fulfils it, the customer sees live status and can return it, all without any paid service.

### Phase 4: Product trust (2–3 weeks)
Photo reviews and "verified buyer", product Q&A, seller ratings, search improvements (typos, Hinglish), recommendations, wishlist alerts.
- **Done when:** a buyer can review with a photo after delivery and ask a question that the seller answers.

### Phase 5: Customer support (3–4 weeks)
Chat saved in the database, support tickets, human handoff with full history, support agent inbox, SLA timers, Jitsi video call from a product or store, damage claims with photos, satisfaction rating after each chat.
- **Done when:** a chat is handed to a human, who resolves it with full context, and the customer rates it.

### Phase 6: Pilot and growth (ongoing)
PostgreSQL, Meilisearch, loyalty and referrals, admin analytics, 20–50 real stores in 2–3 Mumbai areas, weekly review of the numbers in section 12.
- **Done when:** real orders are delivered and the repeat purchase rate is measured.

---

## 9. Security checklist

- [ ] No hard-coded secrets; `.env` only
- [ ] Every endpoint has an explicit permission rule
- [ ] Passwords hashed; no master passwords
- [ ] Rate limits on login, OTP, chat and uploads
- [ ] Uploads checked for type and size; saved outside the public folder
- [ ] Customers can only read their own orders, tickets and chats (tested)
- [ ] AI prompts cannot reveal keys or other users' data (already tested; keep testing)
- [ ] Admin actions written to `AuditLog`
- [ ] HTTPS and secure cookies when deployed
- [ ] Dependencies checked (`npm audit`, `pip-audit`)

---

## 10. Legal basics (India)

Get these reviewed by a lawyer and an accountant before real launch.
- **Consumer Protection (E-Commerce) Rules, 2020:** show seller details, total price with all charges, return and refund policy; appoint a grievance officer; acknowledge complaints within 48 hours and resolve within one month.
- **Digital Personal Data Protection Act, 2023:** clear consent, privacy policy, let users see and delete their data.
- **Aadhaar:** never store the full number (see section 6.5).
- **GST:** marketplace registration and TCS on sellers.
- **Published pages:** terms of use, privacy policy, seller agreement, return policy, shipping policy.
- Medicines and other regulated goods need licensed sellers.

---

## 11. Testing plan

- Keep all existing tests passing; mock the AI so tests are fast and do not use your key.
- **Seller onboarding:** guest cannot list applications (401); customer sees only their own; customer cannot approve (403); unmasked Aadhaar rejected; only last 4 digits stored; PAN mismatch goes to manual review; complete application reaches pending approval; approve creates Seller and Store and sets the role; reject without a reason is refused; profile shows location, products and masked identity.
- **Orders:** quote, reserve, order, cancel and return flows; stock never goes negative under two simultaneous orders.
- **Support:** handoff keeps history; customer cannot read another customer's ticket.
- **Frontend:** `npm run build` passes; check the main flows by hand on a phone-sized screen.

---

## 12. Numbers to watch

| Metric | Why |
|---|---|
| Repeat purchase rate (30 and 90 days) | Do people come back? The key number |
| Average delivery time | Is "same day" real? |
| Conversion (visit to order) | Is shopping easy? |
| Cart abandonment | Is checkout a problem? |
| CSAT and first-conversation resolution | Is support good? |
| Refund time | Do customers trust us? |
| Seller retention and sales per store | Are shops earning? |
| Cost per order vs money earned | Is the business viable? |

---

## 13. Risks and honest limits

| Risk | What to do |
|---|---|
| Free AI limits run out | Rule-based fallback already works; cache common answers |
| Tesseract misreads a document | Send to manual review; never auto-approve |
| Without online payment, some customers won't order | Accept it for the pilot; add a gateway later when revenue allows |
| Stores don't update stock | Simple stock screen, daily reminder, mark stale stock as "check with store" |
| Delivery is the hard part | Start with pickup and a few close areas |
| Legal and tax rules | Get professional advice before launch |
