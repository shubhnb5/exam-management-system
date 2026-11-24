from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal, get_db
from app.http_errors import field_conflicts, field_errors
from app.job_status import fail_job, finish_job, get_job, try_start_job
from app import field_crypto
from sqlalchemy import func

from app.models import ExamCenter, HallTicket, Scan, Student, StudentAccount, Upload, User
from app.schemas import (
    AttendanceResponse,
    AttendanceRow,
    CenterStats,
    DeleteResult,
    DeleteStudentsRequest,
    ExamCenterCreate,
    ExamCenterOut,
    ExamCenterOverview,
    ExamCenterSaveResult,
    ExamCenterUpdate,
    JobStartedResponse,
    JobStatusResponse,
    StatsResponse,
    StudentAccountOut,
    StudentCreate,
    StudentOut,
    StudentSaveResult,
    StudentUpdate,
    TeacherCreate,
    TeacherOut,
    TeacherUpdate,
    UploadOut,
    UploadResult,
)
from app.security import hash_password, require_admin
from app.services.admit_card_lookup import admit_card_status, roster_by_mobile
from app.services.excel_import import import_students_excel
from app.services.student_deletion import delete_all_students, delete_students
from app.services.student_records import (
    create_ticket_for_student,
    mark_ticket_outdated,
    ticket_changes,
    validate_student_input,
)
from app.services.ticket_batch import generate_tickets_for_all
from app.services.ticket_files import discard_ticket_pdf, ensure_ticket_pdf_on_disk
from app.timeutils import ist_today
from app.validators import canonical_district, clean_name, mask_aadhaar

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _run_upload_job(content: bytes, filename: str, admin_id: int, exam_center_id: int) -> None:
    db = SessionLocal()
    try:
        upload, problems, refreshed = import_students_excel(db, content, filename, admin_id, exam_center_id)
        result = UploadResult(upload=UploadOut.model_validate(upload), problems=problems, refreshed_tickets=refreshed)
        finish_job("upload", result.model_dump(mode="json"))
    except ValueError as exc:  # a problem with the file itself (missing columns, empty, ...)
        fail_job("upload", str(exc))
    except Exception as exc:  # noqa: BLE001
        fail_job("upload", f"Upload failed: {exc}")
    finally:
        db.close()


@router.post("/students/upload", response_model=JobStartedResponse, status_code=status.HTTP_202_ACCEPTED)
def upload_students(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    exam_center_id: int = Form(...),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Starts processing an uploaded sheet in the background; poll
    /students/upload/status for the result. A 5000-row PDF takes close to a
    minute to read (PDF table extraction is slow), which would otherwise hit
    the reverse proxy's request timeout."""
    if not file.filename.lower().endswith((".xlsx", ".xlsm", ".csv", ".pdf", ".docx")):
        raise HTTPException(status_code=400, detail="Please upload a .xlsx, .xlsm, .csv, .pdf, or .docx file")
    if db.get(ExamCenter, exam_center_id) is None:
        raise HTTPException(status_code=400, detail="Unknown exam center.")
    content = file.file.read()
    if not try_start_job("upload"):
        raise HTTPException(status_code=409, detail="Another upload is still being processed. Please wait for it to finish.")
    background_tasks.add_task(_run_upload_job, content, file.filename, admin.id, exam_center_id)
    return JobStartedResponse()


@router.get("/students/upload/status", response_model=JobStatusResponse)
def upload_students_status():
    """status: idle | running | done (result = UploadResult) | error (result = {"error": message})"""
    return get_job("upload")


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


@router.post("/tickets/generate", response_model=JobStartedResponse)
def generate_tickets(background_tasks: BackgroundTasks):
    # Generating hundreds of tickets synchronously
    # can take minutes — far longer than most hosting platforms' HTTP request
    # timeouts allow — so this runs in the background and the frontend polls
    # /tickets/generate/status instead of waiting on this request.
    if not try_start_job("generate"):
        raise HTTPException(status_code=409, detail="A ticket generation job is already running.")
    background_tasks.add_task(_run_generate_job)
    return JobStartedResponse()


@router.get("/tickets/generate/status", response_model=JobStatusResponse)
def generate_tickets_status():
    return get_job("generate")


def _student_out(s: Student) -> StudentOut:
    return StudentOut(
        id=s.id,
        full_name=s.full_name,
        email=s.email,
        mobile_number=s.mobile_number,
        exam_center_id=s.exam_center_id,
        has_ticket=s.hall_ticket is not None,
    )


@router.get("/students", response_model=list[StudentOut])
def list_students(db: Session = Depends(get_db)):
    students = db.query(Student).options(joinedload(Student.hall_ticket)).all()
    return [_student_out(s) for s in students]


def _validated(db: Session, payload, student_id: int | None = None) -> dict:
    values, errors, conflicts = validate_student_input(
        db,
        full_name=payload.full_name,
        email=payload.email,
        mobile_number=payload.mobile_number,
        exam_center_id=payload.exam_center_id,
        student_id=student_id,
    )
    if errors:
        raise field_errors(errors)
    if conflicts:
        raise field_conflicts(conflicts)
    return values


def _commit_or_conflict(db: Session) -> None:
    # The checks above give friendly messages; the unique email constraint is
    # the real guarantee if two saves race each other.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise field_conflicts({"email": "This email already belongs to another student."})


@router.post("/students", response_model=StudentSaveResult, status_code=status.HTTP_201_CREATED)
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    """Adds one student by hand — e.g. someone missed from an uploaded sheet —
    and optionally generates their admit card straight away."""
    values = _validated(db, payload)
    student = Student(
        full_name=values["full_name"],
        email=values["email"],
        mobile_number=values["mobile_number"],
        exam_center_id=values["center"].id,
    )
    db.add(student)
    _commit_or_conflict(db)
    db.refresh(student)

    result = StudentSaveResult(student=_student_out(student))
    if payload.generate_admit_card:
        try:
            create_ticket_for_student(db, student)
            db.commit()
            result.ticket_generated = True
        except Exception as exc:  # noqa: BLE001 - the student is saved either way
            db.rollback()
            result.ticket_error = (
                f"Student saved, but the admit card could not be generated ({exc}). "
                "Use Generate Admit Cards to try again."
            )
        db.refresh(student)
        result.student = _student_out(student)
    return result


@router.put("/students/{student_id}", response_model=StudentSaveResult)
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db)):
    """Corrects one student's details. If the details printed on an existing
    admit card change, the card is regenerated (same QR token)."""
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    values = _validated(db, payload, student_id=student_id)

    changes = ticket_changes(student, values["full_name"], values["mobile_number"], values["center"])
    stale_pdf = mark_ticket_outdated(student) if changes else None
    student.full_name = values["full_name"]
    student.email = values["email"]
    student.mobile_number = values["mobile_number"]
    student.exam_center_id = values["center"].id
    _commit_or_conflict(db)
    if stale_pdf:
        discard_ticket_pdf(stale_pdf)
    db.refresh(student)

    return StudentSaveResult(
        student=_student_out(student),
        ticket_changes=changes if student.hall_ticket is not None else [],
    )


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
    return db.query(ExamCenter).order_by(ExamCenter.id).all()


def _next_center_code(existing_codes: set[str]) -> str:
    """CENTER_A, CENTER_B, ... CENTER_Z, CENTER_AA, ... — continues the
    naming of the two seeded centers."""
    n = 0
    while True:
        n += 1
        letters, k = "", n
        while k:
            k, rem = divmod(k - 1, 26)
            letters = chr(ord("A") + rem) + letters
        code = f"CENTER_{letters}"
        if code not in existing_codes:
            return code


def _valid_center_name(db: Session, raw: str, exclude_id: int | None = None) -> str:
    name = clean_name(raw)
    if len(name) < 3:
        raise HTTPException(status_code=400, detail="Exam center name must be at least 3 characters.")
    if len(name) > 200:
        raise HTTPException(status_code=400, detail="Exam center name must be at most 200 characters.")
    others = db.query(ExamCenter).filter(ExamCenter.id != exclude_id) if exclude_id else db.query(ExamCenter)
    if any(clean_name(c.name).casefold() == name.casefold() for c in others.all()):
        raise HTTPException(status_code=409, detail="An exam center with this name already exists.")
    return name


def _valid_district(raw: str) -> str:
    district = canonical_district(raw)
    if district is None:
        raise HTTPException(status_code=400, detail="Please select the district of the exam center.")
    return district


@router.post("/exam-centers", response_model=ExamCenterOut, status_code=status.HTTP_201_CREATED)
def create_exam_center(payload: ExamCenterCreate, db: Session = Depends(get_db)):
    name = _valid_center_name(db, payload.name)
    district = _valid_district(payload.district)
    centers = db.query(ExamCenter).all()

    center = ExamCenter(name=name, code=_next_center_code({c.code for c in centers}), district=district)
    db.add(center)
    db.commit()
    db.refresh(center)
    return center


def _count_by_center(db: Session, column) -> dict[int, int]:
    return {cid: n for cid, n in db.query(column, func.count()).group_by(column).all()}


@router.get("/exam-centers/overview", response_model=list[ExamCenterOverview])
def exam_centers_overview(db: Session = Depends(get_db)):
    students = _count_by_center(db, Student.exam_center_id)
    teachers = _count_by_center(db, User.exam_center_id)
    scans = _count_by_center(db, Scan.exam_center_id)
    cards = {
        cid: n
        for cid, n in db.query(Student.exam_center_id, func.count())
        .join(HallTicket, HallTicket.student_id == Student.id)
        .group_by(Student.exam_center_id)
        .all()
    }
    result = []
    for c in db.query(ExamCenter).order_by(ExamCenter.id).all():
        s, t, sc = students.get(c.id, 0), teachers.get(c.id, 0), scans.get(c.id, 0)
        result.append(
            ExamCenterOverview(
                id=c.id,
                name=c.name,
                code=c.code,
                district=c.district,
                student_count=s,
                admit_card_count=cards.get(c.id, 0),
                teacher_count=t,
                scan_count=sc,
                can_delete=s == 0 and t == 0 and sc == 0,
            )
        )
    return result


@router.put("/exam-centers/{center_id}", response_model=ExamCenterSaveResult)
def update_exam_center(center_id: int, payload: ExamCenterUpdate, db: Session = Depends(get_db)):
    """Renames a center / changes its district. Admit cards of its students
    show the change from their next view/download (same QR code, so printed
    cards still scan)."""
    center = db.get(ExamCenter, center_id)
    if center is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam center not found")
    name = _valid_center_name(db, payload.name, exclude_id=center_id)
    district = _valid_district(payload.district)

    stale_pdfs: list[str] = []
    if name != center.name or district != center.district:
        students = (
            db.query(Student)
            .options(joinedload(Student.hall_ticket))
            .filter(Student.exam_center_id == center_id)
            .all()
        )
        for student in students:
            pdf = mark_ticket_outdated(student)
            if pdf:
                stale_pdfs.append(pdf)
        center.name = name
        center.district = district
    db.commit()
    for pdf in stale_pdfs:
        discard_ticket_pdf(pdf)
    db.refresh(center)
    return ExamCenterSaveResult(center=ExamCenterOut.model_validate(center), admit_cards_updated=len(stale_pdfs))


@router.delete("/exam-centers/{center_id}", response_model=DeleteResult)
def delete_exam_center(center_id: int, db: Session = Depends(get_db)):
    """Deletes a center only when nothing uses it: no students, no teacher
    accounts and no attendance history — so nothing is ever lost by accident."""
    center = db.get(ExamCenter, center_id)
    if center is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam center not found")
    students = db.query(Student).filter(Student.exam_center_id == center_id).count()
    teachers = db.query(User).filter(User.exam_center_id == center_id).count()
    scans = db.query(Scan).filter(Scan.exam_center_id == center_id).count()
    if students or teachers or scans:
        parts = []
        if students:
            parts.append(f"{students} student{'s' if students != 1 else ''}")
        if teachers:
            parts.append(f"{teachers} teacher account{'s' if teachers != 1 else ''}")
        if scans:
            parts.append(f"{scans} attendance record{'s' if scans != 1 else ''}")
        hint = (
            " Attendance history is kept permanently, so this center can't be deleted — rename it instead."
            if scans
            else " Move them to another center or delete them first."
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This exam center is still in use ({', '.join(parts)}).{hint}",
        )
    db.delete(center)
    db.commit()
    return DeleteResult(deleted=1)


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


@router.get("/student-accounts", response_model=list[StudentAccountOut])
def list_student_accounts(db: Session = Depends(get_db)):
    accounts = db.query(StudentAccount).order_by(StudentAccount.created_at.desc()).all()
    roster = roster_by_mobile(db, [a.mobile_number for a in accounts])

    result = []
    for a in accounts:
        aadhaar = field_crypto.decrypt(a.aadhaar_encrypted) if a.aadhaar_encrypted else None
        card = admit_card_status(roster.get(a.mobile_number))
        result.append(
            StudentAccountOut(
                id=a.id,
                full_name=a.full_name,
                email=a.email,
                mobile_number=a.mobile_number,
                gender=a.gender,
                aadhaar_masked=mask_aadhaar(aadhaar) if aadhaar else None,
                created_at=a.created_at,
                admit_card_status=card.status,
                exam_center_name=card.exam_center_name,
                mobile_verified=a.mobile_verified_at is not None,
            )
        )
    return result


@router.delete("/student-accounts/{account_id}", response_model=DeleteResult)
def delete_student_account(account_id: int, db: Session = Depends(get_db)):
    """Removes a portal login only — the uploaded student record, admit card
    and attendance are untouched. Frees the mobile number so the right person
    can register with it."""
    account = db.get(StudentAccount, account_id)
    if account is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student account not found")
    db.delete(account)
    db.commit()
    return DeleteResult(deleted=1)
