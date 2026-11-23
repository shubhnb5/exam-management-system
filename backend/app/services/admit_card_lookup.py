"""Links a student portal account to the admin-uploaded roster.

The link is the normalized 10-digit mobile number: it is unique per account
(enforced at signup) and unique per uploaded student (enforced at upload), so
a logged-in student can only ever resolve to their own admit card. The lookup
always starts from the authenticated account — never from an ID supplied by
the client."""

from sqlalchemy.orm import Session, joinedload

from app.models import Student
from app.schemas import AdmitCardStatus

STATUS_AVAILABLE = "available"
STATUS_NOT_GENERATED = "not_generated"
STATUS_NOT_FOUND = "not_found"


def _pick(students: list[Student]) -> Student | None:
    # Uniqueness is enforced on upload; if older data still has duplicates,
    # prefer the record that actually has an admit card, then the newest.
    if not students:
        return None
    return sorted(
        students,
        key=lambda s: (s.hall_ticket is not None, s.updated_at or s.created_at, s.id),
        reverse=True,
    )[0]


def find_roster_student(db: Session, mobile_number: str) -> Student | None:
    students = (
        db.query(Student)
        .options(joinedload(Student.hall_ticket), joinedload(Student.exam_center))
        .filter(Student.mobile_number == mobile_number)
        .all()
    )
    return _pick(students)


def roster_by_mobile(db: Session, mobile_numbers: list[str]) -> dict[str, Student]:
    """Bulk version of find_roster_student for admin listings (one query)."""
    if not mobile_numbers:
        return {}
    students = (
        db.query(Student)
        .options(joinedload(Student.hall_ticket), joinedload(Student.exam_center))
        .filter(Student.mobile_number.in_(mobile_numbers))
        .all()
    )
    grouped: dict[str, list[Student]] = {}
    for s in students:
        grouped.setdefault(s.mobile_number, []).append(s)
    return {mobile: _pick(group) for mobile, group in grouped.items()}


def admit_card_status(student: Student | None) -> AdmitCardStatus:
    if student is None:
        return AdmitCardStatus(status=STATUS_NOT_FOUND)
    if student.hall_ticket is None:
        return AdmitCardStatus(status=STATUS_NOT_GENERATED, exam_center_name=student.exam_center.name)
    ticket = student.hall_ticket
    return AdmitCardStatus(
        status=STATUS_AVAILABLE,
        exam_center_name=student.exam_center.name,
        generated_at=ticket.generated_at,
        updated_at=ticket.updated_at,
    )
