from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
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

    students: Mapped[list["Student"]] = relationship(back_populates="exam_center")
    users: Mapped[list["User"]] = relationship(back_populates="exam_center")


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
    mobile_number: Mapped[str] = mapped_column(String, nullable=False)
    exam_center_id: Mapped[int] = mapped_column(ForeignKey("exam_centers.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    exam_center: Mapped[ExamCenter] = relationship(back_populates="students")
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

    student: Mapped[Student] = relationship(back_populates="hall_ticket")


class EmailLog(Base):
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
