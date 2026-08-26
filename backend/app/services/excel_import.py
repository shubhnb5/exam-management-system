import re
from io import BytesIO

import openpyxl
import pdfplumber
from docx import Document
from sqlalchemy.orm import Session

from app.models import ExamCenter, Student, Upload

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

EXPECTED_HEADERS = {
    "name": ["student name", "name", "full name"],
    "email": ["email", "email address"],
    "mobile": ["mobile number", "mobile", "phone", "phone number"],
}


def _match_header(header_cells: list[str]) -> dict[str, int]:
    normalized = [str(h or "").strip().lower() for h in header_cells]
    col_map: dict[str, int] = {}
    for field, aliases in EXPECTED_HEADERS.items():
        for idx, cell in enumerate(normalized):
            if cell in aliases:
                col_map[field] = idx
                break
    missing = [f for f in EXPECTED_HEADERS if f not in col_map]
    if missing:
        raise ValueError(
            f"Excel sheet is missing required column(s): {', '.join(missing)}. "
            f"Expected headers like: Student Name, Email, Mobile Number."
        )
    return col_map


def _rows_from_xlsx(file_bytes: bytes) -> list[tuple]:
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        raise ValueError("Excel sheet is empty.")
    return rows


def _rows_from_pdf(file_bytes: bytes) -> list[tuple]:
    """Extracts a student table from a PDF. Assumes the same header row as the
    Excel path (Name/Email/Mobile); if that header repeats on every page (common
    when a table spans multiple pages), later occurrences are treated as a
    repeated header and skipped rather than as a data row."""
    rows: list[tuple] = []
    header_key: list[str] | None = None

    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            for table in page.extract_tables():
                if not table:
                    continue
                table_header, *table_rows = table
                normalized = [str(c or "").strip().lower() for c in table_header]

                if header_key is None:
                    header_key = normalized
                    rows.append(tuple(table_header))
                    rows.extend(tuple(r) for r in table_rows)
                elif normalized == header_key:
                    rows.extend(tuple(r) for r in table_rows)
                else:
                    rows.extend(tuple(r) for r in [table_header, *table_rows])

    if not rows:
        raise ValueError("Could not find a table in the PDF.")
    return rows


def _rows_from_docx(file_bytes: bytes) -> list[tuple]:
    """Extracts a student table from a Word document, same header-repeat
    handling as the PDF path in case the document has more than one table
    (e.g. a table per page)."""
    rows: list[tuple] = []
    header_key: list[str] | None = None

    doc = Document(BytesIO(file_bytes))
    for table in doc.tables:
        if not table.rows:
            continue
        table_rows = [[cell.text for cell in row.cells] for row in table.rows]
        table_header, *data_rows = table_rows
        normalized = [str(c or "").strip().lower() for c in table_header]

        if header_key is None:
            header_key = normalized
            rows.append(tuple(table_header))
            rows.extend(tuple(r) for r in data_rows)
        elif normalized == header_key:
            rows.extend(tuple(r) for r in data_rows)
        else:
            rows.extend(tuple(r) for r in [table_header, *data_rows])

    if not rows:
        raise ValueError("Could not find a table in the Word document.")
    return rows


def import_students_excel(
    db: Session, file_bytes: bytes, filename: str, uploaded_by_user_id: int, exam_center_id: int
) -> tuple[Upload, list[str]]:
    center = db.get(ExamCenter, exam_center_id)
    if center is None:
        raise ValueError("Unknown exam center.")

    lower_name = filename.lower()
    if lower_name.endswith(".pdf"):
        rows = _rows_from_pdf(file_bytes)
    elif lower_name.endswith(".docx"):
        rows = _rows_from_docx(file_bytes)
    else:
        rows = _rows_from_xlsx(file_bytes)

    col_map = _match_header(list(rows[0]))
    data_rows = rows[1:]

    new_count = 0
    updated_count = 0
    errors: list[str] = []

    for i, row in enumerate(data_rows, start=2):
        try:
            name = str(row[col_map["name"]] or "").strip()
            email = str(row[col_map["email"]] or "").strip().lower()
            mobile = str(row[col_map["mobile"]] or "").strip()

            if not name or not email or not mobile:
                errors.append(f"Row {i}: missing required value(s), skipped.")
                continue
            if not EMAIL_RE.match(email):
                errors.append(f"Row {i}: invalid email '{email}', skipped.")
                continue

            existing = db.query(Student).filter(Student.email == email).one_or_none()
            if existing:
                existing.full_name = name
                existing.mobile_number = mobile
                existing.exam_center_id = center.id
                updated_count += 1
            else:
                db.add(
                    Student(
                        full_name=name,
                        email=email,
                        mobile_number=mobile,
                        exam_center_id=center.id,
                    )
                )
                new_count += 1
        except Exception as exc:  # noqa: BLE001 - keep importing remaining rows
            errors.append(f"Row {i}: {exc}")

    upload = Upload(
        filename=filename,
        uploaded_by=uploaded_by_user_id,
        row_count=len(data_rows),
        new_students=new_count,
        updated_students=updated_count,
        error_count=len(errors),
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload, errors
