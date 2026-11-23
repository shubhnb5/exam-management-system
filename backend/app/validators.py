"""Pure validation/normalization helpers shared by the upload importer and
the student portal. No DB or framework access here, so they're trivially
testable."""

import re
import unicodedata
from decimal import Decimal, InvalidOperation

GMAIL_RE = re.compile(r"^[a-z0-9][a-z0-9._+-]{0,63}@gmail\.com$")

GENDERS = ("male", "female", "other")

PASSWORD_MIN_LENGTH = 8
# bcrypt only looks at the first 72 bytes of a password; cap well under that
# so two different long passwords can never silently hash the same.
PASSWORD_MAX_LENGTH = 64

NAME_MAX_LENGTH = 50
_NAME_PUNCTUATION = set(" .'-")


def normalize_mobile(raw: object) -> str | None:
    """Returns the 10-digit Indian mobile number contained in `raw`, or None
    if it isn't one. Accepts the formats real sheets contain:
    "9876543210", "+91 98765 43210", "091-9876543210", "09876543210", and the
    numeric cells spreadsheets produce ("9876543210.0", "9.87654321E9")."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None

    if re.fullmatch(r"\d+(\.\d+)?[eE]\+?\d+", text) or re.fullmatch(r"\d+\.0+", text):
        try:
            text = str(int(Decimal(text)))
        except (InvalidOperation, ValueError):
            return None

    digits = re.sub(r"\D", "", text)
    if len(digits) == 13 and digits.startswith("091"):
        digits = digits[3:]
    elif len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]

    if len(digits) == 10 and digits[0] in "6789":
        return digits
    return None


def mask_mobile(mobile: str) -> str:
    return f"{mobile[:2]}xxxxxx{mobile[-2:]}" if len(mobile) == 10 else mobile


def clean_name(raw: str | None) -> str:
    return re.sub(r"\s+", " ", (raw or "").strip())


def is_valid_name(name: str) -> bool:
    """Letters in any script (so Marathi/Devanagari names work, including
    their combining vowel signs) plus spaces, dots, apostrophes, hyphens."""
    if not name or len(name) > NAME_MAX_LENGTH:
        return False
    has_letter = False
    for ch in name:
        category = unicodedata.category(ch)
        if category[0] == "L":
            has_letter = True
        elif category[0] == "M" or ch in _NAME_PUNCTUATION:
            continue
        else:
            return False
    return has_letter


def normalize_gmail(raw: str | None) -> str:
    return (raw or "").strip().lower()


def is_valid_gmail(email: str) -> bool:
    return bool(GMAIL_RE.match(email))


def password_problem(password: str) -> str | None:
    """Returns a human-readable reason the password is unacceptable, or None."""
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
    if len(password) > PASSWORD_MAX_LENGTH:
        return f"Password must be at most {PASSWORD_MAX_LENGTH} characters."
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        return "Password must contain at least one letter and one number."
    return None


# --- Aadhaar -----------------------------------------------------------------
# UIDAI Aadhaar numbers are 12 digits, never start with 0 or 1, and end in a
# Verhoeff check digit — validating it catches nearly every typo.

_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)
_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)


def _verhoeff_ok(number: str) -> bool:
    check = 0
    for i, ch in enumerate(reversed(number)):
        check = _VERHOEFF_D[check][_VERHOEFF_P[i % 8][int(ch)]]
    return check == 0


def normalize_aadhaar(raw: str | None) -> str:
    return re.sub(r"[\s-]", "", raw or "")


def is_valid_aadhaar(number: str) -> bool:
    return bool(re.fullmatch(r"[2-9]\d{11}", number)) and _verhoeff_ok(number)


def mask_aadhaar(number: str) -> str:
    return f"XXXX-XXXX-{number[-4:]}"
