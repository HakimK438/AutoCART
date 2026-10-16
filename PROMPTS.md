# AutoCart: Build Prompts

Copy-paste prompts to build AutoCart one phase at a time with Claude Code. Each prompt matches a phase in [COMPLETE_PLAN.md](COMPLETE_PLAN.md).

## How to use

1. Open the project folder in Claude Code.
2. Paste **one** prompt at a time, in order. Do not skip ahead.
3. Let Claude finish, check the result, then move on.
4. After each phase, make a git commit (run `git init` first; this folder is not a git repository yet).

**Order of work: the "Enhance first" track (E1 to E6) comes before Phases 0 to 6.** It improves what already exists. It does not replace it. E1 is a preview page only; nothing else changes until you say you like it.

## Standing rules (paste at the start of every session)

```
You are working on AutoCart (Django + React). Read COMPLETE_PLAN.md and PROJECT_REQUIREMENTS.md first.
Rules:
- ENHANCE, DO NOT REPLACE. Keep every existing page, route, API endpoint, model, agent and test working. Add new files beside the old ones. Do not delete or rewrite existing code unless I approve it for that step.
- Do not change the theme of the existing app until I have approved the preview (step E1).
- Design is INSPIRED BY Apple and Forbes (clean, spacious, large typography, editorial layout). Do not copy their logos, brand names, text, icons or images.
- Images must be free to use (for example Unsplash or Pexels, with credit where required) or generated locally. Never hot-link images from other companies' websites.
- Use only FREE tools. No paid services, no paid APIs.
- Never edit existing migrations. Add new ones.
- The AI agents may only answer from real database data. Never invent products, prices, stock or order status.
- Customers can only see their own data. Enforce permissions on the server.
- Never store a full Aadhaar number. Masked Aadhaar only, last 4 digits only.
- No secrets in code. Use .env.
- Work on one phase only. Show a short plan first, then build, then run the tests and show real output.
- Do not delete files without telling me. Keep existing tests passing.
- If something behaves differently than expected, say so and propose an alternative.
```

---

# Enhance first (E1 to E6)

Goal: make AutoCart look and feel like a real, premium product, and make the website, the database, the AI agents, customer support and seller information all show the **same real data**. Nothing existing is removed.

## E1: Premium front page preview (do this first, change nothing else)

```
Step E1: build ONE premium preview of the front end so I can decide if I like the style. Do not change anything else.

Rules for this step:
- Add a new route /preview with new files only (for example src/preview/PremiumHome.jsx and src/preview/preview.css). Do not edit existing pages, components, routes, context, services or backend code. The current site must keep working exactly as it does now.
- Style: premium and calm, inspired by Apple product pages and Forbes editorial layouts. Large clean headline typography, lots of white space, full-width hero with a premium product image, a horizontal "featured products" scroller, an editorial grid ("Top picks", "New arrivals", "Best sellers") with big image cards and thin serif section headings, a slim sticky header with search, a dark footer. Subtle motion only (Framer Motion fade/slide, no flashy effects). Respect prefers-reduced-motion. Mobile first. Light and dark theme.
- Use REAL data from the existing API (GET /api/products, /api/categories). Show real product names, prices, ratings and images from the database. If a product has no image, show a clean placeholder.
- Use free images only (Unsplash or Pexels, credit in the footer) or the images already in the database.
- Include a small "Ask AutoCart" chat button in the corner that opens the existing AI assistant, unchanged.
- Do not use any logo, name or text from Apple or Forbes.

When done: tell me the URL (http://localhost:5173/preview), show a screenshot if you can, and list exactly which new files you added. Then STOP and wait. Do not apply this theme anywhere else until I say "approved".
```

## E2: Apply the approved theme to the whole front end (only after you say "approved")

```
Step E2: I approved the /preview style. Now roll the same design system out to the whole front end.

- Extract the preview style into shared design tokens (colours, fonts, spacing, radius, shadows) in tailwind.config.js and src/index.css, plus a few shared components (Button, Card, Section heading, Product card, Header, Footer). Keep the old components available until each page is migrated.
- Migrate page by page in this order: Home, Products list, Product details, Search, Cart, Checkout, Orders, Profile, Login/Register, then the seller pages and the admin portal. After each page, run npm run build and confirm the page still works with real API data.
- Premium product pages: large image gallery, clear price, rating, stock and nearby-store availability, specifications table, reviews, "Ask about this product" button.
- Keep accessibility: keyboard navigation, visible focus, AA contrast, alt text, text summaries for charts.
- Do not change backend behaviour in this step.
Done when: every page uses the same look, nothing is broken, and npm run build passes. Show me what changed page by page.
```

## E3: Public "everything we sell" page and real data on the login page

```
Step E3: make the site feel real by showing real data to anyone, even before they log in.

- Add a backend endpoint GET /api/catalog/summary (public, read only, cached for a few minutes) that returns real numbers from the database: total products, total categories, total brands, total partner stores, number of cities, price range, products in stock, and the count per category. No private data.
- Add a public page /catalog ("Everything we sell") that lists EVERY product with all its real fields: image, name, brand, category, price, original price, discount, rating, review count, stock status, seller, specifications and description. Add search, filters (category, brand, price, rating, in stock), sort, pagination and a "view details" link. Use the existing /api/products endpoint; add only what is missing (for example pagination or filters) without breaking existing calls.
- On the login and register pages, add a side panel that shows the live summary from /api/catalog/summary ("98 products, 8 categories, 67 partner stores in Mumbai") and a short scroll of featured products, so visitors see that the store is real before they sign in.
- Add a link to /catalog in the header and footer.
- Add backend tests for /api/catalog/summary (numbers match the database) and for the product filters.
Done when: a logged-out visitor can see the real product count and browse every product's full details. Show the test output and the page.
```

## E4: Align the data between database, website, agents and sellers

```
Step E4: make sure the website, database, AI agents, customer support and seller information all use ONE source of truth.

1. Audit and list every place the front end uses mock data (src/data/mock*.js, products.js, users.js, orders.js, sellers.js, coupons.js). For each one, switch it to the real API where an endpoint exists. Report what you changed and what is left.
2. Make field names consistent between the Django models, serializers and the front end (for example the seller name on a product versus the Seller record). If a field is missing, add it with a NEW migration; never edit existing migrations.
3. Link products to sellers properly: a Product should point to its Seller (add a nullable foreign key in a new migration and backfill from the existing `seller` text field). Product pages and the /catalog page show the seller's real name, city and rating.
4. Make sure the AI agents' tools read exactly the same data the website shows (same filters, same stock, same prices). Add a test that the agent's answer for a product matches the /api/products/<id> response.
5. Make the stock shown on the website, in the agents and in the nearby-store map come from the same records.
6. Write a short docs/DATA_MODEL.md that shows how User, Seller, Store, Product, Order, SellerApplication and the agents connect.
Done when: the same product shows the same name, price, stock and seller on the website, in the admin portal, in the AI chat and on the store map. Show the test output.
```

## E5: Free AI key setup and a better AI layer

```
Step E5: use FREE API keys well, and make AI answers reliable. Do not print or commit any key.

- Read how keys are loaded in backend/api/agents/llm_provider.py. Support these free options: Groq free tier (GROQ_API_KEY) and Google Gemini free tier (GEMINI_API_KEY). Tell me where to get each key and which environment variables to set in .env; update .env.example with placeholders only.
- Fix cut-off replies (reply length limit and the model name) and add a clear "which provider answered" field in responses.
- Automatic fallback order: Groq, then Gemini, then the built-in rule-based engine. Cache repeated questions for a few minutes to save free quota. Show a friendly message if all providers are rate limited.
- Add a /api/ai/status endpoint (admin only) that shows which provider is configured and whether it is working, without revealing the key.
- Make tests use a fake provider so they are fast and never spend my quota.
Done when: with only a free key set, every agent answers completely, and with no key set, the rule-based engine still works. Show the test output.
```

## E6: Premium customer support chatbot

```
Step E6: build a much better customer support chatbot on top of the existing agents (Agent B and the others). Add to it; do not remove the current assistant.

What it must do:
- Greet by name when logged in. Understand English, Hindi, Hinglish and Marathi.
- Answer about products using the real database (price, stock, specs, nearby stores), orders (status, tracking, delivery time), returns and refunds, coupons, seller information and store locations.
- Collect the details it needs in a friendly way, only what is needed and only with the user's consent: order number, issue type, product, photo of damage, preferred contact time. Show the user what will be saved before saving it.
- Save every conversation (ChatSession, ChatMessage) and create a SupportTicket automatically when the issue is not solved in chat, with the collected details, so a human sees the whole story.
- Show results as cards inside the chat: product cards, order timeline, store map pin, return status, ticket status.
- Hand over to a human when the user asks, is upset, the refund is above a limit, or the bot is unsure. The human sees the full chat.
- Suggest next actions as buttons (Track order, Return item, Talk to a human, Find nearby store).
- Customers can only ever see their own orders and tickets. Add tests for this and for prompt-injection attempts.
- Add a support dashboard page in the admin portal: open tickets, chats, common questions and satisfaction ratings.
- Premium look: use the approved theme from E2; chat opens as a clean slide-in panel with smooth, subtle motion.
Done when: a test customer can ask about a product, track an order, start a return with a photo, and get handed to a human with full history. Show the test output and walk through it on the running app.
```

---

# Core phases (Phase 0 to 6)

These follow the "Enhance first" track. Where a phase overlaps with an E step, skip the part that is already done.

## Phase 0: Fix the foundation

```
Phase 0 of COMPLETE_PLAN.md: fix the foundation.

1. In backend/api/views.py, remove the login backdoor (login_view accepts "password", "admin123", etc. for any account, and lets users with no password in). Update seed_db.py so demo users get real hashed passwords that match the README demo accounts.
2. Move SECRET_KEY, DEBUG, ALLOWED_HOSTS and CORS settings in settings.py to .env. Lock CORS to the frontend origin. Update .env.example.
3. Replace AllowAny with explicit permission classes. Create one helper for "require role" and use it on every admin and seller endpoint.
4. Fix the cut-off AI replies: look at llm_provider.py (max_output_tokens, model name gemini-3.8-flash) and make replies complete. Make the test suite use a fake LLM so tests are fast (under 1 minute) and never call a real API.
5. Add an AuditLog model + migration and write to it on admin actions.
6. Add rate limiting (DRF throttling) on login and AI endpoints, request logging, and a /api/health endpoint.
7. Add docker-compose.yml with backend, frontend and Redis. Move chat memory (agents/memory.py) from in-memory dict to Redis, with an in-memory fallback if Redis is down.
8. Remove duplicate files (two MainLayout, two Footer, old HomePage/LoginPage etc.) only after checking nothing imports them. List what you removed.

Done when: all tests pass in under a minute, no login backdoor remains, and one command starts everything. Show the test output.
```

## Phase 1: Seller onboarding

```
Phase 1 of COMPLETE_PLAN.md: seller onboarding (section 6). The detailed design is in
C:\Users\Abdul Hakim\.claude\plans\remove-every-paid-things-snazzy-popcorn.md

Backend:
- Add SellerDocument model and new fields on SellerApplication (addressState, storeName, storeLatitude/Longitude, plannedProducts, identityDetails, aadhaarLast4) in a NEW migration. Add SUSPENDED to the status choices. Set MEDIA_ROOT; keep documents private.
- Fix seller_applications_view and admin_seller_application_action_view: they use fields that do not exist (state, user, contactName, stateName, complianceChecklist, submittedData, fromState/toState/notes). Use the real model fields and the status flow in section 6.4.
- GET applications: admin sees all, user sees own, guest gets 401. Admin action: 403 unless ADMIN/STAFF; reason required for REJECT and REQUEST_INFO.
- New endpoints: upload document (multipart, owner only), stream document file (owner/admin only), seller profile (owner/admin).
- OCR (ocr_service.py): add read_text with Pillow + pytesseract (PDF via pypdfium2), parse_aadhaar and parse_pan. Reject unmasked 12-digit Aadhaar. Store only last 4 digits. If Tesseract is missing, set OCR_UNAVAILABLE and go to manual review, never crash. Extend cross_validate_application (PAN, name, PIN, PAN inside GSTIN).
- On APPROVE: update_or_create Seller (real fields only), create a Store from the location, set user role to SELLER, write audit rows.
- Agent D (run_seller_onboarding_agent) must use real OCR results when an application id is given.

Frontend:
- Add leaflet and react-leaflet@4. Create src/components/map/LocationPinMap.jsx.
- Rebuild SellerApplyPage.jsx as a 5-step wizard (business, tax and location with map pin, products, documents with instant "what we read" display, review). Use Mumbai defaults, not Bengaluru.
- Rebuild the detail panel in admin/SellerOnboardingAI.jsx as a full seller profile (masked identity, map, products, documents, form-vs-document table, risk, history) with Approve, Reject (reason box), Request info and Suspend. Use the backend status names.

Tests: create backend/api/test_seller_onboarding.py covering every case in COMPLETE_PLAN.md section 11, mocking pytesseract. Then run migrate, the full test suite and npm run build.

Done when: a test seller applies, the admin approves, and the store shows up in stores/nearby. Show real output and walk through it on the running servers.
```

## Phase 2: Real accounts

```
Phase 2 of COMPLETE_PLAN.md: real accounts, free only.
- Email verification and email OTP login using Gmail SMTP (settings from .env; use the console email backend in development).
- Google sign-in (free). Password reset by email. Session expiry and "log out everywhere".
- Profile page with saved addresses.
- Tests for each flow. Do not use SMS or any paid service.
Done when: a new user can sign up, verify email, log in, reset a password and log out everywhere. Show the test output.
```

## Phase 3: Orders without payment gateways

```
Phase 3 of COMPLETE_PLAN.md: orders without a payment gateway.
- Checkout with Cash on Delivery and Pay at store only.
- Order state machine (placed, accepted, packed, out for delivery, delivered, cancelled, returned) enforced on the server.
- Seller order screen: accept, pack, hand to delivery. Delivery by the store's own rider or customer pickup.
- Return and refund requests with photo upload, reason and status. Add ReturnRequest and Refund models.
- Notification model plus email, in-app and browser push (Firebase Cloud Messaging free tier) on each status change.
- GST invoice as a downloadable PDF.
- Make sure two simultaneous orders can never take stock below zero (test it).
Done when: a customer places an order, the seller fulfils it, the customer follows live status and returns it, with no paid service. Show the test output.
```

## Phase 4: Product trust

```
Phase 4 of COMPLETE_PLAN.md: product trust.
- Reviews with photos and a "verified buyer" label (only after a delivered order). Product Q&A that sellers can answer.
- Seller ratings. Search with typo tolerance and Hinglish keywords.
- Explainable recommendations ("because you bought ...") and wishlist alerts for price drop and back in stock.
- Tests, including that a customer cannot review a product they did not buy.
Done when: a buyer can review with a photo after delivery and ask a question that the seller answers.
```

## Phase 5: Customer support

```
Phase 5 of COMPLETE_PLAN.md section 7: customer support and engagement.
- Save AI chats in the database (ChatSession, ChatMessage).
- Add SupportTicket, TicketMessage and Escalation with owner, priority and deadline.
- Human handoff: the AI hands over when the customer asks, is upset, the refund is above the limit, the AI is unsure, or the issue repeats. The human sees the full chat, order and timeline.
- Support agent inbox in the admin portal with deadline timers.
- "Ask about this product" chat on every product page, grounded in real specs, reviews and seller Q&A, saying "I don't know" when unsure.
- Jitsi Meet video call from a product or store page.
- Photo damage claims: auto-approve low value, send the rest to a human.
- Satisfaction rating after each chat.
- Tests that a customer can never read another customer's ticket or chat.
Done when: a chat is handed to a human, resolved with full context, and rated by the customer.
```

## Phase 6: Pilot and growth

```
Phase 6 of COMPLETE_PLAN.md: prepare the pilot.
- Move to PostgreSQL (Docker) with a migration plan and backup script.
- Add Meilisearch (open source) for search.
- Loyalty points and referral rewards.
- Admin analytics page for the numbers in section 12.
- A short seller guide and a customer FAQ page.
- Draft the legal pages (terms, privacy, returns, shipping, seller agreement) as plain text for a lawyer to review. Do not present them as final legal advice.
Done when: the app runs on PostgreSQL with all tests passing and the analytics page shows real numbers.
```

---

## Handy one-off prompts

**Review before continuing**
```
Review the changes from the last phase. Check permissions, privacy (no full Aadhaar, no leaking other users' data), missing tests and anything that would break the existing tests. List problems first, then fix them.
```

**Security check**
```
Go through the security checklist in COMPLETE_PLAN.md section 9 and tell me honestly which items pass and which fail, with file and line references. Fix the failures.
```

**Explain it simply**
```
Explain what you just built in plain language for someone who is not a programmer: what it does, how I try it, and what is still missing.
```

**Update the docs**
```
Update PROJECT_REQUIREMENTS.md, README_FREE_STACK.md and COMPLETE_PLAN.md so they match what is actually built now. Mark finished items as done and do not claim anything that is not working.
```

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

### Role agent prompts (use these as system rules)
- Customer assistant: "You are AutoCart's shopping assistant for Mumbai local stores. Use only the product and store data provided. Never invent prices, stock or reviews. Keep answers short, show up to 4 products, offer a human when unsure."
- Seller answer drafter: "Draft a short, polite reply to this customer question using only this product's data. If the data does not answer it, say the seller will confirm."
- Admin briefing: "Summarise today's pending seller applications, tickets, enquiries and low-stock items in 5 plain sentences. Use only the counts given."

### Names
Customer assistant: **Saathi** (greets by first name, uses saved preferences, never invents prices or stock). Seller assistant: **Munim** (answers only from the seller's own facts JSON, under 70 words, ends with one next step).
