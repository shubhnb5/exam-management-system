from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from app.services.fonts import BODY, BODY_BOLD, ensure_fonts_registered

MARGIN = 36

RULE_ITEMS = [
    "<b>प्रवेश अनिवार्य:</b> परीक्षा केंद्रात प्रवेशासाठी हॉल तिकीटची छापील प्रत (Printed Hard Copy) सोबत असणे "
    "बंधनकारक आहे. प्रवेशपत्रावरील माहितीच्या आधारेच पडताळणी (Verification) केली जाईल.",
    "<b>सामायिक प्रवेशपत्र:</b> संपूर्ण सराव परीक्षा मालिकेसाठी (Test Series) हे एकच प्रवेशपत्र लागू असेल. "
    "प्रत्येक पेपरच्या वेळी विद्यार्थ्याने हेच प्रवेशपत्र सोबत आणावे.",
    "<b>प्रिंट गुणवत्ता:</b> प्रवेशपत्रावरील QR कोड स्कॅनिंगसाठी सुस्पष्ट असावा, यासाठी प्रिंटची गुणवत्ता "
    "(Good Quality) चांगली असावी.",
    "<b>रोल नंबर:</b> OMR शीटवर प्रवेशपत्रात नमूद केलेला ७ अंकी रोल नंबर (Roll No.) अचूक भरावा.",
    "<b>उपस्थिती:</b> परीक्षा सुरू होण्यापूर्वी किमान ३० मिनिटे अगोदर परीक्षा केंद्रावर हजर राहावे.",
    "<b>वेळापत्रक व अधिकार:</b> परीक्षेचे वेळापत्रक खालील तक्त्यात दिले आहे. अपरिहार्य कारणास्तव परीक्षा केंद्र "
    "किंवा वेळेत बदल करण्याचा अधिकार संस्थेने राखून ठेवला आहे.",
    "__UPDATES__",
    "सर्व यंत्रणा ऑनलाईन पद्धतीने असल्यामुळे विद्यार्थ्यांना केवळ त्यांच्या नियोजित वेळेत आणि नियोजित परीक्षा "
    "केंद्रावरच परीक्षा देता येईल.",
    "कुठल्याही परिस्थितीत उमेदवाराच्या परीक्षा केंद्रात आणि वेळेत तांत्रिक अडचणीच्या पार्श्वभूमीवर बदल करता येत नाही.",
]

PROHIBITED_TEXT = (
    "उमेदवारांनी परीक्षा कक्षेत प्रवेश केल्यावर आपले इलेक्ट्रॉनिक उपकरणे उदा. मोबाईल आणि हेडफोन्स बंद करून "
    "ठेवावेत. उमेदवारांना केवळ काळ्या शाईचे बॉल पेन आणि पाण्याची बॉटल परीक्षा कक्षात घेऊन जाण्याची परवानगी "
    "देण्यात आली आहे."
)


def _updates_text(config) -> str:
    if config.telegram_handle and config.website:
        return (
            f"<b>महत्त्वाचे अपडेट्स:</b> परीक्षेच्या माहितीसाठी व मदतीसाठी Telegram वर {config.telegram_handle} "
            f"सर्च करून चॅनल जॉईन करावे, तसेच {config.website} या संकेतस्थळाला नियमित भेट द्यावी."
        )
    return (
        "<b>महत्त्वाचे अपडेट्स:</b> परीक्षेच्या माहितीसाठी व मदतीसाठी आमच्या अधिकृत संकेतस्थळाला व सोशल "
        "मीडिया चॅनलला नियमित भेट द्यावी."
    )


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

    h1 = ParagraphStyle("h1", fontName=BODY_BOLD, fontSize=16, spaceAfter=10)
    h2 = ParagraphStyle("h2", fontName=BODY_BOLD, fontSize=11, spaceAfter=4)
    body = ParagraphStyle("body", fontName=BODY, fontSize=9.5, leading=14, spaceAfter=6)
    item_style = ParagraphStyle("item", fontName=BODY, fontSize=9.5, leading=14)
    small_bold = ParagraphStyle("small_bold", fontName=BODY_BOLD, fontSize=9.5, spaceAfter=8)

    story = [
        Paragraph("RULES &amp; REGULATIONS", h1),
        Paragraph("परीक्षार्थ्यांसाठी महत्त्वाच्या सूचना (Important Instructions)", h2),
        Paragraph("सर्वसाधारण सूचना:", small_bold),
    ]

    numbered = []
    for raw in RULE_ITEMS:
        text = _updates_text(config) if raw == "__UPDATES__" else raw
        numbered.append(ListItem(Paragraph(text, item_style), spaceAfter=8))

    story.append(
        ListFlowable(
            numbered,
            bulletType="1",
            start="1",
            leftIndent=18,
        )
    )

    story.append(Spacer(1, 10))
    story.append(Paragraph("Prohibited Items:", small_bold))
    story.append(Paragraph(PROHIBITED_TEXT, body))

    story.append(Spacer(1, 16))
    story.append(Paragraph("Best wishes for your examination!", body))
    story.append(Paragraph(config.org_name, ParagraphStyle("orgname", fontName=BODY_BOLD, fontSize=10)))
    story.append(Paragraph("Test Series Department", ParagraphStyle("dept", fontName=BODY, fontSize=9)))

    doc.build(story)
    buf.seek(0)
    return buf
