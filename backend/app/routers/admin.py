from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.job_status import fail_job, get_job, is_running, start_job, finish_job
from app.models import EmailLog, ExamCenter, Scan, Student, Upload, User
from app.schemas import (
    AttendanceResponse,
    AttendanceRow,
    CenterStats,
    DeleteResult,
    DeleteStudentsRequest,
    ExamCenterOut,
    JobStartedResponse,
    JobStatusResponse,
    StatsResponse,
    StudentOut,
    TeacherCreate,
    TeacherOut,
    TeacherUpdate,
    UploadOut,
    UploadResult,
)
from app.security import hash_password, require_admin
from app.services.email_service import send_all_pending_emails
from app.services.excel_import import import_students_excel
from app.services.student_deletion import delete_all_students, delete_students
from app.services.ticket_batch import generate_tickets_for_all
from app.services.ticket_files import ensure_ticket_pdf_on_disk
from app.timeutils import ist_today

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/students/upload", response_model=UploadResult)
def upload_students(
    file: UploadFile = File(...),
    exam_center_id: int = Form(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if not file.filename.lower().endswith((".xlsx", ".xlsm", ".csv", ".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Please upload a .xlsx, .xlsm, .csv, .pdf, or .docx file")
    content = file.file.read()
    try:
        upload, errors = import_students_excel(db, content, file.filename, admin.id, exam_center_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return UploadResult(upload=UploadOut.model_validate(upload), errors=errors)


@router.get("/uploads", response_model=list[UploadOut])
def list_uploads(db: Session = Depends(get_db)):
    return db.query(Upload).order_by(Upload.uploaded_at.desc()).all()


def _run_generate_job() -> None:
    db = SessionLocal()
    try:
        generated, skipped, failed = generate_tickets_for_all(db)
        finish_job("generate", {"generated": generated, "skipped_existing": skipped, "failed": failed})
    except Exception as exc:  # noqa: BLE001
        fail_job("generate", str(exc))
    finally:
        db.close()


def _run_send_emails_job() -> None:
    db = SessionLocal()
    try:
        sent, failed, failures = send_all_pending_emails(db)
        finish_job("send_emails", {"sent": sent, "failed": failed, "failures": failures})
    except Exception as exc:  # noqa: BLE001
        fail_job("send_emails", str(exc))
    finally:
        db.close()


@router.post("/tickets/generate", response_model=JobStartedResponse)
def generate_tickets(background_tasks: BackgroundTasks):
    # Generating (and especially emailing) hundreds of tickets synchronously
    # can take minutes — far longer than most hosting platforms' HTTP request
    # timeouts allow — so this runs in the background and the frontend polls
    # /tickets/generate/status instead of waiting on this request.
    if is_running("generate"):
        raise HTTPException(status_code=409, detail="A ticket generation job is already running.")
    start_job("generate")
    background_tasks.add_task(_run_generate_job)
    return JobStartedResponse()


@router.get("/tickets/generate/status", response_model=JobStatusResponse)
def generate_tickets_status():
    return get_job("generate")


@router.post("/tickets/send-emails", response_model=JobStartedResponse)
def send_emails(background_tasks: BackgroundTasks):
    if is_running("send_emails"):
        raise HTTPException(status_code=409, detail="An email sending job is already running.")
    start_job("send_emails")
    background_tasks.add_task(_run_send_emails_job)
    return JobStartedResponse()


@router.get("/tickets/send-emails/status", response_model=JobStatusResponse)
def send_emails_status():
    return get_job("send_emails")


@router.get("/students", response_model=list[StudentOut])
def list_students(db: Session = Depends(get_db)):
    students = db.query(Student).all()
    result = []
    for s in students:
        latest_log = db.query(EmailLog).filter(EmailLog.student_id == s.id).order_by(EmailLog.id.desc()).first()
        result.append(
            StudentOut(
                id=s.id,
                full_name=s.full_name,
                email=s.email,
                mobile_number=s.mobile_number,
                exam_center_id=s.exam_center_id,
                has_ticket=s.hall_ticket is not None,
                email_status=latest_log.status if latest_log else None,
            )
        )
    return result


@router.delete("/students", response_model=DeleteResult)
def delete_all_students_endpoint(db: Session = Depends(get_db)):
    return DeleteResult(deleted=delete_all_students(db))


@router.post("/students/delete", response_model=DeleteResult)
def delete_students_endpoint(payload: DeleteStudentsRequest, db: Session = Depends(get_db)):
    return DeleteResult(deleted=delete_students(db, payload.student_ids))


@router.delete("/students/{student_id}", response_model=DeleteResult)
def delete_student_endpoint(student_id: int, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return DeleteResult(deleted=delete_students(db, [student_id]))


@router.get("/students/{student_id}/ticket")
def download_ticket(student_id: int, db: Session = Depends(get_db)):
    student = db.get(Student, student_id)
    if student is None or student.hall_ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No ticket generated for this student")
    pdf_path = ensure_ticket_pdf_on_disk(student)
    return FileResponse(
        pdf_path,
        media_type="application/pdf",
        filename=f"hall_ticket_{student.full_name}.pdf",
        headers={"Cache-Control": "no-store"},
    )


@router.get("/exam-centers", response_model=list[ExamCenterOut])
def list_exam_centers(db: Session = Depends(get_db)):
    return db.query(ExamCenter).all()


@router.get("/stats", response_model=StatsResponse)
def stats(target_date: date | None = Query(default=None, alias="date"), db: Session = Depends(get_db)):
    target_date = target_date or ist_today()
    centers = db.query(ExamCenter).all()
    center_stats = []
    for c in centers:
        total = db.query(Student).filter(Student.exam_center_id == c.id).count()
        scanned = (
            db.query(Scan)
            .filter(Scan.exam_center_id == c.id, Scan.scan_date == target_date)
            .count()
        )
        center_stats.append(
            CenterStats(exam_center_id=c.id, exam_center_name=c.name, total_students=total, scanned_today=scanned)
        )
    return StatsResponse(date=target_date, centers=center_stats)


@router.get("/attendance", response_model=AttendanceResponse)
def attendance(target_date: date | None = Query(default=None, alias="date"), db: Session = Depends(get_db)):
    target_date = target_date or ist_today()
    students = db.query(Student).all()
    scans_by_student = {
        s.student_id: s for s in db.query(Scan).filter(Scan.scan_date == target_date).all()
    }

    rows = []
    for student in students:
        scan = scans_by_student.get(student.id)
        rows.append(
            AttendanceRow(
                student_id=student.id,
                full_name=student.full_name,
                email=student.email,
                exam_center_name=student.exam_center.name,
                present=scan is not None,
                scanned_at=scan.scanned_at if scan else None,
                teacher_name=scan.teacher.full_name if scan else None,
            )
        )
    return AttendanceResponse(date=target_date, rows=rows)


@router.post("/teachers", response_model=TeacherOut)
def create_teacher(payload: TeacherCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already exists")
    center = db.get(ExamCenter, payload.exam_center_id)
    if center is None:
        raise HTTPException(status_code=400, detail="Unknown exam center")

    teacher = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        role="teacher",
        exam_center_id=payload.exam_center_id,
        is_active=True,
    )
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return teacher


@router.get("/teachers", response_model=list[TeacherOut])
def list_teachers(db: Session = Depends(get_db)):
    return db.query(User).filter(User.role == "teacher").all()


@router.patch("/teachers/{teacher_id}", response_model=TeacherOut)
def update_teacher(teacher_id: int, payload: TeacherUpdate, db: Session = Depends(get_db)):
    teacher = db.query(User).filter(User.id == teacher_id, User.role == "teacher").first()
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    if payload.is_active is not None:
        teacher.is_active = payload.is_active
    if payload.password:
        teacher.password_hash = hash_password(payload.password)
    db.commit()
    db.refresh(teacher)
    return teacher


@router.delete("/teachers/{teacher_id}", response_model=DeleteResult)
def delete_teacher_endpoint(teacher_id: int, db: Session = Depends(get_db)):
    teacher = db.query(User).filter(User.id == teacher_id, User.role == "teacher").first()
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    if db.query(Scan).filter(Scan.teacher_id == teacher_id).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This teacher has attendance scan history and can't be deleted — revoke their access instead.",
        )
    db.delete(teacher)
    db.commit()
    return DeleteResult(deleted=1)
