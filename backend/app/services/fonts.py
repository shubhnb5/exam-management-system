import os

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ticket_template", "fonts")

BODY = "Body"
BODY_BOLD = "Body-Bold"
# Noto Serif Devanagari: the admit card's timetable cells (e.g. "सकाळी 9.30").
SERIF_DEVA = "SerifDeva"

BODY_PATH = os.path.join(_FONTS_DIR, "NotoSansDevanagari-Regular.ttf")
BODY_BOLD_PATH = os.path.join(_FONTS_DIR, "NotoSansDevanagari-Bold.ttf")
SERIF_DEVA_PATH = os.path.join(_FONTS_DIR, "NotoSerifDevanagari-Regular.ttf")

FONT_PATHS = {BODY: BODY_PATH, BODY_BOLD: BODY_BOLD_PATH, SERIF_DEVA: SERIF_DEVA_PATH}

_registered = False


def ensure_fonts_registered():
    global _registered
    if _registered:
        return
    for name, path in FONT_PATHS.items():
        pdfmetrics.registerFont(TTFont(name, path))
    _registered = True
