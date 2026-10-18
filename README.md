# AutoCart

A marketplace for **local stores in Mumbai**, with three separate experiences (customer, seller, admin) and AI assistants that answer only from the real database.

- **Customers** find what is in stock in nearby stores, buy for delivery or pickup, track orders on a map, and get help from **Saathi**, the shopping assistant, which can also place an order from the chat.
- **Sellers** create an account, apply with their documents, list products with photos, manage stock by hand or automatically, see sales, earnings and profit, and ask **Munim**, the seller assistant, about their own shop.
- **Admins** review seller applications with every document and check, approve or reject, and see a daily briefing of what needs attention.

Everything runs on free tools. Customers can **pay online** (Razorpay in test mode, or a labelled local demo when no keys are set), pay the seller straight by **UPI** (the seller confirms the money arrived), pay on delivery, or pay at the store.

---

---

## Run it (Windows, macOS or Linux)

You need **Python 3.12+** and **Node 20+**. No database server, no API keys and no internet are needed for the demo.

```bash
# 1. Backend (Django, port 8000)
cd backend
python -m venv .venv
.venv\Scripts\activate                  # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt         # the first chat downloads a ~130 MB embedding model once
python scripts/setup_demo.py            # creates the database and loads the shop (about a minute)
python manage.py runserver 127.0.0.1:8000

# 2. Frontend (React + Vite, port 5173): in a second terminal, from the project root
npm install
npm run dev
```

Open http://localhost:5173. `python scripts/setup_demo.py --reset` starts again from an empty database. Restart the server after pulling backend changes.

**Optional `.env`** (copy `.env.example` to `.env` in the project root; never commit it):

| Variable | What it does |
|---|---|
| `GEMINI_API_KEY` | Free key from Google AI Studio. Without it the assistants still work, using database-only answers. |
| `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Gmail app password. Without them, emails are printed in the server console. |
| `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET` | Razorpay **test** keys (`rzp_test_...`). Without them, Pay online runs a labelled local demo. Live keys are refused. |

### Demo accounts (local testing only)

| Role | Sign in at | Email | Password |
|---|---|---|---|
| Admin | `/admin/login` | admin@auracart.com | admin123 |
| Seller | `/seller/login` | seller@example.com | seller123 |
| Customer | `/login` | create one on `/register` | any (6+ characters) |

Every other seller, store and product, with the seller to sign in as, is in **[docs/TEST_ACCOUNTS.md](docs/TEST_ACCOUNTS.md)** (password `Seller@123`). Fake Aadhaar, PAN and bank images for seller onboarding (7 sellers) are in **[backend/data/sample_documents](backend/data/sample_documents/README.md)**. Change all of these before putting the site anywhere public.

To try **Pay now with UPI**, the seller must first add a UPI ID in the Seller centre ("Get paid by UPI"). The demo seller already has the made-up ID `autocart.demo@upi`.

---

## Automation: what the platform does so nobody repeats it

| Who | What is automatic | Where |
|---|---|---|
| Seller | **Autopilot for orders**: turn it on once and every payable order is confirmed and packed the moment it arrives (online orders wait until the money is confirmed); the customer is notified. It never goes past *Packed*, because sending out and delivering happen in the real world. | Seller centre, Orders |
| Seller | **Pack all N ready**: one click for everything waiting. | Seller centre, Orders |
| Seller | **Auto-restock**: when stock falls to your level after a sale, your usual top-up is added and logged. | Seller centre, Products |
| Seller | **"What autopilot did for you"**: every automatic action, in plain words. | Seller centre, Orders |
| Admin | **Application autopilot**: reads every waiting seller application, approves the ones that match and sit under your risk limit, and sends the "please add X" reminder for incomplete ones. Anything odd is left for a person. | Admin, Seller applications |
| Admin | **Audit trail** of automatic actions (`GET /api/admin/automation`). | API |
| Customer | Order pages and the bell update by themselves; **Saathi** can place an order from the chat. | Customer site |
| Operations | `python manage.py run_autopilot` catches up any order autopilot missed. Run it from cron or Windows Task Scheduler (for example every 5 minutes). | Server |

Autopilot only does things the person already asked for, shows what it did, and can be switched off. Every automatic action is stored in `AutomationEvent`.

---

## Data used by the site

| Data | Where it lives | Source |
|---|---|---|
| Categories, coupons, base products | `backend/data/seed_data.json` | Written for this project |
| Curated catalogue (347 products with brand, price, photo, description) | `backend/data/curated_catalog.json` | DummyJSON, a Myntra product CSV, and the Shopify product-catalogue dataset (Hugging Face). Prices of Shopify items are flagged demo prices. |
| Raw datasets | `backend/data/raw/` | `myntra_products.csv`, `products-10k.zip`. Third-party data, kept only to rebuild the catalogue (`python scripts/build_curated_catalog.py`, needs internet). Check each source's licence before using it commercially. |
| Product photos | `backend/media/product_images/` | Downloaded from the Shopify dataset and served by the backend. Other photos load from their source URLs. |
| 17 Mumbai sellers, 60+ stores, stock per store | created by `backend/scripts/seed_*.py` | Made-up businesses, addresses and phone numbers |
| Sample seller documents | `backend/data/sample_documents/` | Fake, labelled "SAMPLE FOR TESTING ONLY" |
| Location lookups, road routes | OpenStreetMap / OSRM at run time | Free public services |

The database (`backend/db.sqlite3`), uploaded seller documents (`backend/media/private/`) and `.env` are never committed.

---

## Project layout

```
backend/
  api/               Django REST API: views, models, agents, automation.py, tests
  autocart_core/     Django settings and root URLs
  scripts/           setup_demo.py (one-command setup), seed_*.py, build_curated_catalog.py, make_sample_documents.py
  data/              seed_data.json, curated_catalog.json, raw/ datasets, sample_documents/
  media/product_images/   product photos (seller documents under media/private/ stay local)
src/
  storefront/        Customer site (Sunset theme, scoped under .ac)
  pages/seller/      Seller application wizard and Seller centre
  pages/admin/       Admin console
docs/                Planning documents and TEST_ACCOUNTS.md (generated)
```

`docs/COMPLETE_PLAN.md`, `docs/PROJECT_REQUIREMENTS.md` and `docs/README_FREE_STACK.md` are the planning documents. Sections titled "updated" reflect what is built today; older sections describe the original plan.

Regenerate the accounts document after changing data: `python scripts/list_seller_addresses.py --write` (from `backend/`).

---

## How to check the whole order flow (about 3 minutes)

1. **Customer**: sign in (or register at `/register`), set your delivery location and buy any product with Cash on delivery or Pay online.
2. Find the product in [docs/TEST_ACCOUNTS.md](docs/TEST_ACCOUNTS.md) to see which seller to sign in as.
3. **Seller**: open `/seller/login`. The order is under *Orders*. Either press **Confirm & pack**, or turn on **Autopilot** and watch it pack by itself.
4. Move it along: **Out for delivery**, then **Mark delivered**. After each step the customer's order page, the bell and a pop-up update within 15 seconds.
5. **Admin**: `/admin/login`. The order and its status are under *Orders*.
6. As the customer, **Cancel order** works only before it is packed; after delivery you can **Return** it within 7 days.

---

### Tests

```bash
cd backend
python manage.py test        # 221 tests; the AI model is switched off so tests never use the network
npm run build                # frontend production build
```

---

## What is built

**Customer**
- Home, a compact shop (five products per row, price and Add to cart visible without scrolling), filter pills and sorting, product pages with photos, reviews, instant "Quick answers", a comparison table, **Buy now** and a sticky buy bar.
- **Only customer accounts can buy.** A visitor who presses Buy now goes straight to the customer sign-in, and the item is added to their cart after they sign in. Sellers and admins are told buying is for customers (and the server refuses their orders).
- Checkout: the server works out price, coupon, delivery fee and stock. The address can be filled from your **current location** (street, area, city and PIN, looked up with free OpenStreetMap). Incomplete forms say what is missing and jump to the first empty field.
- Payment methods: **Pay online** (Razorpay test mode; first in the list at checkout), **Cash on delivery**, **UPI or card on delivery**, **Pay at the store**, and **Pay now with UPI** (scan a QR that pays the seller directly, then enter the 12-digit UPI reference; the seller confirms). UPI is offered only when the whole cart is from one seller who has added a UPI ID, and checkout says why when it is not available.
- Orders, cancel, return, wishlist, profile, support tickets and a contact form. The order page shows the steps and a **road-route map** from the seller's store to you, with distance and drive time.
- **Saathi** chat, built as a **LangGraph agent** (classify, retrieve, answer, buy):
  - Retrieval (RAG) uses a free local Hugging Face embedding model (BAAI/bge-small-en-v1.5, via fastembed) over products and a small policy FAQ.
  - Gemini (free tier) words the reply using only what was retrieved. If Gemini or the model is unavailable it falls back to templates and keyword search.
  - Every product card has **Buy now**. Say "buy the first one" and a confirm step appears in the chat; a customer with a past address confirms in one tap (cash on delivery), others go to checkout.
  - Understands budgets ("under 2k", "between 500 and 1500"), sorting ("cheapest", "best rated"), typos and some Hinglish, and answers in milliseconds from the database. Ask about a product ("is it any good?", "warranty?", "in stock near me?", "compare the first two") and it answers from that product's own data, ranks by stock near your saved location, and gives **phone numbers to call** (support, the store, the seller) for details it does not have or that need a person (bulk orders, invoices). Order cards show the product photo, store, ETA and Track / Cancel / Return / Call.
  - Greets you by first name, answers "where is my order" with the store, distance and status, and hands over to a person. It remembers only categories, a usual budget and your last few searches, which you can see and delete in the chat.

**Seller**
- **Create a seller account** on the seller sign-in page. This opens a draft application straight away, so the admin can see the sign-up.
- Application wizard in a seller-only frame (no shop header): business details, store location pin, **products with stock and a photo**, documents (masked Aadhaar, PAN, GST, address and bank proof) and review. The list of required documents is shown on every step. **You can submit without all documents**; the application is saved and marked incomplete until they are added.
- Documents are read locally (free OCR). The system shows what it read, compares it with the form and computes a risk score.
- On approval, the products from the application go live with their stock and photo.
- Seller centre: sales charts, earnings after commission, and **profit** once you enter a cost price per product. Add products with photos, edit price, **stock by hand (+1, +10) or with an auto-restock rule** (after a sale, if stock is at or below N, add M), and a stock history showing sales, manual edits and auto-restocks.
- **Orders to pack**: confirm a UPI payment, one click **Confirm & pack**, then a route map to the customer.
- **Get paid by UPI**: the seller's own UPI ID. AutoCart never touches the money.
- **Munim**, the seller assistant, answers from the seller's own data: **sales analysis** (this week against last, chart), **product monitoring** (slow movers, overstock, running low, days of stock left, price against similar products, low ratings, thin margins), and ranked **recommendations** with a link to fix each, plus best sellers, revenue, orders and **profit**. Answers come straight from the database in milliseconds; Gemini is only asked for an open-ended question nothing else can place, and is given the same facts.

**Admin**
- Separate login with a profile menu (Seller applications, Settings, View the store, Sign out). Needs-attention cards and a plain-language daily briefing.
- **Seller applications** with tabs including **Still filling in** (sign-ups that have not submitted). Each application shows a risk badge ("Incomplete" while documents are missing), a "before you approve" checklist, Aadhaar and PAN cards, documents you can open, the store on a map, and a decision bar. **Approve stays locked until Aadhaar, PAN and a store location exist** (enforced on the server too).
- **Sellers**: click a seller for contact details, live numbers worked out from real orders, their products and their application.
- **Payments**: how customers pay, and UPI payments waiting for confirmation.
- Support inbox and enquiries with suggested answers.

**Business model** (`backend/api/commission.py`, public at `/api/commission`): free to join and list, no monthly fee, commission only on a sale (Electronics 5%, Fashion 10%, Home & Kitchen 8%, Beauty 8%, Sports 7%, Books 4%, Grocery 3%, Toys 7%, other 6%). **These are proposed launch rates, not a signed price list and not any company's actual rates.**

**Privacy and safety rules**
- A customer never sees admin or seller screens or data. A seller never sees admin data and sees only their own products and orders.
- Uploaded documents are private files, only visible to the owner and admins. Product photos are checked, resized and served publicly.
- "Paid" for UPI only ever means a seller or admin confirmed the money arrived. The same UPI reference cannot be used on two orders.
- Assistants answer from database rows only. They are told not to invent prices, stock or reviews.

---

## What is not built, and why

| Not built | Reason |
|---|---|
| **Looking up a person's details by typing an Aadhaar number** | This will not be built. Aadhaar data is private. There is no free, legal public service for it, and the Aadhaar Act does not allow a private business to look people up or to store full Aadhaar numbers. Instead, a seller uploads their **own masked Aadhaar**. The system reads the name, date of birth and address, stores **only the last 4 digits**, and rejects an upload that shows all 12 digits. |
| Real online payments with live keys | Online payment runs in Razorpay **test mode** only (no real money; live keys are refused). Going live needs a Razorpay business account. Scanning the UPI QR with a real UPI app was **not tested**. |
| Recognising a returning seller from their documents | Planned. It must only ever show a seller their own record after they sign in. |
| Live GPS tracking of a delivery rider | The map shows the road route and distance from store to customer, not a moving rider. The route comes from the free public OSRM service and can be unavailable (a straight line is drawn then). |
| A rider or courier app | The seller presses Out for delivery and Mark delivered. There is no separate rider login and no live GPS dot. |
| Personalised "picked for you", fraud detection, photo reviews | Planned. |
| LangChain chains and hosted Hugging Face inference | The agent uses LangGraph with langchain-core. The Hugging Face model runs locally; hosted inference needs your own token and is not used. |
| PostgreSQL, Redis, Docker | The app runs on SQLite for now. |
| Legal pages (terms, privacy, refund policy) | Missing. |
| Real Gmail sending | Built, but needs your own app password in `.env`. Not tested with real credentials. |

**Known data quality issue:** some sample products have an unrelated photo (for example a phone shown for a mouse). The shop shows a branded tile instead of a photo it can tell is reused, but a few wrong photos remain. Sellers can replace any photo of their own products.

**AI behaviour to expect:** Gemini is a free service and sometimes answers "503 high demand". When that happens the assistants fall back to database-only answers (still correct, just less conversational) and try Gemini again after a few minutes. Gemini wording was not confirmed during testing for this reason.

---
