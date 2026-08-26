from sqlalchemy.orm import Session

from app.config import settings
from app.models import HallTicket, Student
from app.services.pdf_generator import TicketConfig, generate_hall_ticket_pdf
from app.services.qr_service import generate_qr_token
from app.services.ticket_files import CONFIG_PATH


def generate_tickets_for_all(db: Session) -> tuple[int, int, list[str]]:
    """Generates a hall ticket + QR for every student who doesn't already have
    one. Existing tickets are left untouched so re-running after a fresh
    Excel upload only produces tickets for newly added students."""
    config = TicketConfig.load(CONFIG_PATH)
    students = db.query(Student).filter(Student.hall_ticket == None).all()  # noqa: E711

    generated = 0
    failed: list[str] = []

    for student in students:
        try:
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
            db.add(
                HallTicket(
                    student_id=student.id,
                    qr_token=token,
                    pdf_path=output_path,
                )
            )
            db.commit()
            generated += 1
        except Exception as exc:  # noqa: BLE001 - keep processing remaining students
            db.rollback()
            failed.append(f"{student.email}: {exc}")

    already_had = db.query(Student).count() - len(students)
    return generated, already_had, failed
