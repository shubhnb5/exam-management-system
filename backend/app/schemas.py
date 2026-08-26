from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str
    exam_center_id: int | None = None


class ExamCenterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    code: str


class TeacherCreate(BaseModel):
    username: str
    password: str
    full_name: str
    exam_center_id: int


class TeacherOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    full_name: str
    exam_center_id: int | None
    is_active: bool


class TeacherUpdate(BaseModel):
    is_active: bool | None = None
    password: str | None = None


class StudentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    full_name: str
    email: str
    mobile_number: str
    exam_center_id: int
    has_ticket: bool = False
    email_status: str | None = None


class UploadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    row_count: int
    new_students: int
    updated_students: int
    error_count: int
    uploaded_at: datetime


class UploadResult(BaseModel):
    upload: UploadOut
    errors: list[str]


class GenerateTicketsResult(BaseModel):
    generated: int
    skipped_existing: int
    failed: list[str]


class SendEmailsResult(BaseModel):
    sent: int
    failed: int
    failures: list[str]


class JobStartedResponse(BaseModel):
    status: str = "started"


class JobStatusResponse(BaseModel):
    status: str  # idle | running | done | error
    result: dict | None = None


class ScanRequest(BaseModel):
    qr_token: str


class ScanSuccess(BaseModel):
    status: str = "ok"
    student_name: str
    exam_center_name: str
    scanned_at: datetime


class ScanConflict(BaseModel):
    status: str = "duplicate"
    student_name: str
    message: str
    original_scan_center: str
    original_scan_teacher: str
    original_scan_time: datetime


class ScanWrongCenter(BaseModel):
    status: str = "wrong_center"
    student_name: str
    message: str
    assigned_center: str
    scanning_center: str


class CenterStats(BaseModel):
    exam_center_id: int
    exam_center_name: str
    total_students: int
    scanned_today: int


class StatsResponse(BaseModel):
    date: date
    centers: list[CenterStats]


class AttendanceRow(BaseModel):
    student_id: int
    full_name: str
    email: str
    exam_center_name: str
    present: bool
    scanned_at: datetime | None = None
    teacher_name: str | None = None


class AttendanceResponse(BaseModel):
    date: date
    rows: list[AttendanceRow]
