from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class ExamCenter(Base):
    __tablename__ = "exam_centers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    # District printed on admit cards (जिल्हा केंद्र). Required when adding or
    # editing a center; nullable only for centers created before it existed.
    district: Mapped[str | None] = mapped_column(String, nullable=True)

    students: Mapped[list["Student"]] = relationship(back_populates="exam_center")
    users: Mapped[list["User"]] = relationship(back_populates="exam_center")
    time_slots: Mapped[list["ExamCenterTimeSlot"]] = relationship(
        back_populates="exam_center", order_by="ExamCenterTimeSlot.id"
    )


class ExamCenterTimeSlot(Base):
    """A custom exam timing for one center: the three timetable columns
    उपकेंद्रावरील उपस्थिती (reporting), परीक्षा कक्षातील शेवटच्या प्रवेशाची वेळ
    (last_entry) and परीक्षेचा प्रत्यक्ष कालावधी (duration), printed for every
    exam date. A center can have several (e.g. different batches on the same
    day); the slot is chosen per uploaded sheet. Students without a slot get
    the default timing from ticket_template/config.json."""

    __tablename__ = "exam_center_time_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    exam_center_id: Mapped[int] = mapped_column(ForeignKey("exam_centers.id"), nullable=False, index=True)
    reporting: Mapped[str] = mapped_column(String, nullable=False)
    last_entry: Mapped[str] = mapped_column(String, nullable=False)
    duration: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    exam_center: Mapped[ExamCenter] = relationship(back_populates="time_slots")


class User(Base):
    """Unified login for admin + teachers. Teachers get one fixed account each;
    revoking a lost device is just flipping is_active to False."""

    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('admin', 'teacher')", name="ck_users_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    role: Mapped[str] = mapped_column(String, nullable=False)
    exam_center_id: Mapped[int | None] = mapped_column(ForeignKey("exam_centers.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    exam_center: Mapped[ExamCenter | None] = relationship(back_populates="users")
    scans: Mapped[list["Scan"]] = relationship(back_populates="teacher")


class Student(Base):
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    full_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    # Stored normalized to 10 digits (see app.validators.normalize_mobile);
    # this is what links a roster entry to a student portal account.
    mobile_number: Mapped[str] = mapped_column(String, nullable=False, index=True)
    exam_center_id: Mapped[int] = mapped_column(ForeignKey("exam_centers.id"), nullable=False)
    # Custom exam timing (a slot of the student's own center), set from the
    # upload / Add-Edit Student form. NULL = default timing from config.json.
    time_slot_id: Mapped[int | None] = mapped_column(ForeignKey("exam_center_time_slots.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    exam_center: Mapped[ExamCenter] = relationship(back_populates="students")
    time_slot: Mapped["ExamCenterTimeSlot | None"] = relationship()
    hall_ticket: Mapped["HallTicket | None"] = relationship(back_populates="student", uselist=False)
    scans: Mapped[list["Scan"]] = relationship(back_populates="student")
    email_logs: Mapped[list["EmailLog"]] = relationship(back_populates="student")


class HallTicket(Base):
    __tablename__ = "hall_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), unique=True, nullable=False)
    qr_token: Mapped[str] = mapped_column(String, unique=True, nullable=False, index=True)
    pdf_path: Mapped[str] = mapped_column(String, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Set whenever a re-upload changes the details printed on the ticket (name,
    # mobile, center). The on-disk PDF is regenerated if it is older than this,
    # so students always download the current version. The QR token never
    # changes, so already-printed tickets keep scanning correctly.
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # The custom timing printed on this card, copied from the student's time
    # slot when the card is generated (or when the student is moved to another
    # slot). A copy, not a link: editing a slot later only affects cards
    # generated afterwards. NULL = default timing from config.json.
    timing_reporting: Mapped[str | None] = mapped_column(String, nullable=True)
    timing_last_entry: Mapped[str | None] = mapped_column(String, nullable=True)
    timing_duration: Mapped[str | None] = mapped_column(String, nullable=True)

    student: Mapped[Student] = relationship(back_populates="hall_ticket")


class EmailLog(Base):
    """Legacy: history of the removed "Send Emails" feature. Nothing writes to
    this table any more; it is kept so existing history isn't destroyed and is
    still cleaned up when students are deleted."""

    __tablename__ = "email_log"
    __table_args__ = (CheckConstraint("status IN ('pending', 'sent', 'failed')", name="ck_email_log_status"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    student: Mapped[Student] = relationship(back_populates="email_logs")


class Scan(Base):
    """Race-safety comes from the DB, not application code: the unique
    constraint on (student_id, scan_date) means Postgres itself rejects a
    second scan for the same student on the same calendar day, even if two
    inserts land in the same instant from different devices."""

    __tablename__ = "scans"
    __table_args__ = (UniqueConstraint("student_id", "scan_date", name="uq_scans_student_day"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    exam_center_id: Mapped[int] = mapped_column(ForeignKey("exam_centers.id"), nullable=False)
    scan_date: Mapped[date] = mapped_column(Date, nullable=False, server_default=func.current_date())
    scanned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    student: Mapped[Student] = relationship(back_populates="scans")
    teacher: Mapped[User] = relationship(back_populates="scans")
    exam_center: Mapped[ExamCenter] = relationship()


class Upload(Base):
    """Audit trail for each Excel import, shown on the admin dashboard."""

    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    row_count: Mapped[int] = mapped_column(Integer, nullable=False)
    new_students: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_students: Mapped[int] = mapped_column(Integer, nullable=False)
    error_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class StudentAccount(Base):
    """A self-registered student login for the student portal. Deliberately
    separate from `Student` (the admin-uploaded exam roster): a student may
    register before or after the admin uploads them. The two are linked by the
    normalized 10-digit mobile number, which is unique per account."""

    __tablename__ = "student_accounts"
    __table_args__ = (
        CheckConstraint("gender IN ('male', 'female', 'other')", name="ck_student_accounts_gender"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String, nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String, nullable=True)
    last_name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    mobile_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    gender: Mapped[str] = mapped_column(String, nullable=False)
    # Aadhaar is never stored in plain text: the encrypted value is for
    # display (masked) to the admin, the keyed hash enforces uniqueness
    # without having to decrypt every row.
    aadhaar_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    aadhaar_hash: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    # Embedded in every token issued to this account; changing the password
    # bumps it, which invalidates older sessions and used reset tokens.
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    # Set when the mobile number was proven by OTP (at signup or password
    # reset). Accounts created before OTP existed have NULL and still work.
    mobile_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def full_name(self) -> str:
        return " ".join(p for p in (self.first_name, self.middle_name, self.last_name) if p)


class OtpCode(Base):
    """One-time passwords sent by SMS. Only a keyed hash of the code is stored;
    a code is single-use, expires after a few minutes and allows a limited
    number of wrong guesses. Rows also drive the per-number send limits."""

    __tablename__ = "otp_codes"
    __table_args__ = (
        CheckConstraint("purpose IN ('signup', 'reset')", name="ck_otp_codes_purpose"),
        Index("ix_otp_codes_mobile_purpose_created", "mobile_number", "purpose", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    mobile_number: Mapped[str] = mapped_column(String, nullable=False)
    purpose: Mapped[str] = mapped_column(String, nullable=False)
    code_hash: Mapped[str] = mapped_column(String, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
