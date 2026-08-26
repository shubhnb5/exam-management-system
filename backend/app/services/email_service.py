import smtplib
from datetime import datetime, timezone
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from app.config import settings
from app.models import EmailLog, HallTicket, Student
from app.services.ticket_files import ensure_ticket_pdf_on_disk

MAX_ATTEMPTS = 3


def _connect_smtp() -> smtplib.SMTP:
    server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30)
    server.starttls()
    server.login(settings.smtp_username, settings.smtp_app_password)
    return server


def _build_message(student: Student, pdf_path: str) -> MIMEMultipart:
    msg = MIMEMultipart()
    msg["From"] = f"{settings.smtp_from_name} <{settings.smtp_username}>"
    msg["To"] = student.email
    msg["Subject"] = "Your Hall Ticket"

    msg.attach(
        MIMEText(
            f"Dear {student.full_name},\n\n"
            "Please find your hall ticket attached. Print it and bring it to your exam center.\n\n"
            "Best of luck!",
            "plain",
        )
    )

    with open(pdf_path, "rb") as f:
        part = MIMEApplication(f.read(), _subtype="pdf")
    part.add_header("Content-Disposition", "attachment", filename=f"hall_ticket_{student.full_name}.pdf")
    msg.attach(part)
    return msg


def send_all_pending_emails(db: Session) -> tuple[int, int, list[str]]:
    """Sends every pending/failed-but-retryable student's hall ticket email.

    Reuses a single SMTP connection across the whole batch instead of
    reconnecting per email — with hundreds of students, per-email connect
    overhead alone was pushing this well past what a web request (or most
    hosting platforms' request timeouts) can tolerate. The connection is
    re-established automatically if the server drops an idle link mid-batch.
    """
    students = (
        db.query(Student)
        .join(HallTicket)
        .filter(
            ~Student.email_logs.any(EmailLog.status == "sent"),
        )
        .all()
    )

    sent = 0
    failed = 0
    failures: list[str] = []
    server: smtplib.SMTP | None = None

    try:
        for student in students:
            log = db.query(EmailLog).filter(EmailLog.student_id == student.id).order_by(EmailLog.id.desc()).first()
            if log is None:
                log = EmailLog(student_id=student.id, status="pending", attempt_count=0)
                db.add(log)
                db.commit()  # committed on its own so it survives a rollback below if sending fails
                db.refresh(log)

            if log.attempt_count >= MAX_ATTEMPTS:
                continue

            try:
                pdf_path = ensure_ticket_pdf_on_disk(student)
                msg = _build_message(student, pdf_path)

                if server is None:
                    server = _connect_smtp()
                try:
                    server.sendmail(settings.smtp_username, [student.email], msg.as_string())
                except (smtplib.SMTPServerDisconnected, smtplib.SMTPSenderRefused, OSError):
                    # Connection dropped mid-batch (idle timeout etc) — reconnect once and retry this student.
                    server = _connect_smtp()
                    server.sendmail(settings.smtp_username, [student.email], msg.as_string())

                log.status = "sent"
                log.error_message = None
                log.attempt_count += 1
                log.sent_at = datetime.now(timezone.utc)
                db.commit()
                sent += 1
            except Exception as exc:  # noqa: BLE001 - keep sending remaining students
                db.rollback()
                log = db.get(EmailLog, log.id)
                log.status = "failed"
                log.error_message = str(exc)
                log.attempt_count += 1
                db.commit()
                failed += 1
                failures.append(f"{student.email}: {exc}")
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:  # noqa: BLE001
                pass

    return sent, failed, failures
