"""
Puts the marketplace's 17 sellers in Mumbai, each in its own locality on the map, with a login and a live product count.

    python seed_mumbai_sellers.py

- Every existing seller is moved to Mumbai (this is a Mumbai local-store marketplace) and keeps its status, so Pending sellers stay Pending.
- If there are fewer than 17, the list is topped up with brands that already have products listed but no seller account yet.
- Approved sellers get a map pin in their own locality (exact store pins that already exist are kept).
- Then seed_seller_accounts runs, so every seller has a login. Safe to run more than once.
"""

import _bootstrap  # noqa: F401  (puts backend/ on the import path)
import os
import re
import sys

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autocart_core.settings')
django.setup()

from api.models import Product, Seller, SellerApplication  # noqa: E402
from api.location_service import haversine_distance_km  # noqa: E402
from api.seller_views import CITY_CENTRES, MUMBAI_AREAS  # noqa: E402

TARGET = 17
# Real PIN codes for the localities in MUMBAI_AREAS, so a seller's address is complete.
AREA_PINS = {'Bandra West': '400050', 'Andheri West': '400053', 'Powai': '400076', 'Borivali West': '400092', 'Lower Parel': '400013',
             'Colaba': '400005', 'Dadar': '400014', 'Juhu': '400049', 'Malad West': '400064', 'Goregaon East': '400063', 'Kurla': '400070',
             'Ghatkopar': '400077', 'Mulund West': '400080', 'Chembur': '400071', 'Worli': '400018', 'Vile Parle': '400057', 'Byculla': '400027'}
MUMBAI_RADIUS_KM = 120  # a store pin farther than this from Mumbai (Bengaluru, Delhi, Pune, Chandigarh...) is not a Mumbai address


def slug(text):
    return re.sub(r'[^a-z0-9]+', '.', text.lower()).strip('.')


def top_up():
    """Add sellers for brands that already have products, until there are TARGET sellers."""
    known = {n for s in Seller.objects.all() for n in (s.name, s.companyName) if n}
    counts = {}
    for name in Product.objects.values_list('seller', flat=True):
        if name and name not in known:
            counts[name] = counts.get(name, 0) + 1
    need = TARGET - Seller.objects.count()
    for name, _n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:max(need, 0)]:
        sid = f"seller-{Seller.objects.count() + 100}"
        Seller.objects.create(id=sid, name=name, companyName=name, email=f'{slug(name)}@sellers.autocart.in', status='Approved',
                              joinedDate='2025-01-01', city='Mumbai', productsCount=0)


def main():
    top_up()
    Seller.objects.exclude(city='Mumbai').update(city='Mumbai')
    SellerApplication.objects.exclude(sellerId='').filter(sellerId__in=Seller.objects.values_list('id', flat=True)).update(city='Mumbai')

    import seed_seller_accounts  # creates logins and approved applications; prints its own list
    seed_seller_accounts.main()

    centre = CITY_CENTRES['Mumbai'][:2]
    for i, seller in enumerate(Seller.objects.order_by('id')):
        area, lat, lng = MUMBAI_AREAS[i % len(MUMBAI_AREAS)]
        for app in SellerApplication.objects.filter(sellerId=seller.id, status='APPROVED'):
            # Keep real Mumbai pins; replace a missing pin, the bare city centre, or a pin outside the Mumbai region.
            far = app.storeLatitude is not None and haversine_distance_km(app.storeLatitude, app.storeLongitude, centre[0], centre[1]) > MUMBAI_RADIUS_KM
            if app.storeLatitude is None or (round(app.storeLatitude, 4), round(app.storeLongitude, 4)) == centre or far:
                app.storeLatitude, app.storeLongitude, app.address = lat, lng, f'{area}, Mumbai'
                app.pincode, app.addressState = AREA_PINS.get(area, app.pincode), 'Maharashtra'
                app.save(update_fields=['storeLatitude', 'storeLongitude', 'address', 'pincode', 'addressState'])
        live = Product.objects.filter(seller__in=[n for n in (seller.name, seller.companyName) if n]).count()
        Seller.objects.filter(id=seller.id).update(productsCount=live)

    for app in SellerApplication.objects.filter(status='APPROVED', pincode=''):  # an address like "Colaba, Mumbai" gets its PIN code
        area = app.address.split(',')[0].strip()
        if area in AREA_PINS:
            SellerApplication.objects.filter(pk=app.pk).update(pincode=AREA_PINS[area], addressState='Maharashtra')

    print(f'\n{Seller.objects.count()} sellers, all in Mumbai:')
    for s in Seller.objects.order_by('id'):
        print(f'  {s.name[:34]:34} {s.status:9} products={Product.objects.filter(seller__in=[n for n in (s.name, s.companyName) if n]).count()}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
