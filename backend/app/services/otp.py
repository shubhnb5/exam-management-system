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
from app.rate_limit import FailureThrottle

logger = logging.getLogger("uvicorn.error")

PURPOSE_SIGNUP = "signup"
PURPOSE_RESET = "reset"

_ip_throttle = FailureThrottle(max_failures=settings.otp_max_sends_per_ip_per_hour, window_seconds=3600)


class OtpError(Exception):
    """A problem to show the student (status code + message for a form field)."""

    def __init__(self, status_code: int, message: str, field: str = "otp"):
        super().__init__(message)
        self.status_code = status_code
        self.message = message
        self.field = field


class OtpDeliveryError(Exception):
    def __init__(self, message: str, rate_limited: bool = False):
        super().__init__(message)
        self.rate_limited = rate_limited  # the provider refused because of its own per-number limit


# --------------------------------------------------------------- providers


def _send_console(mobile: str, code: str) -> None:
    logger.warning("[OTP TEST MODE] OTP for +91 %s is %s (no SMS sent)", mobile, code)


def _send_msg91(mobile: str, code: str) -> None:
    """MSG91 OTP API (v5). The OTP is generated here and passed to MSG91, which
    puts it into the DLT-approved template identified by MSG91_TEMPLATE_ID."""
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
            body = json.loads(response.read() or b"{}")
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise OtpDeliveryError(f"MSG91 request failed: {exc}") from exc
    if body.get("type") != "success":
        raise OtpDeliveryError(f"MSG91 rejected the request: {body.get('message') or body}")


def _error_message(body: bytes) -> str:
    try:
        data = json.loads(body or b"{}")
    except ValueError:
        return body[:200].decode("utf-8", "replace")
    if isinstance(data, dict):
        msg = data.get("message") or data.get("error")
        if isinstance(msg, list):
            msg = "; ".join(str(m) for m in msg)
        return str(msg or data)[:300]
    return str(data)[:300]


def _send_startmessaging(mobile: str, code: str) -> None:
    """StartMessaging OTP API: POST /otp/send with the code we generated.
    StartMessaging only delivers it; verification stays on our side."""
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
        # No automatic retry: a timed-out request may still have sent the SMS.
        with urllib.request.urlopen(request, timeout=15) as response:
            body = json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as exc:
        detail = _error_message(exc.read())
        hint = {
            401: " (STARTMESSAGING_API_KEY is wrong or revoked)",
            402: " (StartMessaging wallet balance is empty - top up at app.startmessaging.com)",
            429: " (StartMessaging rate limit)",
        }.get(exc.code, "")
        raise OtpDeliveryError(
            f"StartMessaging HTTP {exc.code}{hint}: {detail}", rate_limited=exc.code == 429
        ) from exc
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise OtpDeliveryError(f"StartMessaging request failed: {exc}") from exc
    if not isinstance(body, dict) or body.get("success") is False:
        raise OtpDeliveryError(f"StartMessaging rejected the request: {_error_message(json.dumps(body).encode())}")
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    logger.info(
        "OTP sent via StartMessaging to +91 %s (otpRequestId=%s, messageId=%s, status=%s)",
        mobile,
        data.get("otpRequestId"),
        data.get("messageId"),
        data.get("status"),
    )


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
    """Sends a new OTP. Returns {expires_in_seconds, resend_after_seconds,
    dev_otp}; dev_otp is only set in test mode with OTP_DEV_ECHO enabled."""
    now = _now()

    last = (
        db.query(OtpCode)
        .filter(OtpCode.mobile_number == mobile, OtpCode.purpose == purpose)
        .order_by(OtpCode.created_at.desc())
        .first()
    )
    if last is not None:
        wait = settings.otp_resend_seconds - int((now - last.created_at).total_seconds())
        if wait > 0:
            raise OtpError(429, f"Please wait {wait} seconds before requesting another OTP.", "mobile_number")

    sent_last_hour = (
        db.query(OtpCode)
        .filter(
            OtpCode.mobile_number == mobile,
            OtpCode.purpose == purpose,
            OtpCode.created_at > now - timedelta(hours=1),
        )
        .count()
    )
    if sent_last_hour >= settings.otp_max_sends_per_hour:
        raise OtpError(429, "Too many OTP requests for this number. Please try again after an hour.", "mobile_number")

    ip_key = f"otp-ip:{client_ip or 'unknown'}"
    try:
        _ip_throttle.check(ip_key)
    except Exception:
        raise OtpError(429, "Too many OTP requests from this network. Please try again later.", "mobile_number")

    code = f"{secrets.randbelow(10**6):06d}"
    try:
        _deliver(mobile, code)
    except OtpDeliveryError as exc:
        logger.error("OTP delivery failed for %s: %s", mobile, exc)
        if exc.rate_limited:
            raise OtpError(
                429, "Too many OTP requests for this number. Please wait 5 minutes and try again.", "mobile_number"
            )
        raise OtpError(502, "Could not send the OTP right now. Please try again in a minute.", "mobile_number")
    _ip_throttle.record_failure(ip_key)

    # Only the newest code for a number/purpose is ever valid.
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
        "resend_after_seconds": settings.otp_resend_seconds,
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
