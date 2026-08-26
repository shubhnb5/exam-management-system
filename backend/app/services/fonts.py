import os

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

_FONTS_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "ticket_template", "fonts")

BODY = "Body"
BODY_BOLD = "Body-Bold"

_registered = False


def ensure_fonts_registered():
    global _registered
    if _registered:
        return
    pdfmetrics.registerFont(TTFont(BODY, os.path.join(_FONTS_DIR, "NotoSansDevanagari-Regular.ttf")))
    pdfmetrics.registerFont(TTFont(BODY_BOLD, os.path.join(_FONTS_DIR, "NotoSansDevanagari-Bold.ttf")))
    _registered = True
