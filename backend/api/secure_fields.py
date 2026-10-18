"""
Encryption at rest for the few values that must be stored in full (the Aadhaar number).

The value is encrypted with Fernet (AES-128-CBC + HMAC). The key comes from AADHAAR_ENCRYPTION_KEY in .env (any string);
if that is missing it is derived from Django's SECRET_KEY, so set a dedicated key in production. Losing the key means the
stored numbers cannot be read any more, so back it up with the other secrets.
"""

import base64
import hashlib
import os

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet() -> Fernet:
    secret = os.getenv('AADHAAR_ENCRYPTION_KEY') or settings.SECRET_KEY
    return Fernet(base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest()))


def encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode()).decode() if value else ''


def decrypt(token: str) -> str:
    """The original text, or '' if the token is empty or was made with a different key."""
    try:
        return _fernet().decrypt(token.encode()).decode() if token else ''
    except InvalidToken:
        return ''
