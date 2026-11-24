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
    district: str | None = None


class ExamCenterCreate(BaseModel):
    name: str
    district: str = ""


class ExamCenterUpdate(BaseModel):
    name: str
    district: str = ""


class ExamCenterOverview(BaseModel):
    """An exam center with how much depends on it (for the admin's list)."""

    id: int
    name: str
    code: str
    district: str | None = None
    student_count: int
    admit_card_count: int
    teacher_count: int
    scan_count: int
    can_delete: bool


class ExamCenterSaveResult(BaseModel):
    center: ExamCenterOut
    # Admit cards that will show the new name/district (regenerated on next view).
    admit_cards_updated: int = 0


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


class StudentCreate(BaseModel):
    full_name: str
    email: str
    mobile_number: str
    exam_center_id: int | None = None
    generate_admit_card: bool = True


class StudentUpdate(BaseModel):
    full_name: str
    email: str
    mobile_number: str
    exam_center_id: int | None = None


class StudentSaveResult(BaseModel):
    student: StudentOut
    # Add: whether the admit card was generated now (if requested).
    ticket_generated: bool = False
    ticket_error: str | None = None
    # Edit: changes to details printed on an existing admit card (it was updated).
    ticket_changes: list[str] = []


class UploadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    filename: str
    row_count: int
    new_students: int
    updated_students: int
    error_count: int
    uploaded_at: datetime


class UploadProblem(BaseModel):
    """One skipped row, shown to the admin as a table row."""

    row: int
    name: str = ""
    email: str = ""
    mobile: str = ""
    reason: str


class TicketRefresh(BaseModel):
    """A student whose already-generated admit card was updated by the upload."""

    student_name: str
    changes: list[str]


class UploadResult(BaseModel):
    upload: UploadOut
    problems: list[UploadProblem]
    refreshed_tickets: list[TicketRefresh]


class DeleteStudentsRequest(BaseModel):
    student_ids: list[int]


class DeleteResult(BaseModel):
    deleted: int


class GenerateTicketsResult(BaseModel):
    generated: int
    skipped_existing: int
    failed: list[str]


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


# --- Student portal ----------------------------------------------------------


class StudentSignupRequest(BaseModel):
    first_name: str
    middle_name: str | None = None
    last_name: str
    email: str
    mobile_number: str
    gender: str
    aadhaar_number: str | None = None
    password: str
    # From POST /student/signup/verify-otp: proves the mobile number was verified.
    mobile_verification_token: str | None = None


class OtpSendRequest(BaseModel):
    mobile_number: str


class FirebaseWebConfig(BaseModel):
    apiKey: str
    authDomain: str
    projectId: str


class OtpSendResponse(BaseModel):
    expires_in_seconds: int
    resend_after_seconds: int
    # True while no real SMS is sent (OTP_PROVIDER=console).
    test_mode: bool
    # Only in test mode with OTP_DEV_ECHO=true, so the OTP can be shown on screen.
    dev_otp: str | None = None
    # "sms": the server sent the OTP (StartMessaging / MSG91 / test mode), verify with /verify-otp.
    # "firebase": the browser must now ask Firebase to send the OTP, then send
    #             the resulting Firebase ID token to /verify-firebase.
    channel: str = "sms"
    firebase: FirebaseWebConfig | None = None


class FirebaseVerifyRequest(BaseModel):
    mobile_number: str
    id_token: str


class OtpVerifyRequest(BaseModel):
    mobile_number: str
    otp: str


class SignupOtpVerifyResponse(BaseModel):
    mobile_verification_token: str
    expires_in_minutes: int


class StudentLoginRequest(BaseModel):
    mobile_number: str
    password: str


class StudentToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    full_name: str


class ForgotPasswordVerifyResponse(BaseModel):
    reset_token: str
    expires_in_minutes: int


class ForgotPasswordResetRequest(BaseModel):
    reset_token: str
    new_password: str


class AdmitCardLink(BaseModel):
    # Path relative to the API base URL, e.g. "/student/admit-card/file?token=..."
    path: str
    expires_in_seconds: int


class AdmitCardStatus(BaseModel):
    # available     -> admit card generated, can be downloaded
    # not_generated -> admin uploaded the student but hasn't generated cards yet
    # not_found     -> no uploaded student with this mobile number
    status: str
    exam_center_name: str | None = None
    generated_at: datetime | None = None
    updated_at: datetime | None = None


class StudentProfile(BaseModel):
    first_name: str
    middle_name: str | None
    last_name: str
    full_name: str
    email: str
    mobile_number: str
    gender: str
    admit_card: AdmitCardStatus


class StudentAccountOut(BaseModel):
    """Admin's view of a registered student account."""

    id: int
    full_name: str
    email: str
    mobile_number: str
    gender: str
    aadhaar_masked: str | None
    created_at: datetime
    admit_card_status: str
    exam_center_name: str | None = None
    mobile_verified: bool = False
