"""Student portal: self-registration, login, password reset, and download of
the student's own admit card.

Validation errors are returned as 422 with `detail = {"errors": {field: message}}`
so the frontend can show each message under the right input."""

import re
from datetime import datetime, timezone

from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, HTMLResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import field_crypto
from app.database import get_db
from app.http_errors import field_conflicts as _conflict
from app.http_errors import field_errors as _field_errors
from app.models import StudentAccount
from app.rate_limit import student_login_throttle
from app.schemas import (
    AdmitCardLink,
    ForgotPasswordResetRequest,
    ForgotPasswordVerifyResponse,
    OtpSendRequest,
    OtpSendResponse,
    OtpVerifyRequest,
    SignupOtpVerifyResponse,
    StudentLoginRequest,
    StudentProfile,
    StudentSignupRequest,
    StudentToken,
)
from app.security import (
    ADMIT_DOWNLOAD_EXPIRE_MINUTES,
    PASSWORD_RESET_EXPIRE_MINUTES,
    SIGNUP_MOBILE_TOKEN_EXPIRE_MINUTES,
    TOKEN_STUDENT_ADMIT_DOWNLOAD,
    TOKEN_STUDENT_PASSWORD_RESET,
    create_student_access_token,
    create_student_download_token,
    create_signup_mobile_token,
    create_student_password_reset_token,
    get_current_student,
    hash_password,
    resolve_signup_mobile_token,
    resolve_student_token,
    verify_password,
)
from app.services import otp as otp_service
from app.services.admit_card_lookup import STATUS_AVAILABLE, admit_card_status, find_roster_student
from app.services.ticket_files import ensure_ticket_pdf_on_disk
from app.validators import (
    GENDERS,
    clean_name,
    is_valid_aadhaar,
    is_valid_gmail,
    is_valid_name,
    normalize_aadhaar,
    normalize_gmail,
    normalize_mobile,
    password_problem,
)

router = APIRouter(prefix="/student", tags=["student"])

MSG_MOBILE_TAKEN = "An account with this mobile number already exists. Please log in, or use Forgot password."
MSG_EMAIL_TAKEN = "An account with this Gmail ID already exists."
MSG_AADHAAR_TAKEN = "This Aadhaar number is already registered with another account."


def _now() -> datetime:
    # Whole seconds: the value is embedded in tokens as an int timestamp.
    return datetime.now(timezone.utc).replace(microsecond=0)


def _valid_mobile_or_422(raw: str) -> str:
    mobile = normalize_mobile(raw or "")
    if not (raw or "").strip():
        raise _field_errors({"mobile_number": "Mobile number is required."})
    if mobile is None:
        raise _field_errors({"mobile_number": "Enter a valid 10-digit mobile number."})
    return mobile


def _otp_http_error(exc: otp_service.OtpError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail={"errors": {exc.field: exc.message}})


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


# ----------------------------------------------------------- signup OTP


@router.post("/signup/send-otp", response_model=OtpSendResponse)
def signup_send_otp(payload: OtpSendRequest, request: Request, db: Session = Depends(get_db)):
    """Step 1 of mobile verification at signup: send an OTP to the number."""
    mobile = _valid_mobile_or_422(payload.mobile_number)
    if db.query(StudentAccount.id).filter(StudentAccount.mobile_number == mobile).first():
        raise _conflict({"mobile_number": MSG_MOBILE_TAKEN})
    try:
        return otp_service.send_otp(db, mobile, otp_service.PURPOSE_SIGNUP, _client_ip(request))
    except otp_service.OtpError as exc:
        raise _otp_http_error(exc)


@router.post("/signup/verify-otp", response_model=SignupOtpVerifyResponse)
def signup_verify_otp(payload: OtpVerifyRequest, db: Session = Depends(get_db)):
    """Step 2: check the OTP. Returns a short-lived token that /signup requires
    as proof the student owns this mobile number."""
    mobile = _valid_mobile_or_422(payload.mobile_number)
    try:
        otp_service.verify_otp(db, mobile, otp_service.PURPOSE_SIGNUP, payload.otp)
    except otp_service.OtpError as exc:
        raise _otp_http_error(exc)
    return SignupOtpVerifyResponse(
        mobile_verification_token=create_signup_mobile_token(mobile),
        expires_in_minutes=SIGNUP_MOBILE_TOKEN_EXPIRE_MINUTES,
    )


@router.post("/signup", response_model=StudentToken, status_code=status.HTTP_201_CREATED)
def signup(payload: StudentSignupRequest, db: Session = Depends(get_db)):
    errors: dict[str, str] = {}

    first_name = clean_name(payload.first_name)
    middle_name = clean_name(payload.middle_name) or None
    last_name = clean_name(payload.last_name)
    for field, value, required in (
        ("first_name", first_name, True),
        ("middle_name", middle_name, False),
        ("last_name", last_name, True),
    ):
        if not value:
            if required:
                errors[field] = "This field is required."
        elif not is_valid_name(value):
            errors[field] = "Use letters only (spaces, dot, apostrophe and hyphen allowed), max 50 characters."

    email = normalize_gmail(payload.email)
    if not email:
        errors["email"] = "Gmail ID is required."
    elif not is_valid_gmail(email):
        errors["email"] = "Enter a valid Gmail address ending with @gmail.com."

    mobile = normalize_mobile(payload.mobile_number)
    if not payload.mobile_number.strip():
        errors["mobile_number"] = "Mobile number is required."
    elif mobile is None:
        errors["mobile_number"] = "Enter a valid 10-digit mobile number."

    gender = (payload.gender or "").strip().lower()
    if gender not in GENDERS:
        errors["gender"] = "Please select your gender."

    aadhaar = normalize_aadhaar(payload.aadhaar_number)
    if aadhaar and not is_valid_aadhaar(aadhaar):
        errors["aadhaar_number"] = "Enter a valid 12-digit Aadhaar number, or leave it blank."

    problem = password_problem(payload.password or "")
    if problem:
        errors["password"] = problem

    if errors:
        raise _field_errors(errors)

    aadhaar_hash = field_crypto.fingerprint(aadhaar) if aadhaar else None

    # Friendly per-field messages for the common case; the unique constraints
    # below remain the real guarantee if two signups race each other.
    conflicts: dict[str, str] = {}
    if db.query(StudentAccount.id).filter(StudentAccount.mobile_number == mobile).first():
        conflicts["mobile_number"] = MSG_MOBILE_TAKEN
    if db.query(StudentAccount.id).filter(StudentAccount.email == email).first():
        conflicts["email"] = MSG_EMAIL_TAKEN
    if aadhaar_hash and db.query(StudentAccount.id).filter(StudentAccount.aadhaar_hash == aadhaar_hash).first():
        conflicts["aadhaar_number"] = MSG_AADHAAR_TAKEN
    if conflicts:
        raise _conflict(conflicts)

    # The mobile number must have been proven with an OTP (signup/verify-otp).
    if resolve_signup_mobile_token(payload.mobile_verification_token) != mobile:
        raise _field_errors({"mobile_number": "Please verify your mobile number with the OTP first."})

    account = StudentAccount(
        first_name=first_name,
        middle_name=middle_name,
        last_name=last_name,
        email=email,
        mobile_number=mobile,
        gender=gender,
        aadhaar_encrypted=field_crypto.encrypt(aadhaar) if aadhaar else None,
        aadhaar_hash=aadhaar_hash,
        password_hash=hash_password(payload.password),
        password_changed_at=_now(),
        mobile_verified_at=_now(),
    )
    db.add(account)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        text = str(exc.orig)
        if "mobile_number" in text:
            raise _conflict({"mobile_number": MSG_MOBILE_TAKEN})
        if "email" in text:
            raise _conflict({"email": MSG_EMAIL_TAKEN})
        if "aadhaar" in text:
            raise _conflict({"aadhaar_number": MSG_AADHAAR_TAKEN})
        raise
    db.refresh(account)

    return StudentToken(access_token=create_student_access_token(account), full_name=account.full_name)


@router.post("/login", response_model=StudentToken)
def login(payload: StudentLoginRequest, db: Session = Depends(get_db)):
    mobile = normalize_mobile(payload.mobile_number)
    throttle_key = mobile or re.sub(r"\D", "", payload.mobile_number)
    student_login_throttle.check(throttle_key)

    account = db.query(StudentAccount).filter(StudentAccount.mobile_number == mobile).first() if mobile else None
    if account is None or not verify_password(payload.password, account.password_hash):
        student_login_throttle.record_failure(throttle_key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid mobile number or password.")

    student_login_throttle.reset(throttle_key)
    return StudentToken(access_token=create_student_access_token(account), full_name=account.full_name)


@router.post("/forgot-password/send-otp", response_model=OtpSendResponse)
def forgot_password_send_otp(payload: OtpSendRequest, request: Request, db: Session = Depends(get_db)):
    """Step 1: send an OTP to the account's registered mobile number."""
    mobile = _valid_mobile_or_422(payload.mobile_number)
    if not db.query(StudentAccount.id).filter(StudentAccount.mobile_number == mobile).first():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"errors": {"mobile_number": "No account is registered with this mobile number."}},
        )
    try:
        return otp_service.send_otp(db, mobile, otp_service.PURPOSE_RESET, _client_ip(request))
    except otp_service.OtpError as exc:
        raise _otp_http_error(exc)


@router.post("/forgot-password/verify-otp", response_model=ForgotPasswordVerifyResponse)
def forgot_password_verify_otp(payload: OtpVerifyRequest, db: Session = Depends(get_db)):
    """Step 2: a correct OTP returns a short-lived, single-use token that
    allows setting a new password (step 3)."""
    mobile = _valid_mobile_or_422(payload.mobile_number)
    account = db.query(StudentAccount).filter(StudentAccount.mobile_number == mobile).first()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"errors": {"mobile_number": "No account is registered with this mobile number."}},
        )
    try:
        otp_service.verify_otp(db, mobile, otp_service.PURPOSE_RESET, payload.otp)
    except otp_service.OtpError as exc:
        raise _otp_http_error(exc)
    if account.mobile_verified_at is None:
        # Older accounts (created before OTP existed) become verified here.
        account.mobile_verified_at = _now()
        db.commit()
        db.refresh(account)
    return ForgotPasswordVerifyResponse(
        reset_token=create_student_password_reset_token(account),
        expires_in_minutes=PASSWORD_RESET_EXPIRE_MINUTES,
    )


@router.post("/forgot-password/reset", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password_reset(payload: ForgotPasswordResetRequest, db: Session = Depends(get_db)):
    """Step 3: set the new password. Changing it invalidates the reset token
    and logs out every existing session of this account."""
    account = resolve_student_token(payload.reset_token, TOKEN_STUDENT_PASSWORD_RESET, db)
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link has expired or was already used. Please start again.",
        )

    problem = password_problem(payload.new_password or "")
    if problem:
        raise _field_errors({"new_password": problem})

    account.password_hash = hash_password(payload.new_password)
    account.password_changed_at = _now()
    db.commit()
    student_login_throttle.reset(account.mobile_number)


@router.get("/me", response_model=StudentProfile)
def me(account: StudentAccount = Depends(get_current_student), db: Session = Depends(get_db)):
    return StudentProfile(
        first_name=account.first_name,
        middle_name=account.middle_name,
        last_name=account.last_name,
        full_name=account.full_name,
        email=account.email,
        mobile_number=account.mobile_number,
        gender=account.gender,
        admit_card=admit_card_status(find_roster_student(db, account.mobile_number)),
    )


def _available_card_or_404(db: Session, account: StudentAccount):
    # The roster record is looked up from the authenticated account's own
    # mobile number — there is no way to ask for anyone else's card.
    student = find_roster_student(db, account.mobile_number)
    if admit_card_status(student).status != STATUS_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Your admit card is not available yet. Please contact the admin.",
        )
    return student


def _admit_card_file_response(student):
    pdf_path = ensure_ticket_pdf_on_disk(student)
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", student.full_name).strip("_") or "student"
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"Admit_Card_{safe_name}.pdf",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/admit-card")
def download_admit_card(account: StudentAccount = Depends(get_current_student), db: Session = Depends(get_db)):
    return _admit_card_file_response(_available_card_or_404(db, account))


@router.post("/admit-card/link", response_model=AdmitCardLink)
def admit_card_link(account: StudentAccount = Depends(get_current_student), db: Session = Depends(get_db)):
    """Returns a 2-minute download link for the student's own admit card.
    The portal opens it as a normal link instead of downloading through
    JavaScript, which fails silently in many phone in-app browsers
    (WhatsApp/Instagram/Gmail) and some older mobile browsers."""
    _available_card_or_404(db, account)
    token = create_student_download_token(account)
    return AdmitCardLink(
        path=f"/student/admit-card/file?token={quote(token)}",
        expires_in_seconds=ADMIT_DOWNLOAD_EXPIRE_MINUTES * 60,
    )


def _message_page(status_code: int, message: str) -> HTMLResponse:
    # The download link is opened directly by the phone's browser, so errors
    # are shown as a readable page rather than raw JSON.
    return HTMLResponse(
        status_code=status_code,
        content=(
            '<!doctype html><html lang="en"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            "<title>Admit Card</title></head>"
            '<body style="font-family:sans-serif;padding:32px 20px;max-width:480px;margin:auto;color:#0f172a">'
            f'<h2 style="margin-top:0">Admit Card</h2><p style="font-size:17px">{message}</p></body></html>'
        ),
    )


@router.get("/admit-card/file")
def admit_card_file(token: str = Query(...), db: Session = Depends(get_db)):
    account = resolve_student_token(token, TOKEN_STUDENT_ADMIT_DOWNLOAD, db)
    if account is None:
        return _message_page(
            status.HTTP_401_UNAUTHORIZED,
            "This download link has expired. Please go back to the student portal and tap Download again.",
        )
    student = find_roster_student(db, account.mobile_number)
    if admit_card_status(student).status != STATUS_AVAILABLE:
        return _message_page(
            status.HTTP_404_NOT_FOUND, "Your admit card is not available yet. Please contact the admin."
        )
    return _admit_card_file_response(student)
