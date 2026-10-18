"""Imported first by every script in this folder: puts backend/ on the import path and points Django at its settings,
so each script runs the same from any working directory (python backend/scripts/seed_db.py or python scripts/seed_db.py)."""

import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent   # backend/
DATA = BACKEND / 'data'                            # datasets the scripts read
DOCS = BACKEND.parent / 'docs'                     # generated documents (logins, addresses)

sys.path.insert(0, str(BACKEND))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'autocart_core.settings')
