"""
Writes the "who sells what, where, and how do I log in as them" tables, straight from the database.

    python scripts/list_seller_addresses.py            # print
    python scripts/list_seller_addresses.py --write    # rewrite docs/TEST_ACCOUNTS.md

Three plain tables: every seller (login and password), every store (full address and phone) and every product (which seller to
log in as). Search docs/TEST_ACCOUNTS.md for a product name, copy that seller's email and password into the seller login page, and the
order you just placed is on that seller's dashboard.
"""

from _bootstrap import DOCS
import sys

import django

django.setup()

from api.models import Product, Seller, SellerApplication, Store, StoreInventory, User  # noqa: E402

PASSWORD = 'Seller@123'


def cell(v):
    return str(v if v not in (None, '') else '-').replace('|', '/').replace('\n', ' ')


def table(head, rows):
    return ['| ' + ' | '.join(head) + ' |', '|' + '---|' * len(head)] + ['| ' + ' | '.join(cell(v) for v in r) + ' |' for r in rows]


def sellers():
    """{name or company name: info} for every seller, with the login that really works and whether it opens the seller dashboard."""
    out, listing = {}, []
    for s in Seller.objects.order_by('name', 'id'):
        names = [n for n in (s.name, s.companyName) if n]
        user = User.objects.filter(email__iexact=s.email).first()
        works = bool(user and user.role == 'SELLER')
        if not (user and user.check_password(PASSWORD)):
            continue  # a real sign-up with its own password: never listed in a document that gets published
        pw = PASSWORD
        app = SellerApplication.objects.filter(sellerId=s.id).first() or SellerApplication.objects.filter(companyName__in=names, status='APPROVED').first()
        addr = ', '.join(x for x in (app.address, app.pincode) if x) if app and app.status == 'APPROVED' else ''
        count = Product.objects.filter(seller__in=names).count()
        info = {'name': s.name, 'email': s.email, 'password': pw, 'works': works, 'status': s.status}
        for n in names:
            out[n] = info
        listing.append([s.name, s.email, pw, 'Yes' if works else 'No, still pending approval', addr or '-', count])
    return out, listing


def build():
    by_name, listing = sellers()
    lines = [
        '# Test accounts, sellers, stores and products', '',
        'Generated from the database by `python scripts/list_seller_addresses.py --write`. Development data only: every name, phone number and address is made up.', '',
        '### How to check the whole order flow (about 3 minutes)', '',
        '1. **Customer**: sign in (or register at `/register`), set your delivery location, and buy any product below with Cash on delivery or Pay online. Note the product name and the order number.',
        '2. Search this page (Ctrl+F) for the **product name**. The row tells you which seller to sign in as.',
        '3. **Seller**: open `/seller/login`, paste that seller\'s **email** and **password**. The order is under *Orders*, with the customer\'s name, phone and address, and the product\'s stock has gone down by what you bought.',
        '4. Move the order along, one button at a time: **Confirm & pack**, then **Out for delivery**, then **Mark delivered** (the seller sends it out; there is no separate rider app). After each button, go back to the customer: the order page changes by itself within 15 seconds, the **bell** in the top bar gets a new update and a message pops up. The last one says **"Your product has reached you"**.',
        '5. **Sale recorded**: on the seller dashboard, *Your sales* counts the order the moment it is bought and shows how much is *delivered so far*. For cash on delivery, payment turns to *Paid* when you press Mark delivered.',
        '6. **Admin**: open `/admin/login` with `admin@auracart.com` / `admin123`. The order, its status and the customer\'s details are under *Orders*.',
        '7. As the customer, **Cancel order** works only before it is packed (stock goes back up). After delivery you can **Return** it within 7 days.', '',
        'Sellers marked *No, still pending approval* cannot open the seller dashboard until an admin approves them (their products can still be bought). '
        'The shop also works from other places: set your location to any PIN in the store table to see which stores around it stock a product.', '',
        '### Every seller', '',
        f'Password for every seller below is `{PASSWORD}`. The demo seller `seller@example.com` / `seller123` sells as Appario Retail.', '',
    ]
    lines += table(['Seller', 'Login email', 'Password', 'Can open seller dashboard?', 'Store address', 'Products'], listing)

    stores = []
    for st in Store.objects.order_by('city', 'id'):
        seller = by_name.get(st.seller)
        stocked = StoreInventory.objects.filter(store=st, availableQuantity__gt=0).count()
        stores.append([st.name, st.seller, seller['email'] if seller else '-', f'{st.address}, {st.city}', st.pincode, st.phone, f'{st.latitude:.4f}, {st.longitude:.4f}', stocked])
    lines += ['', f'### Every store ({len(stores)})', '',
              'The store that packs an order is the nearest one to the customer that has the product in stock. Its seller can differ from the product\'s seller, because stores stock products from several sellers.', '']
    lines += table(['Store', 'Run by', 'Run by: login email', 'Full address', 'PIN', 'Phone', 'Map pin', 'Products in stock'], stores)

    prods = []
    for p in Product.objects.order_by('name'):
        s = by_name.get(p.seller)
        prods.append([p.name, f'₹{p.price:,.0f}', p.category, p.seller or '-', s['email'] if s else '(no seller account)', (s['password'] if s else '-') if not s or s['works'] else f"{s['password']} (pending: cannot open dashboard)"])
    lines += ['', f'### Every product ({len(prods)}): which seller to sign in as', '']
    lines += table(['Product', 'Price', 'Category', 'Sold by', 'Seller login email', 'Password'], prods)
    return '\n'.join(lines) + '\n'


def main():
    text = build()
    if '--write' not in sys.argv:
        print(text)
        return
    (DOCS / 'TEST_ACCOUNTS.md').write_text(text, encoding='utf-8')
    print('docs/TEST_ACCOUNTS.md updated.')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
