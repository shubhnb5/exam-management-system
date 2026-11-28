import os

from app.models import Student
from app.services.pdf_generator import TicketConfig, generate_hall_ticket_pdf
from app.services.time_slots import ticket_timing

_TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ticket_template")
CONFIG_PATH = os.path.join(_TEMPLATE_DIR, "config.json")

# Everything that decides how an admit card looks. A cached PDF older than
# any of these was made with an earlier design/content and is regenerated
# (same QR code) on its next view or download.
_LAYOUT_SOURCES = [
    CONFIG_PATH,
    os.path.join(os.path.dirname(__file__), "pdf_generator.py"),
    os.path.join(os.path.dirname(__file__), "rules_page.py"),
]


def _layout_changed_at() -> float:
    newest = 0.0
    paths = list(_LAYOUT_SOURCES)
    try:
        config = TicketConfig.load(CONFIG_PATH)
        paths += [p for p in (config.header_image_path, config.stamp_path, config.photo_placeholder_path) if p]
    except (OSError, ValueError):
        pass
    for path in paths:
        try:
            newest = max(newest, os.path.getmtime(path))
        except OSError:
            pass
    return newest


def _is_stale(pdf_path: str, ticket) -> bool:
    if not os.path.isfile(pdf_path):
        return True
    made_at = os.path.getmtime(pdf_path)
    if made_at < _layout_changed_at():
        return True
    if ticket.updated_at is None:
        return False
    return made_at < ticket.updated_at.timestamp()


def generate_for_student(
    output_path: str, student: Student, qr_token: str, config: TicketConfig, timing: dict | None = None
) -> None:
    """Writes `student`'s admit card PDF with the given QR token. `timing` is
    the card's custom time slot timing (None = config.json's timing)."""
    generate_hall_ticket_pdf(
        output_path=output_path,
        student_name=student.full_name,
        mobile_number=student.mobile_number,
        exam_center_name=student.exam_center.name,
        qr_token=qr_token,
        config=config,
        district=student.exam_center.district,
        timing=timing,
    )


def ensure_ticket_pdf_on_disk(student: Student) -> str:
    """Returns a path to this student's hall ticket PDF, regenerating it if
    missing, older than the ticket's last data change, or made with an older
    card design. Many hosting platforms wipe local disk on every
    redeploy/restart, so the on-disk copy is treated purely as a cache — the
    QR token and student data already in the DB are enough to recreate it."""
    ticket = student.hall_ticket
    pdf_path = ticket.pdf_path

    if _is_stale(pdf_path, ticket):
        generate_for_student(pdf_path, student, ticket.qr_token, TicketConfig.load(CONFIG_PATH), ticket_timing(ticket))

    return pdf_path


def discard_ticket_pdf(pdf_path: str) -> None:
    """Best-effort removal of a cached PDF so the next download regenerates
    it. Failure is harmless: the staleness check above still catches it."""
    try:
        os.remove(pdf_path)
    except OSError:
        pass
