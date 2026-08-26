import json
import os
from dataclasses import dataclass, field
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from app.services.fonts import BODY, BODY_BOLD, ensure_fonts_registered
from app.services.qr_service import render_qr_png
from app.services.rules_page import build_rules_page_pdf

MARGIN = 36
PAGE_W, PAGE_H = A4


@dataclass
class TicketConfig:
    org_name: str = "[Your Organization Name]"
    org_tagline: str = ""
    logo_path: str | None = None
    signature_path: str | None = None
    exam_title: str = "[Exam Title]"
    subject_code: str = ""
    signatory_title: str = "Head of Examination"
    signatory_name: str | None = None
    website: str | None = None
    telegram_handle: str | None = None
    timetable: list[dict] = field(default_factory=list)
    rules_page_pdf_path: str | None = None

    @classmethod
    def load(cls, path: str) -> "TicketConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        base_dir = os.path.dirname(os.path.abspath(path))
        for key in ("logo_path", "signature_path", "rules_page_pdf_path"):
            value = data.get(key)
            if value and not os.path.isabs(value):
                data[key] = os.path.join(base_dir, value)
        return cls(**data)


def _draw_border(c: canvas.Canvas):
    c.setLineWidth(1.2)
    c.rect(MARGIN - 8, MARGIN - 8, PAGE_W - 2 * (MARGIN - 8), PAGE_H - 2 * (MARGIN - 8))


def _draw_logo_placeholder(c: canvas.Canvas, x: float, y: float, size: float, logo_path: str | None):
    if logo_path and os.path.isfile(logo_path):
        c.drawImage(ImageReader(logo_path), x, y, width=size, height=size, preserveAspectRatio=True, mask="auto")
        return
    c.setLineWidth(1)
    c.circle(x + size / 2, y + size / 2, size / 2)
    c.setFont(BODY, 6)
    c.drawCentredString(x + size / 2, y + size / 2 - 3, "LOGO")


def _draw_signature_placeholder(c: canvas.Canvas, cx: float, cy: float, radius: float, signature_path: str | None):
    if signature_path and os.path.isfile(signature_path):
        c.drawImage(
            ImageReader(signature_path),
            cx - radius,
            cy - radius,
            width=2 * radius,
            height=2 * radius,
            preserveAspectRatio=True,
            mask="auto",
        )
        return
    c.setLineWidth(1)
    c.setStrokeColor(colors.grey)
    c.circle(cx, cy, radius)
    c.setFont(BODY, 6)
    c.setFillColor(colors.grey)
    c.drawCentredString(cx, cy - 3, "SIGN")
    c.setFillColor(colors.black)
    c.setStrokeColor(colors.black)


def _label_value_table(rows: list[tuple[str, str]], width: float) -> Table:
    label_style = ParagraphStyle("label", fontName=BODY_BOLD, fontSize=9)
    value_style = ParagraphStyle("value", fontName=BODY, fontSize=9)
    data = [[Paragraph(label, label_style), Paragraph(value, value_style)] for label, value in rows]
    t = Table(data, colWidths=[width * 0.32, width * 0.68])
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.75, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return t


def _timetable_table(rows: list[dict], width: float) -> Table:
    header_style = ParagraphStyle("th", fontName=BODY_BOLD, fontSize=8.5)
    cell_style = ParagraphStyle("td", fontName=BODY, fontSize=8.5)
    data = [[Paragraph("SUBJECT", header_style), Paragraph("DATE", header_style), Paragraph("TIME", header_style)]]
    for row in rows:
        data.append(
            [
                Paragraph(str(row.get("subject", "")), cell_style),
                Paragraph(str(row.get("date", "")), cell_style),
                Paragraph(str(row.get("time", "")), cell_style),
            ]
        )
    t = Table(data, colWidths=[width * 0.4, width * 0.3, width * 0.3])
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.75, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    return t


def _roll_no(mobile_number: str) -> str:
    digits = "".join(ch for ch in mobile_number if ch.isdigit())
    return digits[-7:] if len(digits) >= 7 else digits


def generate_hall_ticket_page(
    c: canvas.Canvas,
    student_name: str,
    mobile_number: str,
    exam_center_name: str,
    qr_token: str,
    config: TicketConfig,
):
    ensure_fonts_registered()
    content_w = PAGE_W - 2 * MARGIN
    _draw_border(c)

    y = PAGE_H - MARGIN - 12

    logo_size = 56
    _draw_logo_placeholder(c, MARGIN, y - logo_size + 12, logo_size, config.logo_path)

    qr_size = 70
    qr_x = PAGE_W - MARGIN - qr_size
    qr_img = ImageReader(render_qr_png(qr_token))
    c.drawImage(qr_img, qr_x, y - qr_size + 12, width=qr_size, height=qr_size)

    text_x = MARGIN + logo_size + 14
    text_w = qr_x - text_x - 10
    c.setFont(BODY_BOLD, 14)
    c.drawCentredString(text_x + text_w / 2, y - 8, config.org_name)
    if config.org_tagline:
        c.setFont(BODY, 9)
        c.drawCentredString(text_x + text_w / 2, y - 22, config.org_tagline)

    y -= logo_size + 20

    bar_h = 28
    c.setLineWidth(1.5)
    c.rect(MARGIN + content_w / 2 - 140, y - bar_h, 280, bar_h)
    c.setFont(BODY_BOLD, 15)
    c.drawCentredString(PAGE_W / 2, y - bar_h + 9, "ADMIT CARD")
    y -= bar_h + 16

    c.setFont(BODY_BOLD, 11)
    c.drawCentredString(PAGE_W / 2, y, config.exam_title)
    y -= 22

    c.setFont(BODY_BOLD, 11)
    c.drawString(MARGIN, y, "CANDIDATE DETAILS")
    y -= 8

    details_table = _label_value_table(
        [
            ("Candidate Name:", student_name),
            ("Mobile Number:", mobile_number),
            ("Roll No:", _roll_no(mobile_number)),
            ("Subject Code:", config.subject_code),
            ("Exam Name:", config.exam_title),
            ("Exam Centre:", exam_center_name),
        ],
        content_w,
    )
    tw, th = details_table.wrap(content_w, 300)
    details_table.drawOn(c, MARGIN, y - th)
    y -= th + 20

    if config.timetable:
        c.setFont(BODY_BOLD, 11)
        c.drawString(MARGIN, y, "EXAM TIME TABLE")
        y -= 8
        tt = _timetable_table(config.timetable, content_w)
        tw, th = tt.wrap(content_w, 400)
        tt.drawOn(c, MARGIN, y - th)
        y -= th + 20

    footer_y = MARGIN + 30
    _draw_signature_placeholder(c, MARGIN + 30, footer_y + 10, 28, config.signature_path)

    line_y = footer_y + 40
    c.line(PAGE_W - MARGIN - 160, line_y, PAGE_W - MARGIN, line_y)
    text_y = line_y - 12
    if config.signatory_name:
        c.setFont(BODY_BOLD, 9)
        c.drawRightString(PAGE_W - MARGIN, text_y, config.signatory_name)
        text_y -= 11
    c.setFont(BODY_BOLD if not config.signatory_name else BODY, 9 if not config.signatory_name else 8)
    c.drawRightString(PAGE_W - MARGIN, text_y, config.signatory_title)


def generate_hall_ticket_pdf(
    output_path: str,
    student_name: str,
    mobile_number: str,
    exam_center_name: str,
    qr_token: str,
    config: TicketConfig,
) -> None:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    generate_hall_ticket_page(c, student_name, mobile_number, exam_center_name, qr_token, config)
    c.showPage()
    c.save()
    buf.seek(0)

    writer = PdfWriter()
    for page in PdfReader(buf).pages:
        writer.add_page(page)

    if config.rules_page_pdf_path and os.path.isfile(config.rules_page_pdf_path):
        rules_reader = PdfReader(config.rules_page_pdf_path)
    else:
        rules_reader = PdfReader(build_rules_page_pdf(config))
    for page in rules_reader.pages:
        writer.add_page(page)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
