# Test accounts, sellers, stores and products

Generated from the database by `python scripts/list_seller_addresses.py --write`. Development data only: every name, phone number and address is made up.

### How to check the whole order flow (about 3 minutes)

1. **Customer**: sign in (or register at `/register`), set your delivery location, and buy any product below with Cash on delivery or Pay online. Note the product name and the order number.
2. Search this page (Ctrl+F) for the **product name**. The row tells you which seller to sign in as.
3. **Seller**: open `/seller/login`, paste that seller's **email** and **password**. The order is under *Orders*, with the customer's name, phone and address, and the product's stock has gone down by what you bought.
4. Move the order along, one button at a time: **Confirm & pack**, then **Out for delivery**, then **Mark delivered** (the seller sends it out; there is no separate rider app). After each button, go back to the customer: the order page changes by itself within 15 seconds, the **bell** in the top bar gets a new update and a message pops up. The last one says **"Your product has reached you"**.
5. **Sale recorded**: on the seller dashboard, *Your sales* counts the order the moment it is bought and shows how much is *delivered so far*. For cash on delivery, payment turns to *Paid* when you press Mark delivered.
6. **Admin**: open `/admin/login` with `admin@auracart.com` / `admin123`. The order, its status and the customer's details are under *Orders*.
7. As the customer, **Cancel order** works only before it is packed (stock goes back up). After delivery you can **Return** it within 7 days.

Sellers marked *No, still pending approval* cannot open the seller dashboard until an admin approves them (their products can still be bought). The shop also works from other places: set your location to any PIN in the store table to see which stores around it stock a product.

### Every seller

Password for every seller below is `Seller@123`. The demo seller `seller@example.com` / `seller123` sells as Appario Retail.

| Seller | Login email | Password | Can open seller dashboard? | Store address | Products |
|---|---|---|---|---|---|
| Adani Wilmar | adani.wilmar@sellers.autocart.in | Seller@123 | Yes | Lower Parel, Mumbai, 400013 | 1 |
| Aditya Birla Fashion | aditya.birla.fashion@sellers.autocart.in | Seller@123 | Yes | Colaba, Mumbai, 400005 | 1 |
| Apex Global Traders | admin@apexglobaltraders.biz | Seller@123 | No, still pending approval | - | 0 |
| Apex Replica Watches & Luxe | replica.wholesale@protonmail.com | Seller@123 | No, still pending approval | - | 0 |
| Appario Retail | seller.appario@auracart.com | Seller@123 | Yes | Goregaon East, Mumbai, 400063 | 241 |
| Biba Apparels | seller.biba@auracart.com | Seller@123 | Yes | Kurla, Mumbai, 400070 | 1 |
| Boldfit Official | seller.boldfit@auracart.com | Seller@123 | No, still pending approval | - | 2 |
| BookWorm India | seller.books@auracart.com | Seller@123 | Yes | Ghatkopar, Mumbai, 400077 | 2 |
| Direct Import Hub | direct.import.hub@sellers.autocart.in | Seller@123 | No, still pending approval | - | 0 |
| FastTrack Wholesale Mobiles | contact@fasttrackmobiles.in | Seller@123 | No, still pending approval | - | 0 |
| Himalayan Pure Organics | compliance@himalayanpure.in | Seller@123 | No, still pending approval | - | 0 |
| Shadow Dropship Express | temp_agent847@mailcatch.xyz | Seller@123 | No, still pending approval | - | 0 |
| Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 | No, still pending approval | - | 118 |
| Unknown Electronics Depot | unknown.electronics.depot@sellers.autocart.in | Seller@123 | No, still pending approval | - | 0 |
| Urban Roots Herbal Co | support@urbanroots.org | Seller@123 | Yes | Powai, Mumbai, 400076 | 0 |
| boAt Official Store | seller.boat@auracart.com | Seller@123 | Yes | Hill Road, Near Bandra Station, Bandra West, 400050 | 1 |

### Every store (68)

The store that packs an order is the nearest one to the customer that has the product in stock. Its seller can differ from the product's seller, because stores stock products from several sellers.

| Store | Run by | Run by: login email | Full address | PIN | Phone | Map pin | Products in stock |
|---|---|---|---|---|---|---|---|
| AutoCart Flagship Studio — Lokhandwala, Andheri West | Appario Retail | seller.appario@auracart.com | Main Market, Lokhandwala Complex, Andheri West, Andheri | 400053 | +91 22 2630 1001 | 19.1410, 72.8285 | 71 |
| AutoCart Express Depot — Chakala, Andheri East | Swift Logistics & Retailers | contact@swiftretail.in | Chakala Metro Station, Andheri-Kurla Road, Andheri East, Andheri | 400069 | +91 22 2838 2002 | 19.1136, 72.8697 | 40 |
| AutoCart Tech Megamart — Infinity Mall, Andheri West | boAt Official Store | seller.boat@auracart.com | Link Road, Opposite Infinity Mall, Andheri West, Andheri | 400053 | +91 22 6695 3003 | 19.1395, 72.8335 | 26 |
| AutoCart Metro Connect — JB Nagar, Andheri East | Boldfit Official | seller.boldfit@auracart.com | JB Nagar Circle, Marol Pipeline, Andheri East, Andheri | 400059 | +91 22 2822 4004 | 19.1120, 72.8720 | 22 |
| AutoCart Smart Store — MIDC Central Road, Andheri East | Appario Retail | seller.appario@auracart.com | MIDC Central Road, Near Seepz Gate 1, Andheri East, Andheri | 400093 | +91 22 2831 5005 | 19.1205, 72.8755 | 67 |
| AutoCart Hub — Marol Naka, Andheri East | Swift Logistics & Retailers | contact@swiftretail.in | Andheri-Ghatkopar Link Road, Marol Naka, Andheri East, Andheri | 400059 | +91 22 2850 6006 | 19.1105, 72.8845 | 47 |
| AutoCart Tech & Lifestyle Hub — Indiranagar | Appario Retail | seller.appario@auracart.com | 100 Feet Road, HAL 2nd Stage, Indiranagar, Bengaluru | 560038 | +91 80 4123 4567 | 12.9784, 77.6408 | 43 |
| AutoCart Digital Express — Koramangala | Appario Retail | seller.appario@auracart.com | 80 Feet Road, 4th Block, Koramangala, Bengaluru | 560034 | +91 80 4234 5678 | 12.9352, 77.6245 | 43 |
| AutoCart Mega Mart — Whitefield | Swift Logistics & Retailers | contact@swiftretail.in | ITPL Main Road, Whitefield, Bengaluru | 560066 | +91 80 4345 6789 | 12.9698, 77.7500 | 43 |
| AutoCart Hyperstore — Dreams Mall, Bhandup | Appario Retail | seller.appario@auracart.com | Lower Ground, Dreams Mall, LBS Marg, Bhandup West, Bhandup | 400078 | +91 22 2596 1001 | 19.1510, 72.9360 | 80 |
| AutoCart Quick Retail — Station Road, Bhandup | boAt Official Store | seller.boat@auracart.com | Station Road, Near Bhandup West Railway Station, Bhandup West, Bhandup | 400078 | +91 22 2566 2002 | 19.1465, 72.9390 | 40 |
| AutoCart Tech Corner — Usha Nagar, Bhandup | Swift Logistics & Retailers | contact@swiftretail.in | Village Road, Usha Nagar, Bhandup West, Bhandup | 400078 | +91 22 2594 3003 | 19.1420, 72.9330 | 51 |
| AutoCart Commerce Hub — Ceat Compound, Bhandup | Appario Retail | seller.appario@auracart.com | LBS Marg, Near Asian Paints Factory, Bhandup West, Bhandup | 400078 | +91 22 2598 4004 | 19.1540, 72.9340 | 83 |
| AutoCart Express Store — Kanjur Link, Bhandup | Boldfit Official | seller.boldfit@auracart.com | Kanjurmarg West Link, Near LBS Junction, Bhandup, Bhandup | 400078 | +91 22 2577 5005 | 19.1350, 72.9310 | 36 |
| AutoCart Prime Hub — Shimpoli, Borivali West | Appario Retail | seller.appario@auracart.com | Shimpoli Road, Near Kastur Park, Borivali West, Borivali | 400092 | +91 22 2898 1001 | 19.2275, 72.8465 | 74 |
| AutoCart Tech Store — IC Colony, Borivali West | boAt Official Store | seller.boat@auracart.com | Holy Cross Road, IC Colony, Borivali West, Borivali | 400103 | +91 22 2893 2002 | 19.2450, 72.8480 | 36 |
| AutoCart Lifestyle & Digital — SV Road, Borivali West | Swift Logistics & Retailers | contact@swiftretail.in | SV Road, Near Borivali West Station, Borivali West, Borivali | 400092 | +91 22 2890 3003 | 19.2290, 72.8530 | 62 |
| AutoCart Express Depot — Carter Road, Borivali East | Boldfit Official | seller.boldfit@auracart.com | Carter Road No 3, Near Abhinav Nagar, Borivali East, Borivali | 400066 | +91 22 2808 4004 | 19.2285, 72.8630 | 34 |
| AutoCart Smart Point — Chikuwadi, Borivali West | Appario Retail | seller.appario@auracart.com | New Link Road, Near Chikuwadi Junction, Borivali West, Borivali | 400092 | +91 22 2868 5005 | 19.2210, 72.8415 | 78 |
| AutoCart Retail Mart — National Park, Borivali East | Swift Logistics & Retailers | contact@swiftretail.in | Kulupwadi Road, Opposite Sanjay Gandhi National Park, Borivali East, Borivali | 400066 | +91 22 2886 6006 | 19.2355, 72.8640 | 56 |
| AutoCart Digital Lounge — Phadke Road, Dombivli | Appario Retail | seller.appario@auracart.com | Phadke Road, Near Appa Pendse Chowk, Dombivli East, Dombivli | 421201 | +91 251 286 1001 | 19.2165, 73.0872 | 77 |
| AutoCart Lifestyle & Tech — Manpada Road, Dombivli | boAt Official Store | seller.boat@auracart.com | Manpada Road, Near Pendharkar College, Dombivli East, Dombivli | 421201 | +91 251 247 2002 | 19.2220, 73.0965 | 26 |
| AutoCart Smart Bazaar — Tilak Road, Dombivli | Swift Logistics & Retailers | contact@swiftretail.in | Tilak Road, Near Sarveshwar Temple, Dombivli East, Dombivli | 421201 | +91 251 280 3003 | 19.2145, 73.0840 | 54 |
| AutoCart Metro Hub — Gupte Road, Dombivli West | Boldfit Official | seller.boldfit@auracart.com | Gupte Road, Near Dombivli Railway Station West, Dombivli West, Dombivli | 421202 | +91 251 248 4004 | 19.2190, 73.0785 | 27 |
| AutoCart Hyper Outlet — Lodha Palava City | Appario Retail | seller.appario@auracart.com | Xperia Mall, Lodha Palava Phase 1, Kalyan-Shil Road, Dombivli, Dombivli | 421204 | +91 251 672 5005 | 19.1915, 73.0780 | 77 |
| AutoCart Quick Mart — Star Colony, Dombivli East | Swift Logistics & Retailers | contact@swiftretail.in | Star Colony, Near Sagarli, Manpada MIDC Road, Dombivli East, Dombivli | 421201 | +91 251 243 6006 | 19.2280, 73.1040 | 59 |
| AutoCart Premier Flagship — R City Mall, Ghatkopar | Appario Retail | seller.appario@auracart.com | Level 2, R City Mall, LBS Marg, Ghatkopar West, Ghatkopar | 400086 | +91 22 6675 1001 | 19.0990, 72.9165 | 70 |
| AutoCart Consumer Electronics — Vallabh Baug, Ghatkopar | boAt Official Store | seller.boat@auracart.com | Vallabh Baug Lane, Near Odeon Swimming Pool, Ghatkopar East, Ghatkopar | 400077 | +91 22 2501 2002 | 19.0815, 72.9080 | 22 |
| AutoCart Retail Express — MG Road, Ghatkopar East | Swift Logistics & Retailers | contact@swiftretail.in | MG Road, Opposite Ghatkopar Railway Station East, Ghatkopar East, Ghatkopar | 400077 | +91 22 2512 3003 | 19.0840, 72.9110 | 60 |
| AutoCart Smart Depot — Pant Nagar, Ghatkopar | Boldfit Official | seller.boldfit@auracart.com | Pant Nagar 90 Feet Road, Near Police Station, Ghatkopar East, Ghatkopar | 400075 | +91 22 2506 4004 | 19.0780, 72.9150 | 37 |
| AutoCart Tech Point — Amrut Nagar, Ghatkopar West | Appario Retail | seller.appario@auracart.com | Amrut Nagar Circle, LBS Marg, Ghatkopar West, Ghatkopar | 400086 | +91 22 2500 5005 | 19.1020, 72.9100 | 81 |
| AutoCart Metro Mart — Jagdusha Nagar, Ghatkopar | Swift Logistics & Retailers | contact@swiftretail.in | Golibar Road, Near Jagdusha Nagar, Ghatkopar West, Ghatkopar | 400086 | +91 22 2515 6006 | 19.0910, 72.9020 | 56 |
| AutoCart Smart Hub — Hitec City | Appario Retail | seller.appario@auracart.com | Madhapur Main Road, Near Cyber Towers, Hitec City, Hyderabad | 500081 | +91 40 4567 8901 | 17.4474, 78.3762 | 43 |
| AutoCart Electronics Megastore — Khadakpada, Kalyan | Appario Retail | seller.appario@auracart.com | Circle Point, Near Wayle Sports Ground, Khadakpada, Kalyan West, Kalyan | 421301 | +91 251 223 1001 | 19.2551, 73.1378 | 73 |
| AutoCart Station Hub — Kalyan Junction | boAt Official Store | seller.boat@auracart.com | Station Road, Opposite Platform 1 Entry, Kalyan West, Kalyan | 421301 | +91 251 231 2002 | 19.2372, 73.1301 | 26 |
| AutoCart Retail Point — Wayle Nagar, Kalyan | Swift Logistics & Retailers | contact@swiftretail.in | Gandhar Nagar Road, Wayle Nagar, Kalyan West, Kalyan | 421301 | +91 251 245 3003 | 19.2505, 73.1250 | 54 |
| AutoCart Smart Store — Rambaug, Kalyan | Appario Retail | seller.appario@auracart.com | Rambaug Lane 4, Near Shivaji Chowk, Kalyan West, Kalyan | 421301 | +91 251 220 4004 | 19.2390, 73.1350 | 81 |
| AutoCart Express Depot — Kolsewadi, Kalyan East | Swift Logistics & Retailers | contact@swiftretail.in | Pune Link Road, Near Tisgaon Naka, Kolsewadi, Kalyan East, Kalyan | 421306 | +91 251 235 5005 | 19.2295, 73.1410 | 57 |
| AutoCart Consumer Hub — Birla College Road, Kalyan | Biba Apparels | seller.biba@auracart.com | Opposite Birla College Campus, Kalyan West, Kalyan | 421301 | +91 251 228 6006 | 19.2470, 73.1440 | 27 |
| AutoCart Tech Store — MG Road, Mulund West | Appario Retail | seller.appario@auracart.com | MG Road, Near Mulund West Railway Station, Mulund West, Mulund | 400080 | +91 22 2564 1001 | 19.1735, 72.9530 | 84 |
| AutoCart Prime Retail — R Mall, Mulund West | boAt Official Store | seller.boat@auracart.com | 1st Floor, R Mall, LBS Marg, Mulund West, Mulund | 400080 | +91 22 6755 2002 | 19.1820, 72.9510 | 29 |
| AutoCart Express Depot — Sarvodaya Nagar, Mulund | Swift Logistics & Retailers | contact@swiftretail.in | Sarvodaya Nagar, Jain Temple Road, Mulund West, Mulund | 400080 | +91 22 2568 3003 | 19.1670, 72.9550 | 62 |
| AutoCart Smart Hub — Mithagar Road, Mulund East | Boldfit Official | seller.boldfit@auracart.com | Mithagar Road, Near Navghar Police Station, Mulund East, Mulund | 400081 | +91 22 2563 4004 | 19.1685, 72.9660 | 32 |
| AutoCart Gadget Point — Yogi Hills, Mulund West | Appario Retail | seller.appario@auracart.com | BR Road, Near Yogi Hills Complex, Mulund West, Mulund | 400080 | +91 22 2560 5005 | 19.1780, 72.9420 | 90 |
| AutoCart Connect — Nahur Link, Mulund West | Swift Logistics & Retailers | contact@swiftretail.in | Goregaon-Mulund Link Road, Near Nahur Station, Mulund West, Mulund | 400080 | +91 22 2567 6006 | 19.1585, 72.9480 | 55 |
| Priya Nair Fashions | Priya Nair Fashions | - | 45 Linking Road, Bandra West, Mumbai | 400050 | 9029660090 | 19.0617, 72.8360 | 0 |
| AutoCart Flagship Store — Bandra West | boAt Official Store | seller.boat@auracart.com | Hill Road, Near Bandra Station, Bandra West, Mumbai | 400050 | +91 22 2640 1122 | 19.0596, 72.8295 | 106 |
| AutoCart Express — Andheri East | Swift Logistics & Retailers | contact@swiftretail.in | Chakala, Andheri-Kurla Road, Andheri East, Mumbai | 400069 | +91 22 2820 3344 | 19.1136, 72.8697 | 111 |
| AutoCart Premier Megastore — Sector 17, Vashi | Appario Retail | seller.appario@auracart.com | Sector 17 Commercial Complex, Near Vashi Plaza, Vashi, Navi Mumbai, Navi Mumbai | 400703 | +91 22 2789 1001 | 19.0760, 72.9985 | 74 |
| AutoCart Grand Central — Seawoods Mall, Navi Mumbai | boAt Official Store | seller.boat@auracart.com | Level 1, Seawoods Grand Central Mall, Sector 40, Seawoods, Navi Mumbai, Navi Mumbai | 400706 | +91 22 6812 2002 | 19.0205, 73.0185 | 19 |
| AutoCart Tech Lounge — Palm Beach Road, Vashi | Swift Logistics & Retailers | contact@swiftretail.in | Sector 19D, Palm Beach Galleria Road, Vashi, Navi Mumbai, Navi Mumbai | 400705 | +91 22 2788 3003 | 19.0680, 73.0070 | 47 |
| AutoCart Smart Depot — Nerul West, Navi Mumbai | Boldfit Official | seller.boldfit@auracart.com | Sector 15, Near Nerul Railway Station West, Navi Mumbai, Navi Mumbai | 400706 | +91 22 2770 4004 | 19.0335, 73.0160 | 39 |
| AutoCart Express Hub — CBD Belapur, Navi Mumbai | Appario Retail | seller.appario@auracart.com | Sector 11, CBD Belapur Station Complex, Navi Mumbai, Navi Mumbai | 400614 | +91 22 2757 5005 | 19.0190, 73.0395 | 70 |
| AutoCart Retail Mart — Sector 20, Kharghar, Navi Mumbai | Swift Logistics & Retailers | contact@swiftretail.in | Sector 20, Near Central Park & Golf Course, Kharghar, Navi Mumbai, Navi Mumbai | 410210 | +91 22 2774 6006 | 19.0430, 73.0670 | 43 |
| AutoCart Central Prime — Connaught Place | Biba Apparels | seller.biba@auracart.com | Radial Road 4, Inner Circle, Connaught Place, New Delhi | 110001 | +91 11 2341 5566 | 28.6304, 77.2177 | 43 |
| AutoCart Lifestyle Hub — South Extension | Biba Apparels | seller.biba@auracart.com | South Extension Part II, Ring Road, New Delhi | 110049 | +91 11 2625 7788 | 28.5708, 77.2215 | 43 |
| AutoCart Premium Store — Hiranandani Gardens, Powai | Appario Retail | seller.appario@auracart.com | Central Avenue, Near Haiko Supermarket, Hiranandani Gardens, Powai, Powai | 400076 | +91 22 2570 1001 | 19.1195, 72.9085 | 90 |
| AutoCart Tech Galleria — Galleria Mall, Powai | boAt Official Store | seller.boat@auracart.com | Shop 112, Galleria Shopping Mall, Hiranandani, Powai, Powai | 400076 | +91 22 2571 2002 | 19.1210, 72.9105 | 40 |
| AutoCart Campus Hub — IIT Main Gate, Powai | Swift Logistics & Retailers | contact@swiftretail.in | Main Gate Road, Opposite IIT Bombay, Powai, Powai | 400076 | +91 22 2576 3003 | 19.1245, 72.9160 | 65 |
| AutoCart Digital Express — Chandivali, Powai | Boldfit Official | seller.boldfit@auracart.com | Chandivali Farm Road, Near Nahar Amrit Shakti, Powai, Powai | 400072 | +91 22 2857 4004 | 19.1120, 72.8960 | 37 |
| AutoCart QuickStore — Saki Vihar Link, Powai | Appario Retail | seller.appario@auracart.com | Saki Vihar Road, Near L&T Infotech Gate, Powai, Powai | 400072 | +91 22 2859 5005 | 19.1160, 72.8910 | 96 |
| AutoCart Smart Store — Raheja Vihar, Powai | Swift Logistics & Retailers | contact@swiftretail.in | Raheja Vihar Commercial Complex, Chandivali, Powai, Powai | 400072 | +91 22 2847 6006 | 19.1140, 72.9020 | 62 |
| AutoCart Experience Hub — Viviana Mall, Thane | Appario Retail | seller.appario@auracart.com | Ground Floor, Viviana Mall, Eastern Express Highway, Thane West, Thane | 400606 | +91 22 6170 1001 | 19.2085, 72.9716 | 77 |
| AutoCart Gadget Studio — Naupada, Thane | boAt Official Store | seller.boat@auracart.com | Gokhale Road, Near Thane Railway Station, Naupada, Thane West, Thane | 400602 | +91 22 2542 3002 | 19.1895, 72.9723 | 34 |
| AutoCart Retail Express — Hiranandani Estate, Thane | Swift Logistics & Retailers | contact@swiftretail.in | The Walk High Street, Hiranandani Estate, Ghodbunder Road, Thane West, Thane | 400607 | +91 22 4192 4003 | 19.2558, 72.9806 | 55 |
| AutoCart Digital Mart — Majiwada Junction, Thane | Appario Retail | seller.appario@auracart.com | Near Lodha iThink, Majiwada Junction, Thane West, Thane | 400601 | +91 22 2539 5004 | 19.2140, 72.9870 | 78 |
| AutoCart Lifestyle & Tech — Teen Hath Naka, Thane | Boldfit Official | seller.boldfit@auracart.com | LBS Marg, Near Teen Hath Naka Flyover, Thane West, Thane | 400604 | +91 22 2580 6005 | 19.1862, 72.9598 | 26 |
| AutoCart QuickStore — Vartak Nagar, Thane | Swift Logistics & Retailers | contact@swiftretail.in | Pokhran Road No 1, Near Korum Mall, Vartak Nagar, Thane West, Thane | 400606 | +91 22 2545 7006 | 19.2112, 72.9601 | 47 |

### Every product (393): which seller to sign in as

| Product | Price | Category | Sold by | Seller login email | Password |
|---|---|---|---|---|---|
| (Précommande)Tablier pour enfant avec toque Stitch | ₹2,088 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| 2024 KT GINXU DRAGONFLY 2 FOIL BOARD | ₹3,348 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| 250% Density Chocolate Brown Lace Front Wig Human Hair 13x4 Body Wave Lace Front Wigs with Baby Hair Colored H | ₹2,878 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| 2PCS Retainer Case with Mirror and Adjustable Vent Holes, Cute Slim Aligner Case Compatible with Invisalign, N | ₹558 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| 3pcs LM317 DC-DC Converter Buck Step Down Module Linear Regulator Adjustable Voltage Regulator Power Supply Bo | ₹21,798 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| 5Core Megaphone Bullhorn Speaker 30W Mini Bull Horn Battery Power Megafono 800 Feet USB | ₹12,048 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| ACR39U-NF PocketMate II USB-C Smart Card Reader | ₹7,448 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| ASUS Vivobook 15 Intel Core i5 16GB RAM FHD Laptop | ₹54,990 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Acer Aspire 5 Intel Core i5 13th Gen 16GB RAM Laptop | ₹52,990 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Adidas Brand Logo Printed T Shirt | ₹1,494 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Air fryer baking tray, silicone tray, oven baking tray | ₹6,388 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Allen Solly Men Blue  White Sport Fit Printed Casual Shirt | ₹1,799 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Allen Solly Men Pure Cotton Joggers | ₹1,649 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Allen Solly Men Slim Fit Trouser | ₹2,099 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Allen Solly Men's Regular Fit Cotton Shirt | ₹999 | Fashion | Aditya Birla Fashion | aditya.birla.fashion@sellers.autocart.in | Seller@123 |
| Alpha® T 20 Dog Collar, Dog Tracking Collar | ₹2,298 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Amazon Echo Plus | ₹9,509 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| American Football | ₹1,899 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Annibale Colombo Bed | ₹180,709 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Annibale Colombo Sofa | ₹237,779 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Anrichte DKD Home Decor natürlich Weiß Mango-Holz (193 x 40,6 x 91,4 cm) | ₹4,868 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Anti-Fatigue Mat:  720.0000″ Length,  48.0000″ Wide,  1/2″ Thick,  Closed Cell Polyvinylchloride,  Beveled Edg | ₹238 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Apple | ₹189 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Apple AirPods Max Silver | ₹52,309 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Apple Airpods | ₹12,359 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Apple Airpower Wireless Charger | ₹7,609 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Apple HomePod Mini Cosmic Grey | ₹9,509 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Apple MacBook Pro 14 Inch Space Grey | ₹190,219 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Apple MagSafe Battery Pack | ₹9,509 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Apple Watch Series 4 Gold | ₹33,289 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Apple iPhone Charger | ₹1,899 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Arista 4-in-1 Enlarging Easel | ₹19,998 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Asian Wonder-13 Breathable Running Shoes | ₹999 | Fashion | Swift Retail Pvt Ltd | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Asus Zenbook Pro Dual Screen Laptop | ₹171,199 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Atomic Habits by James Clear (Hardcover Edition) | ₹499 | Books & Stationery | BookWorm India | seller.books@auracart.com | Seller@123 |
| Attitude Super Leaves Hand Soap | ₹859 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| BBIA Last Velvet Tint NEW - Soft Creamy Matte Finish Lip Stain, Blur Effect & Velvety Texture, Long-Lasting, H | ₹1,838 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| BIBS - Suzeta Colour Latex, tetina rotunda, 0 luni +-Forest Lake | ₹778 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| BOLLARD IP66 MODIS OPTICS 1000MM LED 20W LED WARM-WHITE 3000K CASAMBI URBAN GREY / Urban grey, Transparent / O | ₹1,258 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| BURST Electric Water Flosser Replacement Tips (Perio/2 Pack) / for Fresh Breath & Healthy Gums / Plaque Remova | ₹1,888 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Baggit Women Brown Solid Zip Around Wallet | ₹451 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Baggit Women Dusty Pink Solid Zip Around Wallet | ₹580 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Baggit Women Yellow Solid Three Fold Wallet | ₹625 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Bamboo Spatula | ₹759 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Baseball Ball | ₹859 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Baseball Glove | ₹2,379 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Basketball | ₹1,429 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Basketball Rim | ₹3,799 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Baumgartens Translucent Plastic Mini Staplers - Mini - Assorted | ₹478 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Beats Flex Wireless Earphones | ₹4,749 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Bedside Table African Cherry | ₹28,529 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Beef Steak | ₹1,239 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Bell Sports Stopper 300 4-Patch Bicycle Tube Repair Kit | ₹3,618 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Bernedoodle Umbrella - Blue | ₹4,978 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Biba Women's Printed Anarkali Kurta Set with Dupatta | ₹2,499 | Fashion | Biba Apparels | seller.biba@auracart.com | Seller@123 |
| Black & Brown Slipper | ₹1,899 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Black Aluminium Cup | ₹569 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Black Sun Glasses | ₹2,849 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Black Whisk | ₹949 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Black Women's Gown | ₹12,359 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Blue & Black Check Shirt | ₹2,849 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Blue Frock | ₹2,849 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Blue Women's Handbag | ₹4,749 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Boldfit Anti Slip Yoga Mat 6mm for Men & Women | ₹699 | Sports & Fitness | Boldfit Official | seller.boldfit@auracart.com | Seller@123 (pending: cannot open dashboard) |
| Boldfit Gym Shaker & Sipper Bottle with Blender Ball 700ml | ₹299 | Sports & Fitness | Boldfit Official | seller.boldfit@auracart.com | Seller@123 (pending: cannot open dashboard) |
| Borosil Trek Stainless Steel Vacuum Insulated Flask 700ml | ₹749 | Home & Kitchen | Borosil Official | (no seller account) | - |
| Boxed Blender | ₹3,799 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Braun Silk-épil 7 Epilator SE7-081 | ₹1,338 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Brown Leather Belt Watch | ₹8,559 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| C4M Pouch Enhancing Thong Pearl Extra Large | ₹1,438 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| CONNEX 900 CHAIN GREY 114L | ₹2,398 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| COSRX AHA 7 Whitehead Power Liquid 100ml | ₹648 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Cable Housing 40" | ₹548 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Calvin Klein CK One | ₹4,749 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Calvin Klein Heel Shoes | ₹7,609 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Calvin Klein Jeans Women Colourblocked Extended Sleeves Compression T Shirt | ₹2,399 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Calvin Klein Jeans Women Turtle Neck Slim Fit T Shirt With Logo Print | ₹2,099 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Calvin Klein Jeans Women Typography Printed T Shirt | ₹1,799 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Campus Oxyfit Lightweight Running Shoes | ₹1,499 | Fashion | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Carbon Steel Wok | ₹2,849 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Cargo Trouser Pants | ₹3,498 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Carving Fork 180mm | ₹6,998 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Cat Food | ₹859 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Celio Men Classic Cotton Formal Shirt | ₹3,299 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Celio Round Neck Pocket Breathable Cotton T Shirt | ₹755 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Celio Round Neck Pocket Breathable Cotton T Shirt | ₹649 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Cello H2O Stainless Steel Water Bottle 1000ml (Set of 2) | ₹599 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Chanel Coco Noir Eau De | ₹12,359 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Charcoal Teeth Whitening | ₹528 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Chariot BOSCH 2751 6 Pièces | ₹2,458 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Chicken Meat | ₹949 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Chopping Board | ₹1,239 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Citrus Squeezer Yellow | ₹859 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Classic Loomis Gag Browband Twisted Wire Snaffle | ₹2,748 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Classic Sun Glasses | ₹2,379 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Classmate Octane Gel Pen (Pack of 10 Blue Pens) | ₹100 | Books & Stationery | ITC Limited | (no seller account) | - |
| Clear / Transparent Packing Tape (Plain Tape 65 Meters 41 Micron) - 1 Pcs | ₹158 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Column capital KK13 | ₹5,058 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Conjunto de Treino Benfica 2025-26 - Casaco sem Capuz | ₹2,218 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Cooking Oil | ₹469 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Corset Leather With Skirt | ₹8,559 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Corset With Black Skirt | ₹7,609 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Cosco Light Aluminium Badminton Racquet Pair | ₹899 | Sports & Fitness | Cosco Sports India | (no seller account) | - |
| Creme Captain Cook Indústrias Oriol 1942 / 500ml | ₹208 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Cricket Ball | ₹1,239 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Cricket Bat | ₹2,849 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Cricket Helmet | ₹4,279 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Cricket Wicket | ₹2,849 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Crinkle Teether Skippy Snail | ₹1,048 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Cucumber | ₹139 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| DCMASBC1N XR FlexVolt Brushcutter Attachment | ₹5,538 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Decoration Swing | ₹5,709 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Dell 02R713 100 / 200GB LTO Ultrium 1 LVD Tape Drive | ₹3,428 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Dell WM126 Wireless Optical Mouse (Black) | ₹1,099 | Electronics | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Dior J'adore | ₹8,559 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Dog Food | ₹1,049 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Dolce Shine Eau de | ₹6,659 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Dress Pea | ₹4,749 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| DryLine Grip Correction Tape, Non-Refillable, Gray/Green Applicator, 0.2" x 335" | ₹108 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Dualtron Spider (Pre-order) | ₹1,108 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| E Flite Wing: Viper 64Mm Edf Jet | ₹2,048 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| E3D Revo Six Coldside 12V (REVO-SIX-12V-COLD) | ₹10,898 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| EXTRACTOR DE AIRE | ₹608 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Egg Slicer | ₹659 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Eggs | ₹279 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Electric Stove | ₹4,749 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Elegant Organza Ladies Day Horse Race Pure colour Fedora Hat/Fascinator | ₹798 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Essence Mascara Lash Princess | ₹949 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Eureka - Transparent Curry Pastels | ₹598 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Eyeshadow Palette with Mirror | ₹1,899 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Family Tree Photo Frame | ₹2,849 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Fastrack Casual Analog Watch for Men | ₹1,395 | Fashion | Titan Company Ltd | (no seller account) | - |
| Fastrack Unisex Blue Dial  Straps Printed Analogue Watch 68012pp02 | ₹855 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Fastrack Women Brass Dial  Wrap Around Straps Analogue Watch  6207qm02 | ₹4,236 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Fastrack Women Tan Brown Two Fold Wallet | ₹659 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Feather Shuttlecock | ₹569 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Fine Mesh Strainer | ₹949 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Fish Steak | ₹1,429 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Football | ₹1,709 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Forever 21 Men Beige Printed T Shirt | ₹559 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Forever 21 Men Green Checked Casual Shirt | ₹519 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Forever 21 Women White Open Toe Flats | ₹1,299 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Fork | ₹379 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Fortune Sunlite Refined Sunflower Oil 5 Litre Jar | ₹685 | Grocery & Gourmet | Adani Wilmar | adani.wilmar@sellers.autocart.in | Seller@123 |
| GREEN VALLEY CREAMERY SOUR CREAM LCF ORG - 12 OZ | ₹748 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| GT-Lite inkl. Vibrationsmotoren | ₹13,418 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Gant Men Multicoloured Tartan Checked Button Down Collar Cotton Casual Shirt | ₹4,199 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Gant Men Pink Solid Linen Casual Shirt | ₹4,499 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Gant Men White  Green Tartan Checked Casual Shirt | ₹3,999 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Gay Lea Butter (Salted) 454g | ₹808 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Gewölbe / Buchen Sicher / Tastensperre / Innenbereich / Mittel / Innenvolumen: 1.6 l / 2 Schlüssel inklusive / | ₹698 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Gigabyte Aorus Men Tshirt | ₹2,379 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Girl Summer Dress | ₹1,899 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Glass | ₹469 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Golden Shoes Woman | ₹4,749 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Golf Ball | ₹949 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Grater Black | ₹1,049 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Gray Dress | ₹3,329 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Green Bell Pepper | ₹119 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Green Chili Pepper | ₹89 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Green Crystal Earring | ₹2,849 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Green Mango Raw 1 to 1.5 lb | ₹98 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Green Oval Earring | ₹2,379 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Green and Black Glasses | ₹3,329 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Grüne Fee Kopfsalat Maikönig | ₹248 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Gucci Bloom Eau de | ₹7,609 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| HALDIRAM S GULABJAMUN 1KG | ₹148 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| HP 240 Bluetooth Wireless Mouse with Ergonomic Grip | ₹1,299 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| HP Pavilion 15 Core i5 13th Gen Laptop | ₹64,990 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Hand Blender | ₹3,329 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Happilo Premium California Almonds 500g Pack | ₹449 | Grocery & Gourmet | Happilo International | (no seller account) | - |
| Heshe Women's Leather Bag | ₹12,359 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Highlander Men Black  White Slim Fit Checked Casual Shirt | ₹479 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Highlander Men Black Slim Fit Horizontal Stripes Opaque Striped Casual Shirt | ₹512 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Highlander Men Lavender Slim Fit Printed Casual Shirt | ₹449 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Hip Baby Wrap Ring Sling Baby Carrier for Infants and Toddlers - Beautiful, 100% Soft Cotton Baby Wraps Carrie | ₹1,278 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Honey Jar | ₹659 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| House Showpiece Plant | ₹3,799 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Hrx By Hrithik Roshan Lifestyle Boys Optic White Bio Wash Brand Carrier Sustainable Shorts | ₹549 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Hrx By Hrithik Roshan Men Regular Fit Typography Lifestyle Joggers | ₹644 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Hrx By Hrithik Roshan Men Running Track Pants | ₹584 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Huawei Matebook X Pro | ₹133,159 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Hudson Baby Mink with Faux Fur Lining Pool and Beach Robe Cover-ups, Peace Love Flowers | ₹1,688 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| IWC Ingenieur Automatic Steel | ₹475,559 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Ice Cream | ₹519 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Ice Cube Tray | ₹569 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| In My Pregnant Era 2 Sides Shirt, Pregnancy Sweatshirt, Gift for New Mom, Pregnant Women Tee, Baby Reveal Gift | ₹3,248 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Indian Terrain Men Brown  Blue Pure Cotton Slim Fit Tartan Checks Casual Shirt | ₹944 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Indian Terrain Men Navy Blue  Pink Pure Cotton Slim Fit Printed Casual Shirt | ₹944 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Indian Terrain Men White Slim Fit Printed Casual Shirt | ₹839 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Iron Golf | ₹4,749 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Jaguar PRO Gear - Flexible Hard Plastic Training Rubber Sai Black | ₹1,038 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Juice | ₹379 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| KERNEL POP NATURAL PROMO PACK 360GM | ₹628 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Karcher - S4 Twin sweeper | ₹4,348 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Kent Grand Plus 9-Litre RO + UV + UF Water Purifier | ₹14,999 | Home & Kitchen | Kent RO Systems | (no seller account) | - |
| Kids Sandbox with Cover, 46' Wooden Sand Box w/Adjustable Canopy, Large Outdoor Cedar Sandpit for Backyard Pla | ₹1,738 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Kit Reparador Karseell ORIGINAL : Mascarilla Capilar con Colágeno + Aceite de Argán | ₹448 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Kitchen Sieve | ₹759 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Kiwi | ₹239 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Kneaded Eraser Glow in the Dark | ₹98 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Knife | ₹1,429 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Knoll Saarinen Executive Conference Chair | ₹47,559 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Kobo Rubber Hex Dumbbell Set 10KG (5KG x 2) | ₹1,899 | Sports & Fitness | Kobo Fitness Essentials | (no seller account) | - |
| Korda Compac Distance Stick Bag Dark Kamo | ₹3,738 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Korean Exfoliating Mitt - Exfoliating Gloves 3 Pack - Exfoliating Body Scrubber, Viscose Fiber Body Scrub Glov | ₹408 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Lantern Slide Case and 12 Framed Glass Slides | ₹18,188 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Large silver racing fascinator | ₹2,418 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Lemon | ₹79 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Lenovo Yoga 920 | ₹104,619 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Levi's 511 Men Slim Fit Stretchable Jeans | ₹1,899 | Fashion | Levi Strauss India | (no seller account) | - |
| Levis Women Black 710 Super Skinny Fit High Rise Light Fade Stretchable Jeans | ₹2,319 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Levis Women Blue 710 Super Skinny Fit Light Fade Mid  Rise Stretchable Jeans | ₹2,159 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Levis Women Pink Solid Slim Fit Pure Cotton Slim Fit T Shirt | ₹719 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Logitech M331 Silent Plus Wireless Mouse | ₹1,195 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Logitech MX Master 3S Wireless Mouse | ₹6,999 | Electronics | Logitech Official Store | (no seller account) | - |
| Longines Master Collection | ₹142,669 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Luna E Terra Olijfolie Grieks extra vierge demeter bio 500 Milliliter | ₹368 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Lunch Box | ₹1,239 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Magic Gel+LED | ₹1,318 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Magnoflex Rückenbandage | ₹1,518 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Mamaearth Vitamin C Face Wash with Turmeric 150ml | ₹349 | Beauty & Personal Care | Honasa Consumer Ltd | (no seller account) | - |
| Man Plaid Shirt | ₹3,329 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Man Short Sleeve Shirt | ₹1,899 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Mandarina (6 un aprox.) | ₹118 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Mango Abstract Printed One Shoulder Top | ₹1,845 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Mango Pure Cotton Extended Sleeve Sustainable T Shirt | ₹445 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Mango Sequinned Shoulder Straps Top | ₹1,390 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Marina | ₹2,988 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Marni Red & Black Suit | ₹17,119 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Matches - Bee Bouquet | ₹4,458 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Maybelline New York Colossal Mascara Black | ₹339 | Beauty & Personal Care | L'Oreal India | (no seller account) | - |
| Melody - Upholstered 2-Drawer Nightstand | ₹338 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| MelodySusie Portable Electric Nail Drill,PC120B Compact Efile Electrical Professional Nail File Kit for Acryli | ₹1,728 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Men Check Shirt | ₹2,659 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Metal Baseball Bat | ₹2,849 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Mi Smart TV 43 Inch 4K Ultra HD Google TV | ₹26,999 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Microwave Oven | ₹8,559 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Milk | ₹329 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Milton Thermosteel Flip Lid Insulated Water Bottle 1000ml | ₹899 | Home & Kitchen | Milton Home Store | (no seller account) | - |
| Milton Thermosteel Flip N Sip 1000ml Flask | ₹899 | Home & Kitchen | Hamilton Housewares | (no seller account) | - |
| Mithai & More Thabdi Penda 250 gms And 500 gms | ₹338 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Mobiltelefon reflektionskamera | ₹12,908 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Monopod | ₹1,899 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Mug Tree Stand | ₹1,519 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Mulberry | ₹469 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Multi-Use Cover - Cody | ₹468 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Nescafe Coffee | ₹759 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| New DELL XPS 13 9300 Laptop | ₹142,669 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Nike Air Jordan 1 Red And Black | ₹14,269 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Nike Baseball Cleats | ₹7,609 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Nivea Soft Light Moisturiser 300ml | ₹299 | Beauty & Personal Care | Beiersdorf India | (no seller account) | - |
| Nivia Storm Football Size 5 | ₹499 | Sports & Fitness | Freewill Sports Pvt Ltd | (no seller account) | - |
| Noise ColorFit Pulse 2 Max Smartwatch | ₹1,299 | Electronics | Noise Tech Labs | (no seller account) | - |
| OFFNOVA Spiral Binding Machine, Spiral Coil Binder with Electric Coil Inserter, Easy to Punch Handle, Adjustab | ₹518 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Olay Ultra Moisture Shea Butter Body Wash | ₹1,239 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| OnePlus Nord CE 4 5G (Dark Chrome, 8GB RAM, 128GB) | ₹24,999 | Electronics | OnePlus Official | (no seller account) | - |
| Only Women Blue Skinny Fit High Rise Jeans | ₹1,199 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Only Women Blue Skinny Fit Light Fade Jeans | ₹1,199 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Only Women Solid Acrylic Scarf | ₹1,999 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Oppo A57 | ₹23,779 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Oppo F19 Pro Plus | ₹38,039 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Oppo K1 | ₹28,529 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| PATIKIL 6 Pcs Desk Call Bell 2.5" Dia with Metal Anti-Rust Construction Blue/White | ₹888 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| PHOFAY Body Shimmer Oil | ₹268 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Pampi Shoes | ₹2,849 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Pan | ₹2,379 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Panama Man | ₹3,358 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Party Glasses | ₹1,899 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Pearl Milling Company Sciroppo per Pancake | ₹348 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Perfect Jump Shot Strap (Off Hand) | ₹698 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| PerioSciences Hydrating Mouthwash Rinse Oral Care Pre Brush - Mint Anti Cavity Dry Mouth Plaque Remover for He | ₹218 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Philips BHD350/10 2100W Hair Dryer | ₹1,999 | Beauty & Personal Care | Philips Personal Care | (no seller account) | - |
| Pigeon by Stovekraft 3 Litre Outer Lid Pressure Cooker | ₹799 | Home & Kitchen | Stovekraft Official | (no seller account) | - |
| Plant Pot | ₹1,429 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Plate | ₹379 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Poke-A-Dot: Dinosaurs A to Z (Board Book with Buttons to Pop) / Dinosaur Pop It Book, Push Pop Book | ₹778 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Polare Luxury RFID Blocking Leather Passport Holder Travel Wallet For Men and Women (Black with AirTag Slot) | ₹3,948 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| PostuEase™ - Justerbart hållningsbälte för ryggen | ₹1,348 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Potatoes | ₹219 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Powder Canister | ₹1,429 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Prada Women Bag | ₹57,069 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Precision Pro Rebounder | ₹1,268 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Prestige Iris 750W Mixer Grinder with 4 Jars | ₹3,299 | Home & Kitchen | TTK Prestige India | (no seller account) | - |
| Prince Lionheart My Twist'r Diaper System | ₹1,508 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Protein Powder | ₹1,899 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Psychology of Money by Morgan Housel | ₹299 | Books & Stationery | BookWorm India | seller.books@auracart.com | Seller@123 |
| Puma Flyer Flex Performance Running Shoes | ₹2,499 | Fashion | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Puma Future Rider Trainers | ₹8,559 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Puma Men Black Stride One8 Comfort Sandals | ₹1,949 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Puma Unisex Smash v2 Leather Sneakers | ₹2,199 | Fashion | Puma Sports India | (no seller account) | - |
| Quality Park - Mailers, Sheets & Envelopes; Type: Poly Mailer ; Style: Self Adhesive ; Width (Inch): 12 ; Leng | ₹728 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| RIM 140-14 EXCEL 32 HOLE, ERBBS431 | ₹2,998 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Ray-Ban Aviator Classic Unisex Sunglasses | ₹6,790 | Fashion | Luxottica Retail | (no seller account) | - |
| Realme C35 | ₹14,269 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Realme X | ₹28,529 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Realme XT | ₹33,289 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Red Lipstick | ₹1,239 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Red Nail Polish | ₹859 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Red Onions | ₹189 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Red Shoes | ₹3,329 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Red Tongs | ₹659 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Regal Cake Rusks Original (8 pieces) 165gm | ₹408 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Rice | ₹569 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Rolex Cellini Date Black Dial | ₹856,009 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Rolex Cellini Moonphase | ₹1,236,449 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Rolex Cellini Moonphase | ₹1,521,789 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Rolex Datejust | ₹1,046,229 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Rolex Datejust Women | ₹1,046,229 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Rolex Submariner Watch | ₹1,331,569 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Rouleau d’emballage en crêpe 50cm x 50lfm 2 plis 100% cellulose | ₹1,598 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| SPIDER BROOMBALL | ₹1,498 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| STAPLER-HEAVY DUTY BOSTITCH 65 PREMIUM | ₹438 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Samsung Galaxy S10 | ₹66,579 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Samsung Galaxy S7 | ₹28,529 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Samsung Galaxy S8 | ₹47,559 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Samsung Galaxy Tab S8 Plus Grey | ₹57,069 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Samsung Galaxy Tab White | ₹33,289 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Scaune de grădină cu perne 2 buc Gri deschis Poly Ratan | ₹658 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Selfie Stick Monopod | ₹1,239 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Sender Polar FlowLink | ₹5,808 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Shaker Gray Double Vanity Sink Base Cabinet | ₹2,238 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Short Frock | ₹2,379 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Silver Pot With Glass Cap | ₹3,799 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Slotted Turner | ₹859 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Soft Drinks | ₹189 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Sony WH-1000XM5 Wireless Headphones | ₹29,990 | Electronics | Electronics Bazaar | (no seller account) | - |
| Sparx Hyper-Mesh Athletic Running Shoes | ₹1,249 | Fashion | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Spice Rack | ₹1,899 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Spoon | ₹469 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Sports Sneakers Off White & Red | ₹11,409 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Sports Sneakers Off White Red | ₹10,459 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Strawberry | ₹379 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Sunglasses | ₹2,189 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| TDM Adapter for MEADE LX200 ACF | ₹17,268 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Table Lamp | ₹4,749 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Taiwan Dessert Mico Mochi Strawberry Flavor 80g | ₹188 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Tape Logic - 4-3/4" Long, Black/White Paper D.O.T. Labels - For Multi-Use | ₹588 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Tartan Dress | ₹3,799 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Tata Sampann Unpolished Toor Dal / Arhar Dal 1kg | ₹165 | Grocery & Gourmet | Tata Consumer Products | (no seller account) | - |
| Tennis Ball | ₹659 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Tennis Racket | ₹4,749 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| The Derma Co 10% Niacinamide Face Serum 30ml | ₹499 | Beauty & Personal Care | Derma Co Store | (no seller account) | - |
| Timex Men Black Dial  Croc Textured Leather Straps Analogue Watch Tw0tg8000 | ₹1,097 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Timex Men Champagne Analogue Watch   Tw0tg6503 | ₹1,372 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Timex Women Silver Toned Brass Dial Analogue Watch Twel11424 | ₹1,596 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Tischaufsteller fürs Mikrofon Newskill NS-AC-KALIOPE LED Schwarz | ₹9,588 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Tissue Paper Box | ₹239 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Tommy Hilfiger Men Beige Solid Joggers  | ₹4,199 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Tommy Hilfiger Men Navy Blue Leather Two Fold Wallet | ₹2,639 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Tommy Hilfiger Women Mustard Yellow  Navy Blue Striped Leather Zip Around Wallet | ₹2,319 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Tray | ₹1,619 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Tropical Earring | ₹1,899 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Trousers 2140150 GYW Grey | ₹3,988 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Ultimate Office Mesh Wall File Organizer, 12 Tier Vertical Mount Hanging File Sorter. Multipurpose Display Rac | ₹848 | Books & Stationery | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Unisex windbreaker | ₹2,588 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Valkoinen lasten sängynrunko laatikoilla Sipe 70x140cm (mänty) | ₹6,848 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Van Heusen Men Multicolour Pack Of 2 Solid Antibacterial Colour Fresh Trunks | ₹553 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Van Heusen Men Pack Of 2 Solid Antibacterial Colour Fresh Trunks 10042 | ₹493 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Van Heusen Men Swift Dry 4 Way Stretch Breathable Air Trunks | ₹535 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Vaseline Men Body and Face Lotion | ₹949 | Beauty & Personal Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Vaso de Entrenamiento | ₹568 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Vero Moda Floral Printed Square Neck Top | ₹909 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Vero Moda Green Floral Printed Empire Top | ₹779 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Vero Moda Pink Tropical Print Tropical Cinched Waist Top | ₹1,799 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Vestax NOS DF-175 Rotary Fader Kit With Knobs For PMC-270A PCV-175 Mixers | ₹12,388 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Vishay LED Displays TDSG1160 | ₹19,498 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Vivo S1 | ₹23,779 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Vivo V9 | ₹28,529 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Vivo X21 | ₹47,559 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Volleyball | ₹1,139 | Sports & Fitness | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Wangderm Frozen Pandan Leaves - 4 oz | ₹368 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Watch Gold for Women | ₹76,089 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Water | ₹89 | Grocery & Gourmet | Appario Retail | seller.appario@auracart.com | Seller@123 |
| White Faux Leather Backpack | ₹3,799 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Wipro Smart LED Bulb 12W 16 Million Colors | ₹599 | Home & Kitchen | Wipro Lighting | (no seller account) | - |
| Women Handbag Black | ₹5,709 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Women's Wrist Watch | ₹12,359 | Fashion | Swift Logistics & Retailers | contact@swiftretail.in | Seller@123 (pending: cannot open dashboard) |
| Wooden Bathroom Sink With Mirror | ₹76,089 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Wooden Rolling Pin | ₹1,139 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Wooden Shoe Stretcher | ₹4,928 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Yellow Peeler | ₹569 | Home & Kitchen | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Young4us 2 Pack 6-inch Crystal Optical Glass Triangular Prism for Photography, Kids, Science, Teaching Light S | ₹638 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| Zebra MC9400/MC9450 Ultra-Rugged Android Mobile Computer 2D Barcode Scanner | ₹23,568 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| [Pre-order] YaHaHa with LED -ShenYin Studio | ₹528 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
| boAt Airdopes 141 ANC TWS Earbuds | ₹1,499 | Electronics | boAt Official Store | seller.boat@auracart.com | Seller@123 |
| iPad Mini 2021 Starlight | ₹47,559 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| iPhone 12 Silicone Case with MagSafe Plum | ₹2,849 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| iPhone 13 Pro | ₹104,619 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| iPhone 5s | ₹19,019 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| iPhone 6 | ₹28,529 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| iPhone X | ₹85,599 | Electronics | Appario Retail | seller.appario@auracart.com | Seller@123 |
| sengegelænder til barneseng 120 x 42 cm polyester gråbrun | ₹1,368 | Toys & Baby Care | Appario Retail | seller.appario@auracart.com | Seller@123 |
