import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.database import SessionLocal
from app.models import HallTicket
from app.services.pdf_generator import TicketConfig, generate_hall_ticket_pdf
from app.services.ticket_files import CONFIG_PATH

if __name__ == "__main__":
    db = SessionLocal()
    config = TicketConfig.load(CONFIG_PATH)
    tickets = db.query(HallTicket).all()
    total = len(tickets)
    failed = []

    for i, ticket in enumerate(tickets, 1):
        student = ticket.student
        try:
            generate_hall_ticket_pdf(
                output_path=ticket.pdf_path,
                student_name=student.full_name,
                mobile_number=student.mobile_number,
                exam_center_name=student.exam_center.name,
                qr_token=ticket.qr_token,
                config=config,
            )
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{student.email}: {exc}")
        if i % 100 == 0 or i == total:
            print(f"{i}/{total}")

    print(f"done. failed={len(failed)}")
    for f in failed[:20]:
        print(" -", f)
