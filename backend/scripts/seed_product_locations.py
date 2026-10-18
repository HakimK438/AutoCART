"""
Spreads the catalogue across the Mumbai-region stores so what is "in stock near you" depends on where you are.

    python seed_product_locations.py

Before this, 46 products were stocked in every store and the other 347 in none, so every location saw the same shop
(and a Kalyan shopper was told 61 stores had a product). Now every product is stocked in a few areas only:

- each product gets 2 to 4 areas (5 for best sellers and top-rated items), picked deterministically from its id;
- inside an area it sits in 2 to 4 of the area's stores, preferring stores run by the product's own seller;
- quantities vary (some low, a few out of stock) and each store's price differs by up to +-3%.

Bengaluru, Delhi and Hyderabad stores are left alone. Safe to run more than once: the same input gives the same result.
Run it after seed_mumbai_network.py (which creates the stores).
"""

import _bootstrap  # noqa: F401  (puts backend/ on the import path)
import os
import random
import sys
import zlib
from collections import defaultdict

import django

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autocart_core.settings')
django.setup()

from api.models import Product, Store, StoreInventory  # noqa: E402

OUTSIDE_MUMBAI = {'Bengaluru', 'New Delhi', 'Hyderabad'}


def mumbai_zones():
    """{area name: [stores]} for every store with a map pin in the Mumbai region (Bandra and Andheri East count as the area 'Mumbai')."""
    zones = defaultdict(list)
    for s in Store.objects.exclude(latitude=0).exclude(city__in=OUTSIDE_MUMBAI).order_by('id'):
        if s.id.startswith('store-app-'):  # a seller's own sign-up pin, not a partner outlet
            continue
        zones[s.city].append(s)
    return dict(zones)


def pick_stores(rng, stores, seller):
    """2 to 4 stores of one area, the product's own seller's stores first."""
    n = min(len(stores), rng.randint(2, 4))
    own = [s for s in stores if s.seller == seller]
    rest = [s for s in stores if s.seller != seller]
    rng.shuffle(own)
    rng.shuffle(rest)
    return (own + rest)[:n]


def quantity(rng):
    roll = rng.random()
    if roll < 0.08:
        return 0
    if roll < 0.28:
        return rng.randint(1, 3)
    return rng.randint(6, 24)


def main():
    zones = mumbai_zones()
    names = sorted(zones)
    store_ids = [s.id for stores in zones.values() for s in stores]
    keep, rows = set(), []
    for p in Product.objects.order_by('id'):
        rng = random.Random(zlib.crc32(p.id.encode()))
        k = 2 + rng.randint(0, 2) + (1 if (p.bestSeller or (p.rating or 0) >= 4.5) else 0)
        for area in rng.sample(names, min(k, len(names))):
            for s in pick_stores(rng, zones[area], p.seller):
                qty = quantity(rng)
                price = round(float(p.price) * (1 + rng.randint(-3, 3) / 100), 2)
                inv_id = f'inv-{s.id}-{p.id}'
                keep.add(inv_id)
                rows.append((inv_id, s, p, qty, price))

    removed = StoreInventory.objects.filter(store_id__in=store_ids).exclude(id__in=keep).delete()[0]
    for inv_id, s, p, qty, price in rows:
        StoreInventory.objects.update_or_create(id=inv_id, defaults={
            'store': s, 'product': p, 'availableQuantity': qty, 'reservedQuantity': 0, 'storePrice': price, 'isAvailable': qty > 0})

    products = Product.objects.count()
    print(f'{len(rows)} stock rows for {products} products in {len(store_ids)} stores across {len(names)} areas ({removed} old rows removed).')
    per_area = defaultdict(set)
    for _id, s, p, qty, _price in rows:
        if qty > 0:
            per_area[s.city].add(p.id)
    for area in names:
        print(f'  {area:12} {len(zones[area])} stores, {len(per_area[area]):3} of {products} products in stock')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
