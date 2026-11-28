"""Rules for a single uploaded-student (roster) record, shared by the bulk
upload and the admin's Add/Edit Student form, so both behave identically."""

import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import ExamCenter, ExamCenterTimeSlot, HallTicket, Student
from app.services.pdf_generator import TicketConfig
from app.services.qr_service import generate_qr_token
from app.services.ticket_files import CONFIG_PATH, generate_for_student
from app.services.time_slots import set_ticket_timing, slot_timing, ticket_timing, timing_label
from app.config import settings
from app.validators import clean_name, normalize_mobile

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
STUDENT_NAME_MAX_LENGTH = 120

# ticket_changes(): "the caller isn't changing the time slot".
KEEP_TIME_SLOT = object()


def mobile_owner(db: Session, mobile: str, *, exclude_student_id: int | None = None, exclude_email: str | None = None):
    """Another roster student already using this mobile number, if any."""
    q = db.query(Student).filter(Student.mobile_number == mobile)
    if exclude_student_id is not None:
        q = q.filter(Student.id != exclude_student_id)
    if exclude_email is not None:
        q = q.filter(Student.email != exclude_email)
    return q.first()


def ticket_changes(
    student: Student, name: str, mobile: str, center: ExamCenter, time_slot=KEEP_TIME_SLOT
) -> list[str]:
    """Human-readable list of changes to details printed on the admit card.
    `time_slot` (an ExamCenterTimeSlot, or None = default timing) is compared
    too when given."""
    changes = []
    if student.full_name != name:
        changes.append(f"Name: {student.full_name} → {name}")
    if student.mobile_number != mobile:
        changes.append(f"Mobile: {student.mobile_number} → {mobile}")
    if student.exam_center_id != center.id:
        changes.append(f"Center: {student.exam_center.name} → {center.name}")
    if time_slot is not KEEP_TIME_SLOT and student.time_slot_id != (time_slot.id if time_slot else None):
        # "Old" is what the card actually prints (the slot may have been edited since).
        old = ticket_timing(student.hall_ticket) if student.hall_ticket is not None else slot_timing(student.time_slot)
        changes.append(f"Timing: {timing_label(old)} → {timing_label(slot_timing(time_slot))}")
    return changes


def assign_time_slot(student: Student, time_slot: ExamCenterTimeSlot | None) -> None:
    """Puts the student in `time_slot` (None = default timing). Moving a
    student who already has an admit card to another slot updates the card's
    timing too (same QR token); the caller marks the card outdated."""
    new_id = time_slot.id if time_slot else None
    if student.time_slot_id != new_id and student.hall_ticket is not None:
        set_ticket_timing(student.hall_ticket, time_slot)
    student.time_slot_id = new_id
    student.time_slot = time_slot


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
    time_slot_id: int | None = None,
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

    time_slot = db.get(ExamCenterTimeSlot, time_slot_id) if time_slot_id else None
    if time_slot_id and center is not None and (time_slot is None or time_slot.exam_center_id != center.id):
        errors["time_slot_id"] = "Please select an exam timing of the selected exam center."

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

    values = {"full_name": name, "email": email_clean, "mobile_number": mobile, "center": center, "time_slot": time_slot}
    return values, errors, conflicts


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
    timing = slot_timing(student.time_slot)
    generate_for_student(output_path, student, token, config, timing)
    ticket = HallTicket(student_id=student.id, qr_token=token, pdf_path=output_path)
    # The card keeps this timing even if the slot is edited later.
    set_ticket_timing(ticket, student.time_slot)
    db.add(ticket)
    return ticket
