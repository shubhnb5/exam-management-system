import secrets
from io import BytesIO

import qrcode


def generate_qr_token() -> str:
    """192 bits of randomness, URL-safe. Opaque by design: carries no
    student info, so it can't be guessed, derived, or reused across
    students the way a roll number could."""
    return secrets.token_urlsafe(24)


def render_qr_png(token: str) -> BytesIO:
    img = qrcode.make(token, box_size=8, border=2)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
