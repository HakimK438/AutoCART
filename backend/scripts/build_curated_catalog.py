"""
Build the curated AutoCart catalog from real sources.

    python scripts/build_curated_catalog.py             rebuild from the live sources (needs internet), save data/curated_catalog.json, load it
    python scripts/build_curated_catalog.py --offline   load the saved data/curated_catalog.json only (no internet; what setup_demo.py runs)

  * DummyJSON  - every consumer category (items DummyJSON lists without a brand, e.g. groceries, are kept as 'Unbranded' rather than given an invented brand): title, brand, description, stock, rating, images, USD price (converted to INR with the live
                 rate from open.er-api.com; the USD price and rate are kept on the product).
  * Myntra CSV ("Myntra products .csv" in the project root) - fashion: brand, INR price, ratings, images and the Myntra link.
                 The name comes from the product's own URL slug. The CSV has no stock figure, so stock starts at 10.
  * Shopify product-catalogue (Hugging Face datasets-server API) - extra products with a brand and a photo of at least 500 px.
                 The dataset has NO prices, so these get a flagged demo price (see specifications "Price note").
                 Its image links expire, so each photo is downloaded and served from this backend.
  * ABO and products-10k were checked and not used (ABO has no prices or target brands; products-10k has no pictures).

Rules: a product is skipped unless it has a name, brand, description and at least one image that really loads at >= 400 px
(Shopify: >= 500 px). Every product is saved under one of the 8 shop categories, so it shows up on the category pages and in the chatbot.
Old seed products whose photos are dead and that nobody ordered are removed.
"""
from _bootstrap import DATA
import csv
import hashlib
import io
import json
import os
import random
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import django
import requests
from PIL import Image

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autocart_core.settings')
django.setup()

from api.models import Category, Order, Product  # noqa: E402
from api.product_images import DIR  # noqa: E402

MYNTRA_CSV = DATA / 'raw' / 'myntra_products.csv'
OUT = DATA / 'curated_catalog.json'
UA = {'User-Agent': 'AutoCart-catalog-builder/1.0'}
MEDIA_BASE = os.getenv('AUTOCART_MEDIA_BASE', 'http://localhost:8000')  # where this backend is reachable from the browser

# DummyJSON category -> shop category (vehicles and motorcycles are not part of the shop)
DJ_MAP = {
    'smartphones': 'Electronics', 'mobile-accessories': 'Electronics', 'laptops': 'Electronics', 'tablets': 'Electronics',
    'beauty': 'Beauty & Personal Care', 'fragrances': 'Beauty & Personal Care', 'skin-care': 'Beauty & Personal Care',
    'groceries': 'Grocery & Gourmet', 'kitchen-accessories': 'Home & Kitchen', 'furniture': 'Home & Kitchen', 'home-decoration': 'Home & Kitchen',
    'sports-accessories': 'Sports & Fitness', 'mens-shirts': 'Fashion', 'mens-shoes': 'Fashion', 'mens-watches': 'Fashion', 'womens-bags': 'Fashion',
    'womens-dresses': 'Fashion', 'womens-jewellery': 'Fashion', 'womens-shoes': 'Fashion', 'womens-watches': 'Fashion', 'tops': 'Fashion', 'sunglasses': 'Fashion',
}
SKIP_DJ = {'TV Studio Camera Pedestal', 'Selfie Lamp with iPhone'}
MYNTRA_BRANDS = ['ADIDAS', 'Puma', 'Levis', 'Tommy Hilfiger', 'Calvin Klein Jeans', 'Van Heusen', 'Allen Solly', 'HRX by Hrithik Roshan', 'Indian Terrain',
                 'Timex', 'Fastrack', 'Baggit', 'GANT', 'Celio', 'MANGO', 'ONLY', 'Vero Moda', 'FOREVER 21', 'Highlander']
PER_BRAND = 3
SHOP_MAP = {
    'Apparel & Accessories': 'Fashion', 'Luggage & Bags': 'Fashion', 'Electronics': 'Electronics', 'Cameras & Optics': 'Electronics',
    'Health & Beauty': 'Beauty & Personal Care', 'Sporting Goods': 'Sports & Fitness', 'Toys & Games': 'Toys & Baby Care', 'Baby & Toddler': 'Toys & Baby Care',
    'Office Supplies': 'Books & Stationery', 'Media': 'Books & Stationery', 'Food, Beverages & Tobacco': 'Grocery & Gourmet',
    'Home & Garden': 'Home & Kitchen', 'Furniture': 'Home & Kitchen',
}
SHOP_PER_CATEGORY = 14          # Shopify products to add per shop category
SHOP_PER_BRAND = 2
DEMO_PRICE = {'Fashion': (499, 3999), 'Electronics': (999, 24999), 'Beauty & Personal Care': (199, 1999), 'Sports & Fitness': (399, 5999),
              'Toys & Baby Care': (299, 2499), 'Books & Stationery': (99, 999), 'Grocery & Gourmet': (99, 899), 'Home & Kitchen': (299, 7999)}
SPAMMY = re.compile(r'shop|store|\.com|india|new 20|official|outlet|wholesale|dropship', re.I)
SELLERS = {'Electronics': 'Appario Retail', 'Fashion': 'Swift Logistics & Retailers'}
DEFAULT_SELLER = 'Appario Retail'


def inr_rate():
    return float(requests.get('https://open.er-api.com/v6/latest/USD', headers=UA, timeout=30).json()['rates']['INR'])


def check_image(url):
    """(url, w, h) when the URL serves a real image of >= 400 px on its short side, else None."""
    try:
        r = requests.get(url, headers=UA, timeout=30)
        if r.status_code != 200 or not r.headers.get('content-type', '').startswith('image/'):
            return None
        w, h = Image.open(io.BytesIO(r.content)).size
        return (url, w, h) if min(w, h) >= 400 else None
    except Exception:
        return None


def money(s):
    m = re.sub(r'[^\d.]', '', s or '')
    return float(m) if m else 0.0


def tidy_price(usd, rate):
    return float(round(usd * rate / 10) * 10 - 1)


def build_dummyjson(rate):
    data = requests.get('https://dummyjson.com/products?limit=0', headers=UA, timeout=60).json()['products']
    out = []
    for p in data:
        if p['category'] not in DJ_MAP or p['title'] in SKIP_DJ or not p.get('images') or not p.get('description'):
            continue
        price = tidy_price(float(p['price']), rate)
        off = float(p.get('discountPercentage') or 0)
        out.append({
            'id': f"dj-{p['id']}", 'name': p['title'], 'brand': p.get('brand') or 'Unbranded', 'category': DJ_MAP[p['category']], 'sub': p['category'].replace('-', ' ').title(),
            'price': price, 'originalPrice': float(round(price / (1 - off / 100) / 10) * 10) if off else price, 'rating': round(float(p['rating']), 1),
            'reviewCount': len(p.get('reviews') or []), 'stock': int(p['stock']), 'description': p['description'], 'images': p['images'][:4],
            'link': f"https://dummyjson.com/products/{p['id']}",
            'specs': {'Warranty': p.get('warrantyInformation', ''), 'Return policy': p.get('returnPolicy', ''), 'Source price (USD)': p['price'], 'USD to INR rate used': round(rate, 2)},
        })
    return out


def build_myntra():
    rows = list(csv.DictReader(open(MYNTRA_CSV, encoding='utf-8', errors='ignore')))
    out, seen = [], {}
    for brand in MYNTRA_BRANDS:
        for r in rows:
            if r['title'].strip().lower() != brand.lower() or seen.get(brand, 0) >= PER_BRAND or r['currency'] != 'INR':
                continue
            price, mrp = money(r['final_price']), money(r['initial_price'])
            try:
                imgs = [u.replace('http://', 'https://') for u in json.loads(r['images'])][:4]
                crumbs = [c['name'] for c in json.loads(r['breadcrumbs'])]
                details = json.loads(r['product_details']) if r['product_details'].startswith('{') else {}
            except ValueError:
                continue
            slug = next((s for s in reversed(r['url'].rstrip('/').split('/')) if re.search('[a-z]', s) and s != 'buy'), '')
            name = ' '.join(w.capitalize() for w in slug.split('-'))
            desc = (details.get('description') or r['product_description'] or '').strip()
            if not (price and imgs and name and desc and len(crumbs) >= 3):
                continue
            seen[brand] = seen.get(brand, 0) + 1
            out.append({
                'id': f"myn-{r['product_id']}", 'name': name, 'brand': 'Adidas' if brand == 'ADIDAS' else brand, 'category': 'Fashion',
                'sub': ' '.join(crumbs[1:3]), 'price': price, 'originalPrice': mrp or price, 'rating': round(float(r['rating'] or 0), 1),
                'reviewCount': int(re.sub(r'\D', '', r['ratings_count'] or '0') or 0), 'stock': 10, 'description': desc, 'images': imgs, 'link': r['url'],
                'specs': {'Material and care': details.get('material_and_care', ''), 'Size and fit': details.get('size_and_fit', '')},
            })
    return out


def shopify_page(off):
    for _ in range(4):
        try:
            r = requests.get('https://datasets-server.huggingface.co/rows', timeout=60, params={
                'dataset': 'Shopify/product-catalogue', 'config': 'default', 'split': 'train', 'offset': off, 'length': 100})
            if r.status_code == 200:
                return [x['row'] for x in r.json()['rows']]
        except Exception:
            pass
    return []


def build_shopify(rate, rows_to_read=6000):
    """Extra products from the Shopify dataset. Photos are downloaded now because the dataset's links expire."""
    with ThreadPoolExecutor(6) as ex:
        rows = [r for page in ex.map(shopify_page, range(0, rows_to_read, 100)) for r in page]
    rnd = random.Random(11)
    per_cat, per_brand, out = {}, {}, []
    DIR.mkdir(parents=True, exist_ok=True)
    for r in rows:
        img = r.get('product_image') if isinstance(r.get('product_image'), dict) else {}
        top = (r.get('ground_truth_category') or '').split(' > ')[0]
        cat, brand = SHOP_MAP.get(top), (r.get('ground_truth_brand') or '').strip()
        title, desc = (r.get('product_title') or '').strip(), (r.get('product_description') or '').strip()
        if not (cat and brand and title and len(desc) > 20 and img.get('src') and min(img.get('width', 0), img.get('height', 0)) >= 500):
            continue
        if SPAMMY.search(brand) or len(brand) > 25 or per_cat.get(cat, 0) >= SHOP_PER_CATEGORY or per_brand.get(brand, 0) >= SHOP_PER_BRAND or r.get('ground_truth_is_secondhand') == 'True':
            continue
        try:
            resp = requests.get(img['src'], headers=UA, timeout=40)
            im = Image.open(io.BytesIO(resp.content)).convert('RGB')
        except Exception:
            continue
        if resp.status_code != 200 or min(im.size) < 500:
            continue
        pid = 'shp-' + hashlib.md5((brand + title).encode()).hexdigest()[:10]
        im.thumbnail((1000, 1000))
        im.save(DIR / f'{pid}.jpg', 'JPEG', quality=86)
        lo, hi = DEMO_PRICE[cat]
        price = float(rnd.randrange(lo, hi, 10) - 1)
        per_cat[cat], per_brand[brand] = per_cat.get(cat, 0) + 1, per_brand.get(brand, 0) + 1
        out.append({
            'id': pid, 'name': title[:110], 'brand': brand, 'category': cat, 'sub': (r['ground_truth_category'].split(' > ')[-1]),
            'price': price, 'originalPrice': float(round(price * 1.25, -1)), 'rating': 0.0, 'reviewCount': 0, 'stock': 10, 'description': desc[:600],
            'images': [f'{MEDIA_BASE}/api/media/product_images/{pid}.jpg'], 'link': 'https://huggingface.co/datasets/Shopify/product-catalogue', 'local': True,
            'specs': {'Price note': 'Demo price. The Shopify dataset has no prices; the seller sets the real one.'},
        })
    return out


def fetch_sources():
    """Download and validate every source, save the result to curated_catalog.json, and return (products, dropped names)."""
    rate = inr_rate()
    print(f'USD->INR {rate}')
    items = build_dummyjson(rate) + build_myntra() + build_shopify(rate)
    urls = sorted({u for it in items if not it.get('local') for u in it['images']})
    with ThreadPoolExecutor(12) as ex:
        ok = {r[0]: r for r in ex.map(check_image, urls) if r}
    print(f'remote images: {len(ok)}/{len(urls)} valid')
    final, dropped = [], []
    for it in items:
        if not it.get('local'):
            it['images'] = [u for u in it['images'] if u in ok]
        (final if it['images'] else dropped).append(it)
    OUT.write_text(json.dumps({'usdToInr': rate, 'products': final, 'dropped': [d['name'] for d in dropped]}, indent=1, ensure_ascii=False), encoding='utf-8')
    return final, dropped


def main():
    offline = '--offline' in sys.argv
    if offline:
        final, dropped = json.loads(OUT.read_text(encoding='utf-8'))['products'], []
    else:
        final, dropped = fetch_sources()

    cat_id = {c.name: c.id for c in Category.objects.all()}
    for it in final:
        spec = {k: v for k, v in {'Brand': it['brand'], 'Type': it['sub'], **it['specs']}.items() if v != ''}
        stock = it['stock']
        Product.objects.update_or_create(id=it['id'], defaults=dict(
            name=it['name'], slug=f"{it['id']}-{re.sub(r'[^a-z0-9]+', '-', it['name'].lower())}"[:250], category=it['category'], categoryId=cat_id[it['category']],
            brand=it['brand'], price=it['price'], originalPrice=it['originalPrice'],
            discount=int((it['originalPrice'] - it['price']) / it['originalPrice'] * 100) if it['originalPrice'] > it['price'] else 0,
            rating=it['rating'], reviewCount=it['reviewCount'], stock=stock, stockStatus='Out of Stock' if stock <= 0 else 'Low Stock' if stock <= 10 else 'In Stock',
            images=it['images'], description=it['description'], specifications=spec, seller=SELLERS.get(it['category'], DEFAULT_SELLER), createdAt='2026-10-17'))

    # Old seed products with dead photos: keep them only if somebody ordered them.
    ordered = {str(i.get('id')) for o in Order.objects.all() for i in (o.items or [])}
    removed = 0
    legacy = Product.objects.exclude(id__startswith=('dj-')).exclude(id__startswith='myn-').exclude(id__startswith='shp-')
    keep = set(json.loads(OUT.read_text(encoding='utf-8')).get('keepLegacy', []))
    for p in legacy:
        if offline:   # no internet: keep the old products that had a working photo when the catalogue was built (listed in keepLegacy)
            dead = p.id not in keep
        else:
            dead = not any(check_image(u) for u in (p.images or []) if isinstance(u, str) and u.startswith('http')) and not any(u.startswith('/') or 'localhost' in u for u in (p.images or []))
        if dead and p.id not in ordered:
            p.delete()
            removed += 1
    if not offline:   # remember which old products survived, so an offline load can reproduce this catalogue
        saved = json.loads(OUT.read_text(encoding='utf-8'))
        saved['keepLegacy'] = sorted(legacy.values_list('id', flat=True))
        OUT.write_text(json.dumps(saved, indent=1, ensure_ascii=False), encoding='utf-8')
    # Every product belongs to one of the 8 shop categories, by name and id.
    for p in Product.objects.all():
        if p.category not in cat_id:
            parent = next((c for c in cat_id if cat_id[c] == p.categoryId), None)
            if parent:
                p.category = parent
                p.save(update_fields=['category'])
        elif p.categoryId != cat_id[p.category]:
            p.categoryId = cat_id[p.category]
            p.save(update_fields=['categoryId'])
    for c in Category.objects.all():
        c.productCount = Product.objects.filter(category=c.name).count()
        c.save()
    print(f'loaded {len(final)} products, dropped {len(dropped)}, removed {removed} old products with dead photos')
    for c in Category.objects.all():
        print(f'  {c.name}: {c.productCount}')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
