"""Encryption for sensitive student fields (currently only Aadhaar).

Two derived keys from one secret:
- a Fernet key to encrypt the value so the admin can see it masked, and
- an HMAC key to compute a deterministic fingerprint used for the uniqueness
  check (Fernet output is randomized, so it can't be compared directly).
"""

import base64
import hashlib
import hmac
import logging
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _keys() -> tuple[Fernet, bytes]:
    if settings.field_encryption_key:
        fernet_key = settings.field_encryption_key.encode()
    else:
        logger.warning(
            "FIELD_ENCRYPTION_KEY is not set; deriving it from JWT_SECRET_KEY. "
            "Set a dedicated key in production."
        )
        fernet_key = base64.urlsafe_b64encode(
            hashlib.sha256(b"field-encryption:" + settings.jwt_secret_key.encode()).digest()
        )
    hmac_key = hashlib.sha256(b"field-fingerprint:" + fernet_key).digest()
    return Fernet(fernet_key), hmac_key


def encrypt(value: str) -> str:
    return _keys()[0].encrypt(value.encode()).decode()


def decrypt(token: str) -> str | None:
    try:
        return _keys()[0].decrypt(token.encode()).decode()
    except InvalidToken:
        return None


def fingerprint(value: str) -> str:
    return hmac.new(_keys()[1], value.encode(), hashlib.sha256).hexdigest()
