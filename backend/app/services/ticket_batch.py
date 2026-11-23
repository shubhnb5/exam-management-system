from sqlalchemy.orm import Session, joinedload

from app.models import Student
from app.services.pdf_generator import TicketConfig
from app.services.student_records import create_ticket_for_student
from app.services.ticket_files import CONFIG_PATH

# Commit in batches rather than once per student — a commit is a network
# round-trip plus an fsync on the DB side, so committing after every single
# ticket dominated total batch time once there were more than a handful of
# students. Batching still keeps each student's work isolated in its own
# SAVEPOINT (see below), so one bad student can't affect any other, and a
# crash mid-batch only re-queues the students in the not-yet-committed
# batch — generate_tickets_for_all already only processes students without a
# hall ticket, so simply re-running it picks up exactly where it left off.
COMMIT_BATCH_SIZE = 50


def generate_tickets_for_all(db: Session) -> tuple[int, int, list[str]]:
    """Generates a hall ticket + QR for every student who doesn't already have
    one. Existing tickets are left untouched so re-running after a fresh
    Excel upload only produces tickets for newly added students."""
    config = TicketConfig.load(CONFIG_PATH)
    students = (
        db.query(Student)
        .filter(Student.hall_ticket == None)  # noqa: E711
        .options(joinedload(Student.exam_center))
        .all()
    )

    generated = 0
    failed: list[str] = []

    for student in students:
        try:
            with db.begin_nested():
                create_ticket_for_student(db, student, config)
            generated += 1
        except Exception as exc:  # noqa: BLE001 - keep processing remaining students
            failed.append(f"{student.email}: {exc}")

        if generated % COMMIT_BATCH_SIZE == 0:
            db.commit()

    db.commit()

    already_had = db.query(Student).count() - len(students)
    return generated, already_had, failed
