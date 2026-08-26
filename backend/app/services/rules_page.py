from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from app.services.devanagari_shaping import ShapedParagraphFlowable, contains_devanagari
from app.services.fonts import BODY, BODY_BOLD, FONT_PATHS, ensure_fonts_registered

MARGIN = 36

RULE_ITEMS = [
    "प्रत्येक विद्यार्थ्याने हॉल तिकीट ची छापील प्रत स्वतःबरोबर आणणे बंधनकारक आहे.",
    "छापील हॉल तिकीट शिवाय कोणालाही प्रवेश दिला जाणार नाही.",
    "परीक्षा केंद्रावर दिलेल्या वेळेच्या अर्धा तास अगोदर उपस्थित राहणे अनिवार्य आहे.",
    "परीक्षेसंबंधी काही शंका असल्यास अगोदरच ऑफिसशी संपर्क साधणे आवश्यक आहे.",
    "टेस्ट सिरीज च्या वेळापत्रकात बदल केल्यास तशी पूर्वसूचना विद्यार्थ्यांना देण्यात येईल.",
    "सर्व अधिकार Combine Mentor Official कडे राखीव असतील.",
]


def _flowable(text: str, font_name: str, font_size: float, leading: float | None = None):
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
    return Paragraph(text, ParagraphStyle(f"flow-{font_name}-{font_size}", **style_kwargs))


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

    story = [
        Paragraph("RULES &amp; REGULATIONS", ParagraphStyle("h1", fontName=BODY_BOLD, fontSize=16, spaceAfter=10)),
    ]

    numbered = [ListItem(_flowable(text, BODY, 9.5, leading=14), spaceAfter=8) for text in RULE_ITEMS]

    story.append(
        ListFlowable(
            numbered,
            bulletType="1",
            start="1",
            leftIndent=18,
        )
    )

    story.append(Spacer(1, 16))
    story.append(_flowable("Best wishes for your examination!", BODY, 9.5, leading=14))
    story.append(_flowable(config.org_name, BODY_BOLD, 10))
    story.append(_flowable("Test Series Department", BODY, 9))

    doc.build(story)
    buf.seek(0)
    return buf
