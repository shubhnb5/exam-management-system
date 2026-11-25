"""Verifies Firebase Phone Authentication ID tokens.

With OTP_PROVIDER=firebase the student's browser asks Google Firebase to send
the OTP SMS and checks the code with Firebase. Firebase then gives the browser
an ID token: a JWT signed by Google that contains the verified phone number.
This module checks that token exactly as Google documents for third-party
backends:
  - RS256 signature against Google's published certificates (by key id),
  - audience = our Firebase project id, issuer = securetoken.google.com/<id>,
  - not expired, issued/auth_time not in the future,
  - signed in with the "phone" provider, recently (so an old token can't be
    replayed), and the phone number is an Indian +91 mobile.
"""

import json
import logging
import re
import threading
import time
import urllib.request

from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger("uvicorn.error")

MAX_AUTH_AGE_SECONDS = 15 * 60  # the OTP must have been verified within the last 15 minutes
CLOCK_SKEW_SECONDS = 60

_lock = threading.Lock()
_cache: dict = {"certs": {}, "expires_at": 0.0}


class FirebaseTokenError(Exception):
    pass


def _fetch_certs() -> dict[str, str]:
    with urllib.request.urlopen(settings.firebase_certs_url, timeout=10) as response:
        certs = json.loads(response.read())
        cache_control = response.headers.get("Cache-Control", "")
    match = re.search(r"max-age=(\d+)", cache_control)
    _cache["certs"] = certs
    _cache["expires_at"] = time.time() + (int(match.group(1)) if match else 3600)
    return certs


def _cert_for(kid: str) -> str:
    with _lock:
        certs = _cache["certs"]
        if time.time() >= _cache["expires_at"] or kid not in certs:
            try:
                certs = _fetch_certs()
            except Exception as exc:  # noqa: BLE001
                logger.error("Could not download Firebase public keys: %s", exc)
                raise FirebaseTokenError("Could not verify the OTP right now. Please try again.")
        if kid not in certs:
            raise FirebaseTokenError("Invalid verification. Please request a new OTP.")
        return certs[kid]


def verify_phone_id_token(id_token: str) -> str:
    """Returns the verified 10-digit Indian mobile number, or raises."""
    project = settings.firebase_project_id
    if not project:
        raise FirebaseTokenError("Firebase is not configured on the server.")
    try:
        header = jwt.get_unverified_header(id_token)
    except JWTError:
        raise FirebaseTokenError("Invalid verification. Please request a new OTP.")
    if header.get("alg") != "RS256" or not header.get("kid"):
        raise FirebaseTokenError("Invalid verification. Please request a new OTP.")

    cert = _cert_for(header["kid"])
    try:
        claims = jwt.decode(
            id_token,
            cert,
            algorithms=["RS256"],
            audience=project,
            issuer=f"https://securetoken.google.com/{project}",
            options={"verify_at_hash": False, "leeway": CLOCK_SKEW_SECONDS},
        )
    except JWTError:
        raise FirebaseTokenError("Your verification has expired or is invalid. Please request a new OTP.")

    now = time.time()
    auth_time = claims.get("auth_time")
    if not claims.get("sub") or not isinstance(auth_time, (int, float)):
        raise FirebaseTokenError("Invalid verification. Please request a new OTP.")
    if auth_time > now + CLOCK_SKEW_SECONDS or claims.get("iat", 0) > now + CLOCK_SKEW_SECONDS:
        raise FirebaseTokenError("Invalid verification. Please request a new OTP.")
    if now - auth_time > MAX_AUTH_AGE_SECONDS:
        raise FirebaseTokenError("Your verification has expired. Please request a new OTP.")
    if (claims.get("firebase") or {}).get("sign_in_provider") != "phone":
        raise FirebaseTokenError("Invalid verification. Please request a new OTP.")

    phone = claims.get("phone_number") or ""
    if not re.fullmatch(r"\+91[6-9]\d{9}", phone):
        raise FirebaseTokenError("Only Indian mobile numbers (+91) are supported.")
    return phone[3:]
