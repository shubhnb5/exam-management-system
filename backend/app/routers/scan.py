from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import HallTicket, Scan, User
from app.schemas import ScanConflict, ScanRequest, ScanSuccess, ScanWrongCenter
from app.security import require_teacher
from app.timeutils import ist_today

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("", response_model=ScanSuccess, responses={403: {"model": ScanWrongCenter}, 409: {"model": ScanConflict}})
def scan_qr(
    payload: ScanRequest,
    db: Session = Depends(get_db),
    teacher: User = Depends(require_teacher),
):
    ticket = db.query(HallTicket).filter(HallTicket.qr_token == payload.qr_token).first()
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="QR code not recognized")

    student = ticket.student
    today = ist_today()

    if student.exam_center_id != teacher.exam_center_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=ScanWrongCenter(
                student_name=student.full_name,
                message="This student is assigned to a different exam center.",
                assigned_center=student.exam_center.name,
                scanning_center=teacher.exam_center.name,
            ).model_dump(mode="json"),
        )

    scan = Scan(
        student_id=student.id,
        teacher_id=teacher.id,
        exam_center_id=teacher.exam_center_id,
        scan_date=today,
    )
    db.add(scan)
    try:
        db.commit()
    except IntegrityError:
        # The unique constraint on (student_id, scan_date) is what actually
        # prevents a double-scan under concurrent requests from different
        # devices; this except block only handles reporting it back clearly.
        db.rollback()
        existing = (
            db.query(Scan)
            .filter(Scan.student_id == student.id, Scan.scan_date == today)
            .first()
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=ScanConflict(
                student_name=student.full_name,
                message="This student has already been scanned today.",
                original_scan_center=existing.exam_center.name,
                original_scan_teacher=existing.teacher.full_name,
                original_scan_time=existing.scanned_at,
            ).model_dump(mode="json"),
        )

    db.refresh(scan)
    return ScanSuccess(
        student_name=student.full_name,
        exam_center_name=teacher.exam_center.name,
        scanned_at=scan.scanned_at,
    )
