"""One-time passwords over SMS for verifying a student's mobile number
(signup) and for resetting a forgotten password.

- Codes are 6 random digits, single-use, valid for OTP_EXPIRY_MINUTES.
- Only a keyed HMAC of the code is stored (see field_crypto.fingerprint).
- Abuse limits: a resend cooldown, a per-number hourly cap, a per-IP hourly
  cap (SMS costs money), and a cap on wrong guesses per code.
- Delivery is pluggable: "console" (test mode, no SMS), "msg91" or
  "startmessaging". (With "firebase" the browser does the OTP with Google and
  this module is not used for sending.)
"""

import json
import logging
import secrets
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app import field_crypto
from app.config import settings
from app.models import OtpCode
from app.validators import mask_mobile

logger = logging.getLogger("uvicorn.error")

PURPOSE_SIGNUP = "signup"
PURPOSE_RESET = "reset"


class OtpError(Exception):
    """A problem to show the student (status code or message for a form field)."""

    def __init__(self, status_code: int, message: str, field: str = "otp"):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.field = field


class OtpDeliveryError(Exception):
    def __init__(self, message: str, rate_limited: bool = False, status_code: int | None = None):
        super().__init__(message)
        self.rate_limited = rate_limited
        self.status_code = status_code


# --------------------------------------------------------------- providers


def _send_console(mobile: str, code: str) -> None:
    logger.warning("[OTP TEST MODE] No SMS sent for mobile ending %s", mobile[-4:] if mobile else "")


def _send_msg91(mobile: str, code: str) -> None:
    """MSG91 OTP API (v5). The OTP is generated here and passed to MSG91."""
    if not settings.msg91_auth_key or not settings.msg91_template_id:
        raise OtpDeliveryError("MSG91_AUTH_KEY / MSG91_TEMPLATE_ID are not configured")
    query = urllib.parse.urlencode(
        {
            "template_id": settings.msg91_template_id,
            "mobile": f"91{mobile}",
            "otp": code,
            "otp_expiry": settings.otp_expiry_minutes,
        }
    )
    request = urllib.request.Request(
        f"{settings.msg91_otp_url}?{query}",
        data=b"{}",
        method="POST",
        headers={"authkey": settings.msg91_auth_key, "Content-Type": "application/json", "accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            status_code = response.status
            body = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        detail = _error_message(exc.read())
        logger.error("MSG91 OTP delivery failed: HTTP %s mobile=%s", status_code, mask_mobile(mobile))
        raise OtpDeliveryError(
            f"MSG91 HTTP {status_code}: {detail}",
            rate_limited=status_code == 429,
            status_code=status_code,
        ) from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.error("MSG91 OTP request failed for mobile=%s: %s", mask_mobile(mobile), type(exc).__name__)
        raise OtpDeliveryError(f"MSG91 request failed: {type(exc).__name__}") from exc

    logger.info("MSG91 OTP API response: HTTP %s mobile=%s", status_code, mask_mobile(mobile))
    if body.get("type") != "success":
        raise OtpDeliveryError(
            f"MSG91 rejected the request: {body.get('message') or 'provider error'}",
            status_code=status_code,
        )


def _error_message(body: bytes) -> str:
    try:
        data = json.loads(body or b"{}")
    except ValueError:
        return "provider error"
    if isinstance(data, dict):
        msg = data.get("message") or data.get("error")
        if isinstance(msg, list):
            msg = "; ".join(str(m) for m in msg)
        return str(msg or "provider error")[:300]
    return str(data)[:300]


def _send_startmessaging(mobile: str, code: str) -> None:
    """StartMessaging OTP API: POST /otp/send with the code we generated."""
    if not settings.startmessaging_api_key:
        raise OtpDeliveryError("STARTMESSAGING_API_KEY is not configured")
    variables = {"otp": code}
    if settings.startmessaging_app_name:
        variables["appName"] = settings.startmessaging_app_name
    payload = {"phoneNumber": f"+91{mobile}", "variables": variables}
    if settings.startmessaging_template_id:
        payload["templateId"] = settings.startmessaging_template_id
    request = urllib.request.Request(
        settings.startmessaging_otp_url,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={
            "X-API-Key": settings.startmessaging_api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            status_code = response.status
            body = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        status_code = exc.code
        detail = _error_message(exc.read())
        logger.error("StartMessaging OTP delivery failed: HTTP %s mobile=%s", status_code, mask_mobile(mobile))
        raise OtpDeliveryError(
            f"StartMessaging HTTP {status_code}: {detail}",
            rate_limited=status_code == 429,
            status_code=status_code,
        ) from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        logger.error("StartMessaging OTP request failed for mobile=%s: %s", mask_mobile(mobile), type(exc).__name__)
        raise OtpDeliveryError(f"StartMessaging request failed: {type(exc).__name__}") from exc

    logger.info("StartMessaging OTP API response: HTTP %s mobile=%s", status_code, mask_mobile(mobile))
    if not isinstance(body, dict) or body.get("success") is False:
        raise OtpDeliveryError("StartMessaging rejected the request")


_SMS_PROVIDERS = {"msg91": _send_msg91, "startmessaging": _send_startmessaging}


def _deliver(mobile: str, code: str) -> None:
    _SMS_PROVIDERS.get(settings.otp_provider, _send_console)(mobile, code)


def is_test_mode() -> bool:
    return settings.otp_provider not in (*_SMS_PROVIDERS, "firebase")


# ------------------------------------------------------------------- logic


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(mobile: str, purpose: str, code: str) -> str:
    return field_crypto.fingerprint(f"otp:{purpose}:{mobile}:{code}")


def send_otp(db: Session, mobile: str, purpose: str, client_ip: str | None) -> dict:
    """Sends an OTP without application-level send, resend, or IP limits."""
    now = _now()

    code = f"{secrets.randbelow(10**6):06d}"
    try:
        _deliver(mobile, code)
    except OtpDeliveryError as exc:
        logger.error(
            "OTP delivery failed mobile=%s status=%s provider=%s",
            mask_mobile(mobile),
            exc.status_code or "network",
            settings.otp_provider,
        )
        if exc.rate_limited:
            raise OtpError(
                429, "The OTP provider rate limit was reached. Please wait and try again.", "mobile_number"
            )
        raise OtpError(502, "Could not send the OTP right now. Please try again.", "mobile_number")

    logger.info("OTP delivered mobile=%s client_ip=%s", mask_mobile(mobile), client_ip or "unknown")

    db.query(OtpCode).filter(
        OtpCode.mobile_number == mobile, OtpCode.purpose == purpose, OtpCode.consumed_at.is_(None)
    ).update({OtpCode.consumed_at: now}, synchronize_session=False)
    db.add(
        OtpCode(
            mobile_number=mobile,
            purpose=purpose,
            code_hash=_hash(mobile, purpose, code),
            attempts=0,
            expires_at=now + timedelta(minutes=settings.otp_expiry_minutes),
            created_at=now,
        )
    )
    db.commit()

    return {
        "expires_in_seconds": settings.otp_expiry_minutes * 60,
        "resend_after_seconds": 0,
        "test_mode": is_test_mode(),
        "dev_otp": code if is_test_mode() and settings.otp_dev_echo else None,
    }


def verify_otp(db: Session, mobile: str, purpose: str, code: str) -> None:
    """Consumes the OTP if correct; raises OtpError otherwise."""
    code = (code or "").strip()
    if not (len(code) == 6 and code.isdigit()):
        raise OtpError(422, "Enter the 6-digit OTP.")

    now = _now()
    row = (
        db.query(OtpCode)
        .filter(OtpCode.mobile_number == mobile, OtpCode.purpose == purpose, OtpCode.consumed_at.is_(None))
        .order_by(OtpCode.created_at.desc())
        .with_for_update()
        .first()
    )
    if row is None or row.expires_at <= now:
        db.rollback()
        raise OtpError(400, "This OTP has expired. Please request a new one.")
    if row.attempts >= settings.otp_max_attempts:
        db.rollback()
        raise OtpError(400, "Too many wrong attempts. Please request a new OTP.")

    if not secrets.compare_digest(row.code_hash, _hash(mobile, purpose, code)):
        row.attempts += 1
        left = settings.otp_max_attempts - row.attempts
        db.commit()
        if left <= 0:
            raise OtpError(400, "Too many wrong attempts. Please request a new OTP.")
        raise OtpError(400, f"Incorrect OTP. {left} attempt{'s' if left != 1 else ''} left.")

    row.consumed_at = now
    db.commit()
