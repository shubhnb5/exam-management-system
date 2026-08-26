import os

from sqlalchemy.orm import Session

from app.models import EmailLog, HallTicket, Scan, Student


def delete_students(db: Session, student_ids: list[int]) -> int:
    """Deletes the given students along with their hall ticket (DB row + PDF
    on disk), email history, and scan records — there are no DB-level cascade
    rules on these foreign keys, so the child rows have to go first."""
    if not student_ids:
        return 0

    tickets = db.query(HallTicket).filter(HallTicket.student_id.in_(student_ids)).all()
    for ticket in tickets:
        try:
            os.remove(ticket.pdf_path)
        except OSError:
            pass

    db.query(EmailLog).filter(EmailLog.student_id.in_(student_ids)).delete(synchronize_session=False)
    db.query(Scan).filter(Scan.student_id.in_(student_ids)).delete(synchronize_session=False)
    db.query(HallTicket).filter(HallTicket.student_id.in_(student_ids)).delete(synchronize_session=False)
    deleted = db.query(Student).filter(Student.id.in_(student_ids)).delete(synchronize_session=False)
    db.commit()
    return deleted


def delete_all_students(db: Session) -> int:
    ids = [row[0] for row in db.query(Student.id).all()]
    return delete_students(db, ids)
