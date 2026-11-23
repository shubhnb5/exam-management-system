import csv
import io
import re
from io import BytesIO

import openpyxl
import pdfplumber
from docx import Document
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models import ExamCenter, Student, Upload
from app.schemas import TicketRefresh, UploadProblem
from app.services.student_records import EMAIL_RE, mark_ticket_outdated, ticket_changes
from app.services.ticket_files import discard_ticket_pdf
from app.validators import normalize_mobile

# Substrings matched against a header cell after punctuation is stripped, so
# "Phone No.", "Mobile No", "Contact Number", "Email ID", "Candidate Name",
# etc. are all recognized without needing an exact alias match.
FIELD_KEYWORDS = {
    "name": ["name"],
    "email": ["email", "e mail"],
    "mobile": ["mobile", "phone", "contact", "whatsapp"],
}


def _normalize_header(cell) -> str:
    text = str(cell or "").strip().lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _match_header(header_cells: list[str]) -> dict[str, int]:
    normalized = [_normalize_header(h) for h in header_cells]
    col_map: dict[str, int] = {}
    for field, keywords in FIELD_KEYWORDS.items():
        for idx, cell in enumerate(normalized):
            if idx in col_map.values():
                continue
            if any(keyword in cell for keyword in keywords):
                col_map[field] = idx
                break
    missing = [f for f in FIELD_KEYWORDS if f not in col_map]
    if missing:
        raise ValueError(
            f"Sheet is missing required column(s): {', '.join(missing)}. "
            f"Expected headers like: Student Name, Email, Mobile Number/Phone No."
        )
    return col_map


def _cell(row: tuple, idx: int) -> str:
    if idx >= len(row):
        return ""
    return str(row[idx] if row[idx] is not None else "").strip()


def _is_blank_row(row: tuple) -> bool:
    return not any(str(c or "").strip() for c in row)


def _decode_text(file_bytes: bytes) -> str:
    """CSV files exported from Excel/Google Sheets on Windows are frequently
    saved as cp1252/latin-1 rather than UTF-8, and often carry a BOM — try
    the common encodings in order rather than assuming UTF-8 and failing
    the whole upload over a single rupee/mojibake character."""
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="replace")


def _rows_from_csv(file_bytes: bytes) -> list[tuple]:
    """Parses a .csv upload. Delimiter is sniffed rather than assumed —
    files saved from Excel as "CSV" sometimes actually use tabs or
    semicolons — and fully blank rows are dropped up front."""
    text = _decode_text(file_bytes)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = [tuple(row) for row in reader if not _is_blank_row(row)]
    if not rows:
        raise ValueError("CSV file is empty.")
    return rows


def _rows_from_xlsx(file_bytes: bytes) -> list[tuple]:
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb.active
    all_rows = list(ws.iter_rows(values_only=True))
    if not all_rows:
        raise ValueError("Excel sheet is empty.")
    header, *data_rows = all_rows
    rows = [header, *(r for r in data_rows if not _is_blank_row(r))]
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
                    rows.extend(tuple(r) for r in table_rows if not _is_blank_row(r))
                elif normalized == header_key:
                    rows.extend(tuple(r) for r in table_rows if not _is_blank_row(r))
                else:
                    rows.extend(tuple(r) for r in [table_header, *table_rows] if not _is_blank_row(r))

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
            rows.extend(tuple(r) for r in data_rows if not _is_blank_row(r))
        elif normalized == header_key:
            rows.extend(tuple(r) for r in data_rows if not _is_blank_row(r))
        else:
            rows.extend(tuple(r) for r in [table_header, *data_rows] if not _is_blank_row(r))

    if not rows:
        raise ValueError("Could not find a table in the Word document.")
    return rows


def import_students_excel(
    db: Session, file_bytes: bytes, filename: str, uploaded_by_user_id: int, exam_center_id: int
) -> tuple[Upload, list[UploadProblem], list[TicketRefresh]]:
    center = db.get(ExamCenter, exam_center_id)
    if center is None:
        raise ValueError("Unknown exam center.")

    lower_name = filename.lower()
    if lower_name.endswith(".csv"):
        rows = _rows_from_csv(file_bytes)
    elif lower_name.endswith(".pdf"):
        rows = _rows_from_pdf(file_bytes)
    elif lower_name.endswith(".docx"):
        rows = _rows_from_docx(file_bytes)
    else:
        rows = _rows_from_xlsx(file_bytes)

    col_map = _match_header(list(rows[0]))
    data_rows = [r for r in rows[1:] if not _is_blank_row(r)]

    # Every existing student is loaded once up front and all checks run in
    # memory, then everything is written in one transaction. (Checking and
    # saving row-by-row took ~80s for 5000 rows even against a local DB —
    # longer than a reverse proxy's request timeout.)
    existing_students = (
        db.query(Student).options(selectinload(Student.hall_ticket), selectinload(Student.exam_center)).all()
    )
    by_email: dict[str, Student] = {s.email: s for s in existing_students}
    # mobile -> current holder. `row` is set for students added/updated by
    # this file, so problems can point at the conflicting row.
    holder_by_mobile: dict[str, dict] = {}
    for s in existing_students:
        holder_by_mobile.setdefault(s.mobile_number, {"email": s.email, "name": s.full_name, "row": None})

    new_count = 0
    updated_count = 0
    problems: list[UploadProblem] = []
    refreshed: dict[int, TicketRefresh] = {}
    pdfs_to_discard: list[str] = []
    new_students: list[Student] = []

    for i, row in enumerate(data_rows, start=2):
        name = _cell(row, col_map["name"])
        email = _cell(row, col_map["email"]).lower()
        raw_mobile = _cell(row, col_map["mobile"])

        def skip(reason: str) -> None:
            problems.append(UploadProblem(row=i, name=name, email=email, mobile=raw_mobile, reason=reason))

        if not name or not email or not raw_mobile:
            missing = [label for label, value in (("name", name), ("email", email), ("mobile", raw_mobile)) if not value]
            skip(f"Missing {', '.join(missing)}.")
            continue
        if not EMAIL_RE.match(email):
            skip("Invalid email address.")
            continue
        mobile = normalize_mobile(raw_mobile)
        if mobile is None:
            skip("Invalid mobile number — must be a 10-digit Indian mobile number.")
            continue

        # One mobile number = one student. Students log into the portal with
        # their mobile number and only see the admit card uploaded under it,
        # so two students sharing a number can't both be accepted.
        holder = holder_by_mobile.get(mobile)
        if holder is not None and holder["email"] != email:
            if holder["row"] is not None:
                skip(f"Same mobile number as row {holder['row']} ({holder['name']}) in this file.")
            else:
                skip(f"Mobile number already belongs to {holder['name']} ({holder['email']}), uploaded earlier.")
            continue

        student = by_email.get(email)
        if student is not None:
            if student.id is not None:
                changes = ticket_changes(student, name, mobile, center)
                if changes and student.hall_ticket is not None:
                    # Keep the QR token (already-printed cards still scan);
                    # the PDF is rebuilt from the new details on next view.
                    pdf_path = mark_ticket_outdated(student)
                    if pdf_path not in pdfs_to_discard:
                        pdfs_to_discard.append(pdf_path)
                    previous = refreshed.get(student.id)
                    merged = (previous.changes if previous else []) + changes
                    refreshed[student.id] = TicketRefresh(student_name=name, changes=merged)
            if student.mobile_number != mobile:
                old = holder_by_mobile.get(student.mobile_number)
                if old is not None and old["email"] == email:
                    del holder_by_mobile[student.mobile_number]
            student.full_name = name
            student.mobile_number = mobile
            student.exam_center_id = center.id
            student.exam_center = center
            updated_count += 1
        else:
            student = Student(full_name=name, email=email, mobile_number=mobile, exam_center_id=center.id)
            student.exam_center = center
            by_email[email] = student
            new_students.append(student)
            new_count += 1
        holder_by_mobile[mobile] = {"email": email, "name": name, "row": i}

    db.add_all(new_students)
    upload = Upload(
        filename=filename,
        uploaded_by=uploaded_by_user_id,
        row_count=len(data_rows),
        new_students=new_count,
        updated_students=updated_count,
        error_count=len(problems),
    )
    db.add(upload)
    try:
        db.commit()
    except IntegrityError:
        # Only possible if someone else changed the same students at the
        # same moment (e.g. two uploads at once). Nothing was saved.
        db.rollback()
        raise ValueError("The student list changed while this file was being uploaded. Nothing was saved — please upload it again.")
    db.refresh(upload)

    for pdf_path in pdfs_to_discard:
        discard_ticket_pdf(pdf_path)

    return upload, problems, list(refreshed.values())
