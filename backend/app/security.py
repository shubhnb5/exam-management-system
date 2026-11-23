from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import StudentAccount, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Every token carries a "typ" claim so a token minted for one audience can
# never be accepted by another (e.g. a student token on an admin endpoint).
# Staff tokens issued before this claim existed have no "typ" and are still
# accepted as staff until they expire.
TOKEN_STAFF = "staff"
TOKEN_STUDENT = "student"
TOKEN_STUDENT_PASSWORD_RESET = "student_pwd_reset"
TOKEN_STUDENT_ADMIT_DOWNLOAD = "student_admit_dl"
TOKEN_SIGNUP_MOBILE = "signup_mobile"

STUDENT_SUBJECT_PREFIX = "student:"
PASSWORD_RESET_EXPIRE_MINUTES = 10
ADMIT_DOWNLOAD_EXPIRE_MINUTES = 2
SIGNUP_MOBILE_TOKEN_EXPIRE_MINUTES = 20


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _encode(claims: dict, expire_minutes: int) -> str:
    payload = {**claims, "exp": datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)}
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def _decode(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def create_access_token(subject: str) -> str:
    """Token for admin/teacher (users table)."""
    return _encode({"sub": subject, "typ": TOKEN_STAFF}, settings.jwt_expire_minutes)


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    payload = _decode(token)
    if payload is None or payload.get("typ", TOKEN_STAFF) != TOKEN_STAFF:
        raise _credentials_error()
    username: str | None = payload.get("sub")
    if username is None:
        raise _credentials_error()

    user = db.query(User).filter(User.username == username).first()
    if user is None or not user.is_active:
        raise _credentials_error()
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


def require_teacher(user: User = Depends(get_current_user)) -> User:
    if user.role != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Teacher access required")
    return user


# --- Student portal ----------------------------------------------------------


def _password_stamp(account: StudentAccount) -> int:
    return int(account.password_changed_at.timestamp())


def _student_claims(account: StudentAccount, typ: str) -> dict:
    return {
        "sub": f"{STUDENT_SUBJECT_PREFIX}{account.id}",
        "typ": typ,
        "pwc": _password_stamp(account),
    }


def create_student_access_token(account: StudentAccount) -> str:
    return _encode(_student_claims(account, TOKEN_STUDENT), settings.jwt_expire_minutes)


def create_student_password_reset_token(account: StudentAccount) -> str:
    return _encode(_student_claims(account, TOKEN_STUDENT_PASSWORD_RESET), PASSWORD_RESET_EXPIRE_MINUTES)


def create_signup_mobile_token(mobile: str) -> str:
    """Proof (from a successful signup OTP) that the holder owns `mobile`.
    Required to create an account with that number."""
    return _encode({"sub": f"mobile:{mobile}", "typ": TOKEN_SIGNUP_MOBILE}, SIGNUP_MOBILE_TOKEN_EXPIRE_MINUTES)


def resolve_signup_mobile_token(token: str | None) -> str | None:
    payload = _decode(token) if token else None
    if payload is None or payload.get("typ") != TOKEN_SIGNUP_MOBILE:
        return None
    subject = payload.get("sub") or ""
    return subject[len("mobile:"):] if subject.startswith("mobile:") else None


def create_student_download_token(account: StudentAccount) -> str:
    """Short-lived token that can only download this student's own admit
    card — safe to put in a URL (see /student/admit-card/link)."""
    return _encode(_student_claims(account, TOKEN_STUDENT_ADMIT_DOWNLOAD), ADMIT_DOWNLOAD_EXPIRE_MINUTES)


def resolve_student_token(token: str, expected_typ: str, db: Session) -> StudentAccount | None:
    """Returns the account a student token belongs to, or None if the token is
    invalid, expired, of the wrong type, or was issued before the account's
    last password change (logs out old sessions, makes reset tokens single-use)."""
    payload = _decode(token)
    if payload is None or payload.get("typ") != expected_typ:
        return None
    subject = payload.get("sub") or ""
    if not subject.startswith(STUDENT_SUBJECT_PREFIX):
        return None
    try:
        account_id = int(subject[len(STUDENT_SUBJECT_PREFIX):])
    except ValueError:
        return None

    account = db.get(StudentAccount, account_id)
    if account is None or payload.get("pwc") != _password_stamp(account):
        return None
    return account


def get_current_student(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> StudentAccount:
    account = resolve_student_token(token, TOKEN_STUDENT, db)
    if account is None:
        raise _credentials_error()
    return account
