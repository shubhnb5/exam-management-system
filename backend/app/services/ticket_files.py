import os

from app.models import Student
from app.services.pdf_generator import TicketConfig, generate_hall_ticket_pdf

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ticket_template", "config.json")


def ensure_ticket_pdf_on_disk(student: Student) -> str:
    """Returns a path to this student's hall ticket PDF, regenerating it if
    missing. Many hosting platforms wipe local disk on every redeploy/restart,
    so the on-disk copy is treated purely as a cache — the QR token and
    student data already in the DB are enough to recreate it identically."""
    ticket = student.hall_ticket
    pdf_path = ticket.pdf_path

    if not os.path.isfile(pdf_path):
        config = TicketConfig.load(CONFIG_PATH)
        generate_hall_ticket_pdf(
            output_path=pdf_path,
            student_name=student.full_name,
            mobile_number=student.mobile_number,
            exam_center_name=student.exam_center.name,
            qr_token=ticket.qr_token,
            config=config,
        )

    return pdf_path
