# AutoCart

A marketplace for **local stores in Mumbai**, with three separate experiences (customer, seller, admin) and AI assistants that answer only from the real database.

- **Customers** find what is in stock in nearby stores, buy for delivery or pickup, track orders, and get help from **Saathi**, the shopping assistant.
- **Sellers** join with their documents, list products, see sales charts and what they earn after commission, and ask **Munim**, the seller assistant, about their own shop.
- **Admins** review seller applications, handle support tickets and enquiries, and see a daily briefing of what needs attention.

Everything runs on free tools. Payments are Razorpay **test mode** only.

---

## Run it (Windows, macOS or Linux)

You need **Python 3.12+** and **Node 20+**.

### 1. Environment file

Copy `.env.example` to `.env` in the project root. Everything is optional:

| Variable | What it does |
|---|---|
| `GEMINI_API_KEY` | Free key from Google AI Studio. Without it the assistants still work, using database-only answers. |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | **Test** keys only (`rzp_test_...`). Without them, "Razorpay (Test Mode)" runs a clearly labelled demo. Live keys are refused. |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Gmail app password. Without them, emails are printed in the server console. |

Never commit `.env`. It is in `.gitignore`.

### 2. Backend (Django, port 8000)

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python seed_db.py
python seed_more_products.py
python seed_stores_and_inventory.py
python seed_mumbai_network.py
python seed_demo_seller.py
python manage.py runserver 127.0.0.1:8000
```

Restart the server after pulling backend changes (new routes are only loaded at start).

### 3. Frontend (React + Vite, port 5173)

```bash
npm install
npm run dev
```

Open http://localhost:5173.

### Demo accounts (local testing only)

| Role | Sign in at | Email | Password |
|---|---|---|---|
| Admin | `/admin/login` | admin@auracart.com | admin123 |
| Seller | `/seller/login` | seller@example.com | seller123 |
| Customer | `/login` | create one on `/register` | any |

### Tests

```bash
cd backend
python manage.py test        # 119 tests; the AI model is switched off so tests never use the network
npm run build                # frontend production build
```

---

## What is built

**Customer**
- Home, shop with filter pills and sorting, product pages with photos, reviews, instant "Quick answers", comparison table, a **Buy now** button, and a sticky buy bar.
- Deal of the day, "shop by need" collections, and category icons (using real ratings, stock and prices only).
- Cart, checkout (server calculates price, coupon, delivery fee and stock), orders, tracking, return and cancel, wishlist, profile.
- Payment methods: Cash on Delivery, Pay at Store, Razorpay (Test Mode).
- Store map (OpenStreetMap) and live per-store stock.
- Contact form and support tickets.
- **Saathi** chat: greets you by first name, finds products with Add to cart buttons, looks up your orders, hands over to a person. It remembers only categories, a usual budget and your last few searches, and you can see and delete that from the chat.

**Seller**
- Application wizard: details, store location pin on a map, planned products, documents (masked Aadhaar, PAN, GST, address and bank proof), review and submit.
- Documents are read locally (free OCR). The system shows what it read, compares it with the form, and computes a risk score.
- Seller centre: sales charts, earnings after commission, add products, edit price and stock, orders with your items, customer questions with suggested answers, and **Munim**.
- "How selling works" and the fee table, shown before and after joining.

**Admin**
- Separate login. Needs-attention cards and a plain-language daily briefing.
- Seller applications with documents, OCR results, risk summary, and approve / reject / ask for more information / suspend, with an audit trail.
- Support inbox, enquiries (with suggested answers), payment status and a Razorpay connection test.

**Business model** (`backend/api/commission.py`, public at `/api/commission`): free to join and list, no monthly fee, commission only on a sale (Electronics 5%, Fashion 10%, Home & Kitchen 8%, Beauty 8%, Sports 7%, Books 4%, Grocery 3%, Toys 7%, other 6%). Online payments add the payment provider's charge (about 2%) at cost. **These are proposed launch rates, not a signed price list and not any company's actual rates.**

**Privacy and safety rules**
- A customer never sees admin or seller screens or data. A seller never sees admin data and sees only their own products and orders.
- Uploaded documents are private files, only visible to the owner and admins.
- Assistants answer from database rows only. They are told not to invent prices, stock or reviews.

---

## What is not built, and why

| Not built | Reason |
|---|---|
| **Looking up a person's details by typing an Aadhaar number** | This will not be built. Aadhaar data is private. There is no free, legal public service for it, and the Aadhaar Act does not allow a private business to look people up or to store full Aadhaar numbers. Instead, a seller uploads their **own masked Aadhaar**. The system reads the name, date of birth and address, stores **only the last 4 digits**, and rejects an upload that shows all 12 digits. |
| Recognising a returning seller from their documents | Planned. It must only ever show a seller their own record after they sign in. |
| Store name and location entered after verification | Today the wizard asks for store details before documents. |
| Shortest-route order tracking | Planned. Orders have status tracking, not a map route. |
| Seller order-status updates (packed, shipped) | Planned. |
| Personalised "picked for you", fraud detection | Planned. |
| Photo reviews | Planned. |
| PostgreSQL, Redis, Docker | The app runs on SQLite for now. |
| Legal pages (terms, privacy, refund policy) | Missing. |
| Real Razorpay test checkout and real Gmail sending | Built, but need your own keys in `.env`. They were not tested with real keys. |

**Known data quality issue:** some sample products share or have an unrelated photo. The shop shows a branded tile instead of a clearly wrong photo where it can detect this, but a few wrong photos remain.

**AI behaviour to expect:** Gemini is a free service and sometimes answers "503 high demand". When that happens the assistants fall back to database-only answers (still correct, just less conversational), then try Gemini again after a few minutes.

---

## Project layout

```
backend/            Django REST API (api/ holds views, models, agents, tests)
src/storefront/     Customer site (Sunset theme, scoped under .ac)
src/pages/seller/   Seller application wizard and Seller centre
src/pages/admin/    Admin console
PROJECT_REQUIREMENTS.md, README_FREE_STACK.md, PROMPTS.md, COMPLETE_PLAN.md
                    Planning documents. The sections titled "updated" reflect what is built today; older sections describe the original plan.
```
