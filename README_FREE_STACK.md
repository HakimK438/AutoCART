# AutoCart: Free-Stack Build Plan

A structured plan to build AutoCart into a real marketplace **using only free tools**, including real seller onboarding with document upload and admin approval.

> Status: this is a **plan**. The seller onboarding feature below is designed but **not built yet**. See section 5 for what is broken today.

---

## 1. Goal

A real e-commerce marketplace where anyone can shop and real local stores can sell, with:
- AI shopping help and customer support that only answers from real data
- Nearby-store, same-day local delivery
- Safe seller onboarding: sellers register, upload documents, an admin approves or rejects

Rule for now: **no paid services.** Paid options are listed in section 2 only as "later".

---

## 2. Free tools to use now

| Need | Free choice now | Later (paid, not now) |
|---|---|---|
| Login | Email + password, email OTP via Gmail SMTP, Google sign-in | SMS OTP |
| Payments | **Cash on Delivery** and **Pay at store (pickup)** | Online payment gateway |
| Notifications | Email (Gmail SMTP), in-app notifications, browser push (Firebase Cloud Messaging) | WhatsApp, SMS |
| Delivery | The store's own delivery staff, or customer pickup | Courier / hyperlocal delivery APIs |
| AI replies | Gemini and Groq free tiers, plus the built-in rule-based fallback | Paid LLM plan |
| Document reading (OCR) | **Tesseract** (open source, runs on your computer) | Cloud OCR |
| Maps | **Leaflet + OpenStreetMap** tiles | Google Maps |
| Address to location | Nominatim (free, max 1 request per second, needs a User-Agent) | Paid geocoding |
| Video "show me the product" | Jitsi Meet embed | Custom video service |
| Voice help | Browser Web Speech API | Phone IVR |
| Database, cache | SQLite now; PostgreSQL + Redis in Docker later | Managed cloud |
| Hosting | Run locally for now | Paid hosting |

Free tiers have limits. Check each provider's current terms. Legal rules (GST, consumer law, data protection) apply even when the tools are free.

---

## 3. Architecture

```
React app (Vite)  ──►  Django REST API  ──►  SQLite database
 customer / seller        │   │
 / admin screens          │   ├──► AI agents (6)  ──► Gemini / Groq  (fallback: rule-based engine)
                          │   ├──► Tesseract OCR  (seller documents)
                          │   └──► Nominatim      (address → map location)
                          └──► private file storage (seller documents, never public)
```

---

## 4. Seller onboarding and admin approval (the new feature)

### 4.1 What the seller does
1. Logs in and opens **Become a seller**.
2. Fills in all required details:
   - store name, contact person, email, phone, business type
   - GSTIN and PAN
   - store address, PIN code, and a **pin on the map** for the exact store location
   - product categories and a list of **products they sell** (name, category, approximate price)
3. Uploads the required documents:

| Document | Required | Notes |
|---|---|---|
| Aadhaar (masked) | Yes | Must be the masked copy from the myAadhaar portal |
| PAN card | Yes | |
| GST certificate | Yes | |
| Store address proof | Yes | |
| Bank proof (cancelled cheque or passbook) | Yes | |
| Store photo | Yes | |

4. After each upload, the system reads the document and **shows the extracted details** right away (name, date of birth, address, PAN number, masked Aadhaar). If a document doesn't match the form, the seller sees a warning and can fix it.

### 4.2 What the admin sees
For each application, one **seller profile** page with:
- identity details read from Aadhaar and PAN (masked)
- business details and **store location on a map**
- **products they sell**
- every uploaded document (view the file)
- a "form vs document" comparison table showing matches and mismatches
- an automatic risk score and checklist
- the full history of who did what and when

Admin buttons: **Approve**, **Reject** (reason required), **Request more information**, **Suspend**.

### 4.3 Status flow

```
Seller submits ──► DOCUMENT_PROCESSING   (documents are read)
   ├─ documents missing ─────────────► NEEDS_MORE_INFORMATION ──(seller uploads)──► DOCUMENT_PROCESSING
   ├─ unreadable or mismatch ────────► NEEDS_MANUAL_REVIEW
   └─ everything matches ────────────► PENDING_ADMIN_APPROVAL

Admin decides:
   APPROVE       ──► APPROVED   (seller account, store on the nearby-store map, role set to SELLER)
   REJECT        ──► REJECTED   (a reason is required and shown to the seller)
   REQUEST_INFO  ──► NEEDS_MORE_INFORMATION
   SUSPEND       ──► SUSPENDED  (only from APPROVED)
```

**The AI never approves anyone.** It only reads documents and suggests a risk score. A human admin makes the final decision.

### 4.4 Aadhaar rules (important)
Indian law does not allow a private business to store a full Aadhaar number. So AutoCart:
- **accepts only masked Aadhaar** (first 8 digits hidden) and rejects an upload that shows all 12 digits
- stores **only the last 4 digits**
- removes the number from the text it saves
- keeps document files in a private folder, viewable only by the owner and admins

"Complete details" from Aadhaar means name, date of birth, gender, address and `XXXX-XXXX-1234`.

---

## 5. What is wrong in the current seller code

These were found by testing the running project:

| Problem | Effect |
|---|---|
| The seller application code uses field names that don't exist in the database model | Filtering applications returns a server error (500); submitting and admin actions would crash |
| Anyone who isn't logged in can list all seller applications | Privacy leak |
| The admin approve/reject endpoint doesn't check that the user is an admin | Anyone could approve a seller |
| There is no real file upload; the "OCR" reads text built from the form itself | It always "matches", so nothing is actually verified |
| The website and the backend use different status names | Admin screen and database disagree |
| The form defaults to Bengaluru | The project is built around Mumbai |

---

## 6. Build phases

| Phase | What | Done when |
|---|---|---|
| **0. Fix the foundation** | Remove the login backdoor, move secrets to `.env`, fix the cut-off AI replies, fix the seller bugs above | Tests pass and the backdoor is gone |
| **1. Seller onboarding** | Document upload, OCR, seller profile, map, admin approve/reject (section 4) | A test seller can apply, an admin can approve, and the store appears on the nearby-store map |
| **2. Checkout without payments** | Cash on Delivery, pay at store, email notifications | A customer can place and track an order end to end |
| **3. Customer support** | In-app chat, human handoff with support tickets, Jitsi video call with a store | A chat can be passed to a human with full history |
| **4. Pilot** | A few real stores in 2–3 Mumbai areas | Real orders delivered, problems tracked |

---

## 7. Setup (for phase 1)

1. Run the backend and frontend as in [README.md](README.md).
2. Install **Tesseract** (free). On Windows, use the UB-Mannheim installer, then put its path in `.env`:
   ```
   TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe
   ```
3. If Tesseract is missing, uploads still work but are sent to manual admin review.
4. Seller documents are saved in `backend/media/private/` (this folder must be in `.gitignore`).

---

## 8. How we will test phase 1

- A visitor who isn't logged in cannot list applications (gets 401).
- A customer cannot approve a seller (gets 403).
- An unmasked Aadhaar upload is rejected, and only the last 4 digits are ever stored.
- A PAN that doesn't match the form moves the application to manual review.
- A complete, matching application reaches "pending admin approval".
- Approving creates the seller and store and sets the role to SELLER.
- Rejecting without a reason is refused.
- The seller profile shows the location, products and masked identity.

Tests use saved sample text instead of the real OCR, so they run without Tesseract or internet.

---

## AI agents by role: requirements and honest status (updated)

Goal: a customer, seller and admin experience that is useful in real life, using free tools only (Groq/Gemini free tiers with a rule-based fallback, local OCR, OpenStreetMap; no payment gateway: pay on delivery, at the store, or UPI straight to the seller).

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

Known gaps: PostgreSQL/Redis/Docker not used yet (SQLite); some sample products have wrong photos or an absurd price in seed data; real Gmail sending needs your own app password in .env; legal pages missing.
### Assistants and seller business model (updated)

- **Saathi** (customer assistant): greets the signed-in customer by first name, remembers only categories, a usual budget and the last few searches (table `UserMemory`), and the customer can see and delete this from the chat ("What Saathi remembers" and "Forget everything"). Answers use real catalogue and the customer's own orders. Gemini is used when available; a database-grounded engine is the fallback.
- **Munim** (seller assistant): separate bot inside the Seller centre. The database computes the numbers; Gemini only words the answer from those facts; if Gemini is unavailable the plain database answer is shown. It can only see the signed-in seller's own products and orders.
- The old "Advanced assistant" drawer was removed from the chat.
- **Seller dashboard**: revenue-per-day chart, best sellers chart, and an earnings breakdown (item total, commission, what the seller keeps), each with a plain-language headline.
- **Business model** (`backend/api/commission.py`, public at `/api/commission`): free to join, list and no monthly fee; commission only on a sale, by category (Electronics 5%, Fashion 10%, Home & Kitchen 8%, Beauty 8%, Sports 7%, Books 4%, Grocery 3%, Toys 7%, default 6%); online payments add the payment provider charge (about 2%) at cost. These are proposed launch rates modelled on how large Indian marketplaces charge referral fees, not a signed price list or exact copies of any company's rates.

### Free AI stack in use (updated)
LangGraph + langchain-core (agent graph), fastembed with BAAI/bge-small-en-v1.5 from Hugging Face (free, local retrieval), Gemini free tier (wording), OSRM public server and OpenStreetMap (routes and tiles), RapidOCR (documents).
