from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.devanagari_shaping import ShapedParagraphFlowable, contains_devanagari
from app.services.fonts import BODY, BODY_BOLD, FONT_PATHS, ensure_fonts_registered

ORG_BLUE = colors.Color(0.06, 0.22, 0.60)
DEPT_GREY = colors.Color(0.35, 0.35, 0.35)

MARGIN = 36

RULE_ITEMS = [
    "प्रत्येक विद्यार्थ्याने हॉल तिकीट ची छापील प्रत स्वतःबरोबर आणणे बंधनकारक आहे.",
    "छापील हॉल तिकीट शिवाय कोणालाही प्रवेश दिला जाणार नाही.",
    "परीक्षा केंद्रावर दिलेल्या वेळेच्या अर्धा तास अगोदर उपस्थित राहणे अनिवार्य आहे.",
    "परीक्षेसंबंधी काही शंका असल्यास अगोदरच ऑफिसशी संपर्क साधणे आवश्यक आहे.",
    "टेस्ट सिरीज च्या वेळापत्रकात बदल केल्यास तशी पूर्वसूचना विद्यार्थ्यांना देण्यात येईल.",
    "सर्व अधिकार Combine Mentor Official कडे राखीव असतील.",
]


def _flowable(text: str, font_name: str, font_size: float, leading: float | None = None, color=None):
    """Paragraph, or a HarfBuzz-shaped+word-wrapped equivalent when the text
    contains Devanagari — reportlab's own Paragraph can't shape Indic
    conjuncts (see devanagari_shaping.py), so plain Paragraph is only safe for
    non-Devanagari text."""
    text = str(text)
    if contains_devanagari(text):
        return ShapedParagraphFlowable(text, FONT_PATHS[font_name], font_size, leading=leading)
    style_kwargs = {"fontName": font_name, "fontSize": font_size}
    if leading is not None:
        style_kwargs["leading"] = leading
    if color is not None:
        style_kwargs["textColor"] = color
    return Paragraph(text, ParagraphStyle(f"flow-{font_name}-{font_size}-{color}", **style_kwargs))


def build_rules_page_pdf(config) -> BytesIO:
    ensure_fonts_registered()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN,
    )

    heading_w = A4[0] - 2 * MARGIN
    heading_table = Table(
        [[Paragraph("RULES &amp; REGULATIONS", ParagraphStyle("h1box", fontName=BODY_BOLD, fontSize=16, alignment=TA_CENTER))]],
        colWidths=[heading_w],
    )
    heading_table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.3, colors.black),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 9),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )

    story = [heading_table, Spacer(1, 16)]

    numbered = [ListItem(_flowable(text, BODY, 9.5, leading=14), spaceAfter=8) for text in RULE_ITEMS]

    story.append(
        ListFlowable(
            numbered,
            bulletType="1",
            start="1",
            leftIndent=18,
        )
    )

    story.append(Spacer(1, 20))
    story.append(_flowable("Best wishes for your examination!", BODY_BOLD, 12, leading=16))
    story.append(Spacer(1, 8))
    story.append(_flowable(config.org_name, BODY_BOLD, 14, leading=17, color=ORG_BLUE))
    story.append(Spacer(1, 4))
    story.append(_flowable("Test Series Department", BODY, 10.5, leading=13, color=DEPT_GREY))

    doc.build(story)
    buf.seek(0)
    return buf
