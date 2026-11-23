"""Rules for a single uploaded-student (roster) record, shared by the bulk
upload and the admin's Add/Edit Student form, so both behave identically."""

import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import ExamCenter, HallTicket, Student
from app.services.pdf_generator import TicketConfig, generate_hall_ticket_pdf
from app.services.qr_service import generate_qr_token
from app.services.ticket_files import CONFIG_PATH
from app.config import settings
from app.validators import clean_name, normalize_mobile

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STUDENT_NAME_MAX_LENGTH = 120


def mobile_owner(db: Session, mobile: str, *, exclude_student_id: int | None = None, exclude_email: str | None = None):
    """Another roster student already using this mobile number, if any."""
    q = db.query(Student).filter(Student.mobile_number == mobile)
    if exclude_student_id is not None:
        q = q.filter(Student.id != exclude_student_id)
    if exclude_email is not None:
        q = q.filter(Student.email != exclude_email)
    return q.first()


def ticket_changes(student: Student, name: str, mobile: str, center: ExamCenter) -> list[str]:
    """Human-readable list of changes to details printed on the admit card."""
    changes = []
    if student.full_name != name:
        changes.append(f"Name: {student.full_name} → {name}")
    if student.mobile_number != mobile:
        changes.append(f"Mobile: {student.mobile_number} → {mobile}")
    if student.exam_center_id != center.id:
        changes.append(f"Center: {student.exam_center.name} → {center.name}")
    return changes


def mark_ticket_outdated(student: Student) -> str | None:
    """Flags an existing admit card for regeneration (QR token unchanged).
    Returns the cached PDF path for the caller to discard after commit."""
    if student.hall_ticket is None:
        return None
    student.hall_ticket.updated_at = datetime.now(timezone.utc)
    return student.hall_ticket.pdf_path


def validate_student_input(
    db: Session,
    *,
    full_name: str,
    email: str,
    mobile_number: str,
    exam_center_id: int | None,
    student_id: int | None = None,
) -> tuple[dict, dict[str, str], dict[str, str]]:
    """Validates Add/Edit Student form input.

    Returns (clean_values, field_errors, conflicts). `conflicts` are
    duplicate email/mobile problems (HTTP 409); `field_errors` are invalid
    values (HTTP 422)."""
    errors: dict[str, str] = {}
    conflicts: dict[str, str] = {}

    name = clean_name(full_name)
    if not name:
        errors["full_name"] = "Student name is required."
    elif len(name) > STUDENT_NAME_MAX_LENGTH:
        errors["full_name"] = f"Student name must be at most {STUDENT_NAME_MAX_LENGTH} characters."

    email_clean = (email or "").strip().lower()
    if not email_clean:
        errors["email"] = "Email is required."
    elif not EMAIL_RE.match(email_clean):
        errors["email"] = "Enter a valid email address."

    mobile = normalize_mobile(mobile_number)
    if not (mobile_number or "").strip():
        errors["mobile_number"] = "Mobile number is required."
    elif mobile is None:
        errors["mobile_number"] = "Enter a valid 10-digit Indian mobile number."

    center = db.get(ExamCenter, exam_center_id) if exam_center_id else None
    if center is None:
        errors["exam_center_id"] = "Please select an exam center."

    if "email" not in errors:
        q = db.query(Student).filter(Student.email == email_clean)
        if student_id is not None:
            q = q.filter(Student.id != student_id)
        other = q.first()
        if other:
            conflicts["email"] = f"This email already belongs to {other.full_name} ({other.mobile_number})."

    if "mobile_number" not in errors:
        other = mobile_owner(db, mobile, exclude_student_id=student_id)
        if other:
            conflicts["mobile_number"] = f"This mobile number already belongs to {other.full_name} ({other.email})."

    return {"full_name": name, "email": email_clean, "mobile_number": mobile, "center": center}, errors, conflicts


def create_ticket_for_student(db: Session, student: Student, config: TicketConfig | None = None) -> HallTicket:
    """Generates one student's admit card (PDF + QR token) and adds the
    HallTicket row to the session. The caller commits."""
    config = config or TicketConfig.load(CONFIG_PATH)
    token = generate_qr_token()
    # Always use forward slashes, even on Windows dev machines — this
    # path gets stored in the DB and must resolve correctly wherever
    # it's read back from later (e.g. a Linux production container
    # sharing the same volume/database).
    output_path = f"{settings.ticket_storage_dir.rstrip('/')}/{student.id}.pdf"
    generate_hall_ticket_pdf(
        output_path=output_path,
        student_name=student.full_name,
        mobile_number=student.mobile_number,
        exam_center_name=student.exam_center.name,
        qr_token=token,
        config=config,
    )
    ticket = HallTicket(student_id=student.id, qr_token=token, pdf_path=output_path)
    db.add(ticket)
    return ticket
