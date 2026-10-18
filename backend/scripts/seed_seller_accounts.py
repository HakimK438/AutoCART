"""
Gives every seller in the marketplace a real login, a store pin on the map and (for approved sellers) an approved application,
so each one can sign in at /seller/login and the admin can see them all on the sellers map.

    python seed_seller_accounts.py

Every account gets the same development password (SELLER_PASSWORD below). Sellers that are still Pending get a customer-role
account, exactly like a real applicant: they can sign in at /seller/login and carry on with their application, but cannot
sell until an admin approves them. Nothing is invented about products: each seller keeps the products already linked to them.
The map pin is the centre of the seller's city unless the seller already has a store with exact coordinates.
Safe to run more than once. The list of logins is generated into docs/TEST_ACCOUNTS.md by list_seller_addresses.py.
"""

import _bootstrap  # noqa: F401  (puts backend/ on the import path)
import os
import re
import sys
from pathlib import Path

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autocart_core.settings')
django.setup()

from api.models import Product, Seller, SellerApplication, Store, User  # noqa: E402
from api.seller_views import CITY_CENTRES  # noqa: E402

SELLER_PASSWORD = 'Seller@123'
CITY = CITY_CENTRES


def slug(text):
    return re.sub(r'[^a-z0-9]+', '.', text.lower()).strip('.')


def main():
    rows = []
    for seller in Seller.objects.all().order_by('id'):
        name = (seller.name or '').strip()
        if not name:
            continue
        email = (seller.email or '').strip().lower() or f'{slug(name)}@sellers.autocart.in'
        approved = seller.status == 'Approved'
        user = User.objects.filter(email__iexact=email).first()
        created = user is None
        if created:
            user = User(id=f'user-{seller.id}', email=email, name=name, phone=(seller.phone or '')[-10:], role='SELLER' if approved else 'CUSTOMER', status='Active')
            user.set_password(SELLER_PASSWORD)
            user.save()
        if not seller.email:
            seller.email = email
            seller.save(update_fields=['email'])

        pin = None
        if approved:
            store = Store.objects.filter(sellerId=seller.id).exclude(latitude=0).first()
            lat, lng, state = (store.latitude, store.longitude, store.state) if store else (None, None, '')
            if lat is None and seller.city in CITY:
                lat, lng, state = CITY[seller.city]
            pin = (lat, lng)
            app = SellerApplication.objects.filter(ownerUserId=user.id, status='APPROVED').first()
            if not app:
                SellerApplication.objects.update_or_create(id=f'app-{seller.id}', defaults=dict(
                    ownerUserId=user.id, sellerId=seller.id, applicantName=name, companyName=name, storeName=name, email=email, phone=seller.phone or '',
                    city=seller.city or '', address=(store.address if store else f'{seller.city} (city centre, exact address not given)'), pincode=(store.pincode if store else ''),
                    addressState=state, storeLatitude=lat, storeLongitude=lng, status='APPROVED', riskScore=10, riskCategory='Low', reviewedBy='seed',
                    plannedProducts=[]))
        rows.append((seller.id, name, seller.companyName, seller.city, seller.status, email, Product.objects.filter(seller__in=[name, seller.companyName]).count(), pin, created))

    # Sellers that came from real sign-ups already have their own login: list them too.
    for app in SellerApplication.objects.filter(status='APPROVED', ownerUserId__gt='').exclude(sellerId__startswith='seller-'):
        u = User.objects.filter(id=app.ownerUserId).first()
        if u and not any(r[5] == u.email.lower() for r in rows):
            rows.append((app.sellerId or app.id, app.companyName, app.companyName, app.city, 'Approved', u.email, Product.objects.filter(seller=app.companyName).count(), (app.storeLatitude, app.storeLongitude), False))

    print(f'{len(rows)} seller logins ready (password for new accounts: {SELLER_PASSWORD})')
    for sid, name, company, city, status, email, n, pin, created in rows:
        print(f'  {"NEW" if created else "   "} {name[:34]:34} {status:9} {email[:40]:40} products={n} map={"yes" if pin and pin[0] else "no"}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
