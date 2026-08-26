import os

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ticket_template", "fonts")

BODY = "Body"
BODY_BOLD = "Body-Bold"

BODY_PATH = os.path.join(_FONTS_DIR, "NotoSansDevanagari-Regular.ttf")
BODY_BOLD_PATH = os.path.join(_FONTS_DIR, "NotoSansDevanagari-Bold.ttf")

FONT_PATHS = {BODY: BODY_PATH, BODY_BOLD: BODY_BOLD_PATH}

_registered = False


def ensure_fonts_registered():
    global _registered
    if _registered:
        return
    pdfmetrics.registerFont(TTFont(BODY, BODY_PATH))
    pdfmetrics.registerFont(TTFont(BODY_BOLD, BODY_BOLD_PATH))
    _registered = True
