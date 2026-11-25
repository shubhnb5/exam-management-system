"""Admit card (प्रवेश प्रमाणपत्र) PDF: page 1 is the card, page 2 the
instructions. The layout reproduces the approved sample card point for point
(positions measured from it, in points from the top-left of an A4 page).

Per-student values: QR code, seat number (seat_prefix + last 5 digits of the
mobile number), mobile number, name, exam center district and exam center
name. Everything else (header, exam name, timetable, signatory, instructions)
comes from ticket_template/config.json."""

import json
import os
import tempfile
from dataclasses import dataclass, field, fields
from io import BytesIO

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from app.services.devanagari_shaping import contains_devanagari, measure_shaped_width_pt, render_shaped_png
from app.services.fonts import BODY, BODY_BOLD, FONT_PATHS, SERIF_DEVA, ensure_fonts_registered
from app.services.pdf_images import draw_file, draw_png
from app.services.qr_service import render_qr_png
from app.services.rules_page import draw_page_footer, draw_rules_page

# Store images as compressed binary instead of ASCII85 text (smaller, faster;
# the rendered output is identical).
rl_config.useA85 = 0

PAGE_W, PAGE_H = A4

# Latin text uses the standard PDF fonts (metric-compatible with the sample's
# Liberation fonts). Devanagari text is shaped with the Noto fonts.
TIMES = "Times-Roman"
TIMES_BOLD = "Times-Bold"
HELV = "Helvetica"
HELV_BOLD = "Helvetica-Bold"
_DEVANAGARI_FALLBACK = {TIMES: BODY, TIMES_BOLD: BODY_BOLD, HELV: BODY, HELV_BOLD: BODY_BOLD}

LABEL_GREY = colors.Color(0.949, 0.949, 0.949)
SIGNATURE_GREY = colors.Color(0.851, 0.851, 0.851)
GRID = 0.75  # table / box line width

CHANGED_NAME_PLACEHOLDER = "--"


@dataclass
class TicketConfig:
    header_image_path: str | None = None
    stamp_path: str | None = None
    photo_placeholder_path: str | None = None
    exam_title: str = ""
    seat_prefix: str = "10"
    signatory_name: str = ""
    signatory_title: str = ""
    footer_text: str = ""
    schedule: list[dict] = field(default_factory=list)
    important_notes: list[str] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: str) -> "TicketConfig":
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        base_dir = os.path.dirname(os.path.abspath(path))
        for key in ("header_image_path", "stamp_path", "photo_placeholder_path"):
            value = data.get(key)
            if value and not os.path.isabs(value):
                data[key] = os.path.join(base_dir, value)
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


def seat_number(mobile_number: str, prefix: str = "10") -> str:
    """बैठक क्रमांक: the prefix followed by the last 5 digits of the mobile
    number (7028773531 -> 1073531). Not unique by design: two students whose
    numbers end in the same 5 digits get the same seat number; the QR code is
    what identifies a student at the gate."""
    digits = "".join(ch for ch in str(mobile_number or "") if ch.isdigit())
    return f"{prefix}{digits[-5:]}"


# ------------------------------------------------------------------ drawing


def _y(top: float) -> float:
    """Converts a distance from the top of the page into reportlab's y."""
    return PAGE_H - top


def _font_for(text: str, font: str) -> str:
    if contains_devanagari(text) and font in _DEVANAGARI_FALLBACK:
        return _DEVANAGARI_FALLBACK[font]
    return font


def _text_width(text: str, font: str, size: float, char_space: float = 0) -> float:
    font = _font_for(text, font)
    if font in FONT_PATHS:
        return measure_shaped_width_pt(text, FONT_PATHS[font], size)
    return stringWidth(text, font, size) + char_space * max(len(text) - 1, 0)


def _draw(c: canvas.Canvas, text: str, font: str, size: float, x: float, baseline: float, align: str = "left", char_space: float = 0):
    """Draws one line of text with its baseline `baseline` pt from the top of
    the page. Devanagari is shaped (HarfBuzz) and placed as an image, since
    reportlab cannot form Indic conjuncts itself."""
    text = str(text)
    if not text:
        return
    font = _font_for(text, font)
    if font in FONT_PATHS:
        png, w, h, base = render_shaped_png(text, FONT_PATHS[font], size)
        left = x - w / 2 if align == "center" else x - w if align == "right" else x
        draw_png(c, png, left, _y(baseline) - (h - base), w, h)
        return
    w = _text_width(text, font, size, char_space)
    left = x - w / 2 if align == "center" else x - w if align == "right" else x
    t = c.beginText(left, _y(baseline))
    t.setFont(font, size)
    t.setCharSpace(char_space)
    t.textOut(text)
    c.drawText(t)


def _wrap(text: str, font: str, size: float, max_width: float) -> list[str]:
    """Word-wraps `text` into lines no wider than `max_width` (a single word
    longer than the width keeps its own line). Explicit newlines are kept."""
    lines: list[str] = []
    for paragraph in str(text).split("\n"):
        current = ""
        for word in paragraph.split():
            candidate = f"{current} {word}" if current else word
            if not current or _text_width(candidate, font, size) <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
    return lines or [""]


def _draw_lines(c, lines, font, size, x, center, offset, leading, align="left"):
    """Draws `lines` vertically centred on `center` (baselines at
    center + offset, spread by `leading`) — the sample's middle alignment."""
    first = center + offset - (len(lines) - 1) * leading / 2
    for i, line in enumerate(lines):
        _draw(c, line, font, size, x, first + i * leading, align)


def _image(c, path: str | None, x0: float, top: float, x1: float, bottom: float):
    if path and os.path.isfile(path):
        draw_file(c, path, x0, _y(bottom), x1 - x0, bottom - top)


def _fill_rect(c, x0, top, x1, bottom, color):
    c.setFillColor(color)
    c.rect(x0, _y(bottom), x1 - x0, bottom - top, stroke=0, fill=1)
    c.setFillColor(colors.black)


def _hline(c, x0, x1, top):
    c.line(x0, _y(top), x1, _y(top))


def _vline(c, x, top, bottom):
    c.line(x, _y(top), x, _y(bottom))


# ------------------------------------------------------------------ page 1

# Candidate details table.
DT_LEFT, DT_LABEL_R, DT_VALUE_R, DT_RIGHT = 43.1, 175.85, 436.1, 552.35
DT_TOP = 184.1
DT_LABEL_X, DT_VALUE_X = 48.9, 182.1
DT_VALUE_W = DT_VALUE_R - DT_VALUE_X - 6
DT_LABEL_SIZE, DT_LABEL_LEADING, DT_LABEL_OFFSET = 10, 13.5, 2.67
DT_VALUE_SIZE, DT_VALUE_LEADING, DT_VALUE_OFFSET, DT_VALUE_PAD = 10.99, 15.39, 3.36, 7.11
PHOTO_CELL_MIN_H = 135.75

# Timetable.
TT_COLS = [43.1, 139.85, 205.85, 271.85, 340.85, 399.35, 457.85, 552.35]
TT_GAP = 9.0  # between the two tables
TT_HEADER_H = 54.0
TT_ROW_MIN_H = 39.5
TT_HEADERS = [
    ["परीक्षेचा वार व", "दिनांक"],
    ["उपकेंद्रावरील", "उपस्थिती"],
    ["परीक्षा", "कक्षातील", "शेवटच्या", "प्रवेशाची वेळ"],
    ["परीक्षेचा प्रत्यक्ष", "कालावधी"],
    ["विषय"],
    ["विषयाचा", "संकेतांक"],
    ["परीक्षेचे स्वरूप"],
]
TT_FIELDS = ["date", "reporting", "last_entry", "duration", "subject", "subject_code", "format"]
TT_BOLD_SIZE, TT_BOLD_LEADING, TT_BOLD_OFFSET = 9.49, 12.0, 1.87
TT_SERIF_SIZE, TT_SERIF_LEADING, TT_SERIF_OFFSET = 9.49, 11.4, 0.73
TT_CODE_SIZE, TT_CODE_OFFSET = 10.5, 3.0
TT_PAD = 2.5  # vertical breathing room above/below a cell's text
TT_WRAP_PAD = 4.0  # horizontal padding when wrapping cell text


def _draw_header(c, qr_token: str, config: TicketConfig):
    c.setLineWidth(GRID)
    c.rect(43.1, _y(138.4), 552.4 - 43.1, 138.4 - 34.1, stroke=1, fill=0)
    _image(c, config.header_image_path, 48.7, 43.5, 443.2, 129.7)
    c.drawImage(ImageReader(render_qr_png(qr_token)), 451.5, _y(132.7), width=93, height=93)
    c.roundRect(448.9, _y(133.9), 547.1 - 448.9, 133.9 - 39.4, 6, stroke=1, fill=0)

    _draw(c, "- प्रवेश प्रमाणपत्र -", BODY_BOLD, 15, PAGE_W / 2, 156.78, align="center")
    _draw(c, config.exam_title, BODY_BOLD, 10.5, 42.5, 174.72)


def _draw_details(c, *, seat_no: str, mobile: str, name: str, district: str, center_name: str, config: TicketConfig) -> float:
    """Draws the candidate details table; returns its bottom (from top)."""
    rows = [
        (["बैठक क्रमांक :-"], seat_no, 28.5),
        (["मोबाईल नंबर :-"], mobile, 28.5),
        (["उमेदवाराचे नाव :-"], name, 22.5),
        (["उमेदवाराचे बदलेले नाव", "(असल्यास):-"], CHANGED_NAME_PLACEHOLDER, 36.75),
        (["जिल्हा केंद्र:-"], district, 22.5),
        (["परीक्षेचे ठिकाण :-"], center_name, 22.5),
    ]
    laid_out = []
    for label_lines, value, min_h in rows:
        value_lines = _wrap(value or CHANGED_NAME_PLACEHOLDER, TIMES, DT_VALUE_SIZE, DT_VALUE_W)
        label_h = len(label_lines) * DT_LABEL_LEADING + 9.75
        height = max(min_h, len(value_lines) * DT_VALUE_LEADING + DT_VALUE_PAD, label_h)
        laid_out.append([label_lines, value_lines, height])

    # Rows 1-2 share the photo-caption cell; rows 3-6 share the photo cell,
    # which needs a minimum height for the photo + signature boxes.
    photo_rows_h = sum(r[2] for r in laid_out[2:])
    if photo_rows_h < PHOTO_CELL_MIN_H:
        laid_out[-1][2] += PHOTO_CELL_MIN_H - photo_rows_h

    bounds = []
    top = DT_TOP
    for _, _, height in laid_out:
        bounds.append((top, top + height))
        top += height
    bottom = top
    caption_bottom = bounds[1][1]

    for (row_top, row_bottom) in bounds:
        _fill_rect(c, DT_LEFT, row_top, DT_LABEL_R, row_bottom, LABEL_GREY)
    _fill_rect(c, DT_VALUE_R, DT_TOP, DT_RIGHT, caption_bottom, LABEL_GREY)

    for (label_lines, value_lines, _), (row_top, row_bottom) in zip(laid_out, bounds):
        center = (row_top + row_bottom) / 2
        _draw_lines(c, label_lines, BODY_BOLD, DT_LABEL_SIZE, DT_LABEL_X, center, DT_LABEL_OFFSET, DT_LABEL_LEADING)
        _draw_lines(c, value_lines, TIMES, DT_VALUE_SIZE, DT_VALUE_X, center, DT_VALUE_OFFSET, DT_VALUE_LEADING)

    photo_cx = (DT_VALUE_R + DT_RIGHT) / 2
    _draw_lines(
        c,
        ["उमेदवाराचे छायाचित्र व", "स्वाक्षरी"],
        BODY_BOLD,
        DT_LABEL_SIZE,
        photo_cx,
        (DT_TOP + caption_bottom) / 2,
        DT_LABEL_OFFSET,
        DT_LABEL_LEADING,
        align="center",
    )
    photo_top = caption_bottom
    _image(c, config.photo_placeholder_path, 440.2, photo_top + 3.4, 548.2, photo_top + 91.9)
    sig_top = photo_top + 95.3
    c.setFillColor(SIGNATURE_GREY)
    c.setLineWidth(GRID)
    c.roundRect(440.6, _y(sig_top + 24.7), 547.9 - 440.6, 24.7, 5, stroke=1, fill=1)
    c.setFillColor(colors.black)
    _draw(c, "signature", HELV, 8.5, photo_cx, sig_top + 15.4, align="center")

    c.setLineWidth(GRID)
    c.setStrokeColor(colors.black)
    _hline(c, DT_LEFT, DT_RIGHT, DT_TOP)
    for i, (_, row_bottom) in enumerate(bounds):
        # Row separators stop at the photo column, except below the caption
        # cell and at the bottom of the table.
        right = DT_RIGHT if i in (1, len(bounds) - 1) else DT_VALUE_R
        _hline(c, DT_LEFT, right, row_bottom)
    for x in (DT_LEFT, DT_LABEL_R, DT_VALUE_R, DT_RIGHT):
        _vline(c, x, DT_TOP, bottom)
    return bottom


def _draw_timetable(c, top: float, schedule: list[dict]):
    cols = TT_COLS
    widths = [cols[i + 1] - cols[i] - 2 * TT_WRAP_PAD for i in range(len(cols) - 1)]

    def cell_lines(i: int, value: str) -> list[str]:
        if TT_FIELDS[i] == "date":
            return _wrap(value, BODY_BOLD, TT_BOLD_SIZE, widths[i])
        if TT_FIELDS[i] == "subject_code":
            return _wrap(value, TIMES_BOLD, TT_CODE_SIZE, widths[i])
        return _wrap(value, SERIF_DEVA, TT_SERIF_SIZE, widths[i])

    header_bottom = top + TT_HEADER_H
    _fill_rect(c, cols[0], top, cols[-1], header_bottom, LABEL_GREY)
    header_center = (top + header_bottom) / 2
    for i, lines in enumerate(TT_HEADERS):
        cx = (cols[i] + cols[i + 1]) / 2
        _draw_lines(c, lines, BODY_BOLD, TT_BOLD_SIZE, cx, header_center, TT_BOLD_OFFSET, TT_BOLD_LEADING, align="center")

    row_top = header_bottom
    row_lines = [top, header_bottom]
    for entry in schedule:
        cells = [cell_lines(i, str(entry.get(f, "") or "")) for i, f in enumerate(TT_FIELDS)]
        needed = max(
            len(lines) * (TT_BOLD_LEADING if TT_FIELDS[i] == "date" else TT_SERIF_LEADING) + 2 * TT_PAD
            for i, lines in enumerate(cells)
        )
        row_bottom = row_top + max(TT_ROW_MIN_H, needed)
        center = (row_top + row_bottom) / 2
        for i, lines in enumerate(cells):
            cx = (cols[i] + cols[i + 1]) / 2
            field_name = TT_FIELDS[i]
            if field_name == "date":
                _draw_lines(c, lines, BODY_BOLD, TT_BOLD_SIZE, cx, center, TT_BOLD_OFFSET, TT_BOLD_LEADING, "center")
            elif field_name == "subject_code":
                _draw_lines(c, lines, TIMES_BOLD, TT_CODE_SIZE, cx, center, TT_CODE_OFFSET, TT_BOLD_LEADING, "center")
            else:
                _draw_lines(c, lines, SERIF_DEVA, TT_SERIF_SIZE, cx, center, TT_SERIF_OFFSET, TT_SERIF_LEADING, "center")
        row_lines.append(row_bottom)
        row_top = row_bottom

    c.setLineWidth(GRID)
    for y in row_lines:
        _hline(c, cols[0], cols[-1], y)
    for x in cols:
        _vline(c, x, top, row_top)


def _draw_signatory(c, config: TicketConfig):
    _image(c, config.stamp_path, 42.7, 709.5, 122.2, 787.5)
    cx = (348.7 + 552.7) / 2
    _draw(c, config.signatory_name, HELV_BOLD, 12.49, cx, 756.74, align="center", char_space=0.23)
    _fill_rect(c, 348.7, 765.0, 552.7, 766.5, colors.black)
    _draw(c, config.signatory_title, HELV_BOLD, 9.49, cx, 779.98, align="center", char_space=0.45)


def generate_hall_ticket_page(
    c: canvas.Canvas,
    student_name: str,
    mobile_number: str,
    exam_center_name: str,
    qr_token: str,
    config: TicketConfig,
    district: str | None = None,
):
    ensure_fonts_registered()
    c.setStrokeColor(colors.black)
    c.setFillColor(colors.black)
    _draw_header(c, qr_token, config)
    details_bottom = _draw_details(
        c,
        seat_no=seat_number(mobile_number, config.seat_prefix),
        mobile=mobile_number,
        name=student_name,
        district=district or CHANGED_NAME_PLACEHOLDER,
        center_name=exam_center_name,
        config=config,
    )
    _draw_timetable(c, details_bottom + TT_GAP, config.schedule)
    _draw_signatory(c, config)
    draw_page_footer(c, config.footer_text)


def generate_hall_ticket_pdf(
    output_path: str,
    student_name: str,
    mobile_number: str,
    exam_center_name: str,
    qr_token: str,
    config: TicketConfig,
    district: str | None = None,
) -> None:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"प्रवेश प्रमाणपत्र - {student_name}")
    c.setAuthor(config.footer_text)
    generate_hall_ticket_page(c, student_name, mobile_number, exam_center_name, qr_token, config, district)
    c.showPage()
    draw_rules_page(c, config)
    c.showPage()
    c.save()

    # Write to a temporary file and atomically swap it in, so a student
    # downloading while the card is being (re)generated can never receive a
    # half-written PDF.
    out_dir = os.path.dirname(output_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(dir=out_dir, prefix=".tmp-", suffix=".pdf")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(buf.getvalue())
        os.replace(tmp_path, output_path)
    except BaseException:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise
