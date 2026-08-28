import json
import math
import os
from dataclasses import dataclass, field
from io import BytesIO

from pypdf import PdfReader, PdfWriter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from app.services.devanagari_shaping import ShapedTextFlowable, contains_devanagari, render_shaped_png
from app.services.fonts import BODY, BODY_BOLD, FONT_PATHS, ensure_fonts_registered
from app.services.qr_service import render_qr_png
from app.services.rules_page import build_rules_page_pdf

MARGIN = 36
PAGE_W, PAGE_H = A4

BRAND_BLUE = colors.Color(0.06, 0.22, 0.60)
BRAND_GREEN = colors.Color(0.11, 0.47, 0.20)
STAMP_COLOR = colors.Color(0.42, 0.11, 0.60)
ADDRESS_GREY = colors.Color(0.30, 0.30, 0.30)
CAPTION_GREY = colors.Color(0.35, 0.35, 0.35)


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
    signatory_signature_path: str | None = None
    signatory_org_line: str | None = None
    website: str | None = None
    telegram_handle: str | None = None
    org_address: str | None = None
    timetable: list[dict] = field(default_factory=list)
    rules_page_pdf_path: str | None = None

    @classmethod
    def load(cls, path: str) -> "TicketConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        base_dir = os.path.dirname(os.path.abspath(path))
        for key in ("logo_path", "signature_path", "signatory_signature_path", "rules_page_pdf_path"):
            value = data.get(key)
            if value and not os.path.isabs(value):
                data[key] = os.path.join(base_dir, value)
        return cls(**data)


_rules_page_cache: dict[str, bytes] = {}


def _get_rules_page_bytes(config: TicketConfig) -> bytes:
    """The rules page is identical for every student in a batch (it only
    depends on config.org_name — see rules_page.py), but building it involves
    a full reportlab flowable layout plus HarfBuzz-shaping several Devanagari
    lines. Rebuilding that per student was one of the biggest costs in a
    hall-ticket batch, so it's built once per org_name and reused."""
    cached = _rules_page_cache.get(config.org_name)
    if cached is None:
        cached = build_rules_page_pdf(config).getvalue()
        _rules_page_cache[config.org_name] = cached
    return cached


def _draw_text(
    c: canvas.Canvas,
    text: str,
    font_name: str,
    font_size: float,
    x: float,
    y: float,
    align: str = "left",
    color=None,
):
    """Draws `text` at baseline (x, y), same as reportlab's own drawString
    family — except Devanagari text is routed through HarfBuzz+FreeType
    shaping first (see devanagari_shaping.py) since reportlab can't form
    Indic conjuncts on its own. Non-Devanagari text is drawn exactly as
    before, so this is a no-op behavior change for plain English tickets.
    `color` only applies to the non-Devanagari path — omit it (default) to
    keep drawing in whatever fill color the canvas already has, unchanged."""
    text = str(text)
    if contains_devanagari(text):
        png_bytes, w, h, baseline = render_shaped_png(text, FONT_PATHS[font_name], font_size)
        if align == "center":
            draw_x = x - w / 2
        elif align == "right":
            draw_x = x - w
        else:
            draw_x = x
        c.drawImage(ImageReader(BytesIO(png_bytes)), draw_x, y - baseline, width=w, height=h, mask="auto")
    else:
        c.setFont(font_name, font_size)
        if color is not None:
            c.setFillColor(color)
        if align == "center":
            c.drawCentredString(x, y, text)
        elif align == "right":
            c.drawRightString(x, y, text)
        else:
            c.drawString(x, y, text)
        if color is not None:
            c.setFillColor(colors.black)


def _draw_wrapped_center(
    c: canvas.Canvas,
    text: str,
    font_name: str,
    font_size: float,
    cx: float,
    top_y: float,
    max_width: float,
    color=None,
    line_gap: float | None = None,
) -> float:
    """Word-wraps `text` to fit `max_width`, drawing each line centered on
    `cx` starting at `top_y` and moving downward. Returns the y position
    just below the last line drawn."""
    line_gap = line_gap or (font_size + 2)
    words = str(text).split()
    lines: list[str] = []
    current = ""
    for word in words:
        trial = f"{current} {word}".strip()
        if not current or c.stringWidth(trial, font_name, font_size) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    y = top_y
    for line in lines:
        _draw_text(c, line, font_name, font_size, cx, y, align="center", color=color)
        y -= line_gap
    return y


def _draw_arc_text(
    c: canvas.Canvas,
    text: str,
    cx: float,
    cy: float,
    radius: float,
    font_name: str,
    font_size: float,
    start_deg: float,
    end_deg: float,
    color,
    flip: bool = False,
):
    """Draws `text` character-by-character along the circular arc from
    `start_deg` to `end_deg` (standard math angles: 0=east, 90=north),
    used to letter a seal/stamp ring. `flip` rotates each glyph 180 degrees
    extra, for text running along the bottom of the ring."""
    c.setFont(font_name, font_size)
    widths = [c.stringWidth(ch, font_name, font_size) for ch in text]
    total_width = sum(widths) or 1
    total_angle = end_deg - start_deg
    angle = start_deg
    for ch, w in zip(text, widths):
        span = (w / total_width) * total_angle
        mid = angle + span / 2
        rad = math.radians(mid)
        x = cx + radius * math.cos(rad)
        y = cy + radius * math.sin(rad)
        c.saveState()
        c.translate(x, y)
        c.rotate((mid - 90) + (180 if flip else 0))
        c.setFillColor(color)
        c.setFont(font_name, font_size)
        c.drawCentredString(0, 0, ch)
        c.restoreState()
        angle += span


def _draw_official_stamp(c: canvas.Canvas, cx: float, cy: float, radius: float):
    """Self-drawn circular exam-office seal (vector primitives only, no
    external image asset) — used as the default bottom-left mark when no
    real signature image has been configured."""
    c.saveState()
    c.setStrokeColor(STAMP_COLOR)
    c.setLineWidth(1.3)
    c.circle(cx, cy, radius, stroke=1, fill=0)
    c.setLineWidth(0.6)
    c.circle(cx, cy, radius - 4, stroke=1, fill=0)

    _draw_arc_text(c, "COMBINE MENTOR", cx, cy, radius - 9, BODY_BOLD, 5.4, 150, 30, STAMP_COLOR)
    _draw_arc_text(c, "OFFICIAL SEAL", cx, cy, radius - 9, BODY_BOLD, 5.0, 210, 330, STAMP_COLOR, flip=True)

    c.setLineWidth(0.8)
    c.setStrokeColor(STAMP_COLOR)
    c.line(cx - radius + 5, cy, cx - radius + 11, cy)
    c.line(cx + radius - 11, cy, cx + radius - 5, cy)

    c.setFillColor(STAMP_COLOR)
    c.setFont(BODY_BOLD, radius * 0.38)
    c.drawCentredString(cx, cy - radius * 0.14, "CMO")

    c.setStrokeColor(colors.black)
    c.setFillColor(colors.black)
    c.restoreState()


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


def _draw_photo_placeholder(c: canvas.Canvas, x: float, y: float, w: float, h: float):
    """Reserved candidate-photo slot. No photo upload exists in the app yet,
    so this draws a dashed frame with a plain black bust-silhouette icon
    (the standard "person" glyph, à la 👤) standing in for a photo — drawn
    with vector shapes rather than the literal emoji character, since the
    ticket's embedded font (NotoSansDevanagari) has no emoji glyphs and
    would render the character as a blank/missing-glyph box instead."""
    c.saveState()
    c.setDash(3, 2)
    c.setLineWidth(1)
    c.setStrokeColor(colors.grey)
    c.rect(x, y, w, h, stroke=1, fill=0)
    c.setDash()

    label_h = 14
    icon_bottom = y + label_h
    icon_top = y + h - 10
    icon_h = icon_top - icon_bottom
    cx = x + w / 2

    icon_scale = 0.78
    scaled_h = icon_h * icon_scale
    icon_top = icon_top - (icon_h - scaled_h) / 2
    icon_bottom = icon_bottom + (icon_h - scaled_h) / 2
    icon_h = scaled_h

    c.setFillColor(colors.black)

    head_r = icon_h * 0.21
    head_cy = icon_top - head_r
    c.circle(cx, head_cy, head_r, stroke=0, fill=1)

    shoulder_base_y = icon_bottom + icon_h * 0.06
    shoulder_bulge = icon_h * 0.34
    shoulder_w = w * 0.74 * icon_scale
    c.wedge(
        cx - shoulder_w / 2,
        shoulder_base_y - shoulder_bulge,
        cx + shoulder_w / 2,
        shoulder_base_y + shoulder_bulge,
        0,
        180,
        stroke=0,
        fill=1,
    )

    c.setFillColor(colors.grey)
    c.setFont(BODY_BOLD, 7)
    c.drawCentredString(cx, y + 4, "PHOTO")

    c.setFillColor(colors.black)
    c.restoreState()


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
    _draw_official_stamp(c, cx, cy, radius)
    _draw_text(c, "Official Examination Stamp", BODY, 7, cx + radius + 10, cy - 2, align="left", color=CAPTION_GREY)


def _cell_flowable(text: str, font_name: str, font_size: float, align: str = "LEFT"):
    text = str(text)
    if contains_devanagari(text):
        return ShapedTextFlowable(text, FONT_PATHS[font_name], font_size)
    alignment = TA_CENTER if align == "CENTER" else TA_LEFT
    return Paragraph(
        text,
        ParagraphStyle(f"cell-{font_name}-{font_size}-{align}", fontName=font_name, fontSize=font_size, alignment=alignment),
    )


def _label_value_table(rows: list[tuple[str, str]], width: float) -> Table:
    data = [[_cell_flowable(label, BODY_BOLD, 11), _cell_flowable(value, BODY_BOLD, 11)] for label, value in rows]
    t = Table(data, colWidths=[width * 0.32, width * 0.68])
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.75, colors.black),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def _exam_details_table(seat_no: str, exam_center_name: str, width: float) -> Table:
    data = [
        [_cell_flowable("Exam Seat No", BODY_BOLD, 9.5, align="CENTER"), _cell_flowable("Exam Centre", BODY_BOLD, 9.5, align="CENTER")],
        [_cell_flowable(seat_no, BODY_BOLD, 11, align="CENTER"), _cell_flowable(exam_center_name, BODY_BOLD, 11, align="CENTER")],
    ]
    t = Table(data, colWidths=[width * 0.28, width * 0.72])
    t.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.75, colors.black),
                ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    return t


def _timetable_table(rows: list[dict], width: float) -> Table:
    data = [
        [
            _cell_flowable("SUBJECT", BODY_BOLD, 8.5),
            _cell_flowable("DATE", BODY_BOLD, 8.5),
            _cell_flowable("TIME", BODY_BOLD, 8.5),
        ]
    ]
    for row in rows:
        data.append(
            [
                _cell_flowable(row.get("subject", ""), BODY, 8.5),
                _cell_flowable(row.get("date", ""), BODY, 8.5),
                _cell_flowable(row.get("time", ""), BODY, 8.5),
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

    logo_size = 102
    _draw_logo_placeholder(c, MARGIN, y - logo_size + 12, logo_size, config.logo_path)

    qr_size = 102
    qr_x = PAGE_W - MARGIN - qr_size
    qr_img = ImageReader(render_qr_png(qr_token))
    c.drawImage(qr_img, qr_x, y - qr_size + 12, width=qr_size, height=qr_size)

    text_x = MARGIN + logo_size + 14
    text_w = qr_x - text_x - 10
    text_cx = text_x + text_w / 2
    header_y = y - 12
    _draw_text(c, config.org_name, BODY_BOLD, 22, text_cx, header_y, align="center", color=BRAND_BLUE)
    header_y -= 21
    if config.org_tagline:
        _draw_text(c, config.org_tagline, BODY_BOLD, 14.5, text_cx, header_y, align="center", color=BRAND_GREEN)
        header_y -= 17
    if config.org_address:
        _draw_wrapped_center(c, config.org_address, BODY_BOLD, 9.8, text_cx, header_y, text_w, color=ADDRESS_GREY, line_gap=12)

    y -= logo_size + 20

    c.setLineWidth(1)
    c.line(MARGIN, y + 10, PAGE_W - MARGIN, y + 10)

    bar_w, bar_h = 300, 32
    bar_x = PAGE_W / 2 - bar_w / 2
    c.setLineWidth(1.4)
    c.roundRect(bar_x, y - bar_h, bar_w, bar_h, 5, stroke=1, fill=0)
    c.setLineWidth(0.6)
    c.roundRect(bar_x + 3, y - bar_h + 3, bar_w - 6, bar_h - 6, 3, stroke=1, fill=0)
    c.setFont(BODY_BOLD, 14)
    spaced_title = " ".join("ADMIT") + "    " + " ".join("CARD")
    c.drawCentredString(PAGE_W / 2, y - bar_h / 2 - 4, spaced_title)
    y -= bar_h + 16

    _draw_text(c, config.exam_title, BODY_BOLD, 11, PAGE_W / 2, y, align="center")
    y -= 22

    c.setFont(BODY_BOLD, 11)
    c.drawString(MARGIN, y, "CANDIDATE DETAILS")
    y -= 8

    photo_w = 92
    photo_gap = 12
    table_w = content_w - photo_w - photo_gap

    details_table = _label_value_table(
        [
            ("Candidate Name:", student_name),
            ("Mobile Number:", mobile_number),
            ("Roll No:", _roll_no(mobile_number)),
            ("Subject Code:", config.subject_code),
            ("Exam Name:", config.exam_title),
        ],
        table_w,
    )
    tw, th = details_table.wrap(table_w, 300)
    details_table.drawOn(c, MARGIN, y - th)
    _draw_photo_placeholder(c, MARGIN + table_w + photo_gap, y - th, photo_w, th)
    y -= th + 20

    c.setFont(BODY_BOLD, 11)
    c.drawString(MARGIN, y, "EXAMINATION DETAILS")
    y -= 8

    exam_details_table = _exam_details_table(_roll_no(mobile_number), exam_center_name, content_w)
    tw, th = exam_details_table.wrap(content_w, 200)
    exam_details_table.drawOn(c, MARGIN, y - th)
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
    line_left = PAGE_W - MARGIN - 160
    line_right = PAGE_W - MARGIN

    if config.signatory_signature_path and os.path.isfile(config.signatory_signature_path):
        sig_img = ImageReader(config.signatory_signature_path)
        native_w, native_h = sig_img.getSize()
        sig_h = min(32, native_h * 110 / native_w)
        sig_w = sig_h * native_w / native_h
        c.drawImage(
            sig_img,
            (line_left + line_right) / 2 - sig_w / 2,
            line_y + 3,
            width=sig_w,
            height=sig_h,
            preserveAspectRatio=True,
            mask="auto",
        )

    c.line(line_left, line_y, line_right, line_y)
    text_y = line_y - 12
    if config.signatory_name:
        _draw_text(c, config.signatory_name, BODY_BOLD, 9, PAGE_W - MARGIN, text_y, align="right")
        text_y -= 11
    title_font, title_size = (BODY_BOLD, 9) if not config.signatory_name else (BODY, 8)
    _draw_text(c, config.signatory_title, title_font, title_size, PAGE_W - MARGIN, text_y, align="right")
    if config.signatory_org_line:
        text_y -= 10
        _draw_text(
            c, config.signatory_org_line, BODY, 7.5, PAGE_W - MARGIN, text_y, align="right", color=ADDRESS_GREY
        )


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
        rules_reader = PdfReader(BytesIO(_get_rules_page_bytes(config)))
    for page in rules_reader.pages:
        writer.add_page(page)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
