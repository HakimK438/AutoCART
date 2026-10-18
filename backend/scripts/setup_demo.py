"""
One command that turns an empty checkout into a working demo shop.

    python scripts/setup_demo.py            # create the database and fill it
    python scripts/setup_demo.py --reset    # delete the database first, then do the same

It runs, in order: migrations, the base catalogue, the curated catalogue (offline, from data/curated_catalog.json), the Mumbai store
network, the 17 sellers with logins, and product placement across stores. Everything is safe to run twice. Needs no internet and no API keys.
"""

import os
import subprocess
import sys
from pathlib import Path

import _bootstrap
from _bootstrap import BACKEND

STEPS = [
    ('Create tables', [str(BACKEND / 'manage.py'), 'migrate', '--noinput']),
    ('Base catalogue, categories, coupons', ['scripts/seed_db.py']),
    ('More catalogue items', ['scripts/seed_more_products.py']),
    ('Curated catalogue (offline)', ['scripts/build_curated_catalog.py', '--offline']),
    ('Stores and stock', ['scripts/seed_stores_and_inventory.py']),
    ('Mumbai store network', ['scripts/seed_mumbai_network.py']),
    ('Demo seller', ['scripts/seed_demo_seller.py']),
    ('Mumbai sellers with logins', ['scripts/seed_mumbai_sellers.py']),
    ('Spread products across stores', ['scripts/seed_product_locations.py']),
]


def main() -> int:
    if '--reset' in sys.argv:
        db = Path(os.environ.get('AUTOCART_DB') or BACKEND / 'db.sqlite3')
        db.unlink(missing_ok=True)
        print(f'Removed {db.name}')
    for i, (title, cmd) in enumerate(STEPS, 1):
        print(f'\n[{i}/{len(STEPS)}] {title}', flush=True)
        script = cmd[0] if cmd[0].endswith('manage.py') else str(BACKEND / cmd[0])
        done = subprocess.run([sys.executable, script, *cmd[1:]], cwd=BACKEND, env={**os.environ, 'PYTHONIOENCODING': 'utf-8'})
        if done.returncode:
            print(f'\nStep {i} failed: {title}')
            return done.returncode
    print('\nDone. Start the API:  python manage.py runserver 127.0.0.1:8000\nThen, in the project root:  npm install && npm run dev')
    return 0


if __name__ == '__main__':
    sys.exit(main())
