"""Page 2 of the admit card: "अत्यंत महत्वाचे" notes and "उमेदवारांना सूचना"
instructions, laid out like the approved sample. Text comes from
ticket_template/config.json; **double asterisks** mark bold phrases inside an
instruction."""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.services.devanagari_shaping import measure_shaped_width_pt, render_shaped_png
from app.services.fonts import BODY, BODY_BOLD, FONT_PATHS, ensure_fonts_registered
from app.services.pdf_images import draw_png

PAGE_W, PAGE_H = A4
TEXT_LEFT = 42.5
TEXT_WIDTH = 552.4 - 42.5


def draw_page_footer(c: canvas.Canvas, footer_text: str):
    """Full-width rule and right-aligned organisation name at the bottom of
    both pages."""
    c.setFillColor(colors.black)
    c.rect(0, PAGE_H - 806.2, PAGE_W, 1.5, stroke=0, fill=1)
    if footer_text:
        size, char_space = 9.49, 0.45
        t = c.beginText()
        t.setFont("Helvetica-Bold", size)
        t.setCharSpace(char_space)
        width = c.stringWidth(footer_text, "Helvetica-Bold", size) + char_space * (len(footer_text) - 1)
        t.setTextOrigin(586.3 - width, PAGE_H - 822.78)
        t.textOut(footer_text)
        c.drawText(t)


def _runs(text: str, default_font: str) -> list[tuple[str, str]]:
    """Splits "plain **bold** plain" into (word, font) tokens."""
    tokens: list[tuple[str, str]] = []
    for i, part in enumerate(text.split("**")):
        font = BODY_BOLD if i % 2 else default_font
        tokens.extend((word, font) for word in part.split())
    return tokens


def _wrap_tokens(tokens, size: float, max_width: float):
    lines, current, width = [], [], 0.0
    for word, font in tokens:
        w = measure_shaped_width_pt(word, FONT_PATHS[font], size)
        space = measure_shaped_width_pt(" ", FONT_PATHS[font], size) if current else 0
        if current and width + space + w > max_width:
            lines.append(current)
            current, width = [], 0.0
            space = 0
        current.append((word, font))
        width += space + w
    if current:
        lines.append(current)
    return lines


def _draw_token_line(c: canvas.Canvas, tokens, size: float, x: float, baseline: float):
    """Draws a line made of runs in different fonts (regular/bold), each run
    shaped separately and placed one after the other."""
    runs: list[list] = []
    for word, font in tokens:
        if runs and runs[-1][1] == font:
            runs[-1][0] += " " + word
        else:
            runs.append([word, font])
    for i, (text, font) in enumerate(runs):
        path = FONT_PATHS[font]
        if i:
            x += measure_shaped_width_pt(" ", path, size)
        png, w, h, base = render_shaped_png(text, path, size)
        draw_png(c, png, x, PAGE_H - baseline - (h - base), w, h)
        x += measure_shaped_width_pt(text, path, size)


def _draw_centered(c: canvas.Canvas, text: str, font: str, size: float, baseline: float):
    png, w, h, base = render_shaped_png(text, FONT_PATHS[font], size)
    draw_png(c, png, PAGE_W / 2 - w / 2, PAGE_H - baseline - (h - base), w, h)


def draw_rules_page(c: canvas.Canvas, config):
    """Draws page 2 onto the current page of `c`."""
    ensure_fonts_registered()

    _draw_centered(c, "-: अत्यंत महत्वाचे :-", BODY_BOLD, 12, 39.0)
    baseline = 66.03
    for note in config.important_notes:
        for line in _wrap_tokens(_runs(note, BODY_BOLD), 9.0, TEXT_WIDTH):
            _draw_token_line(c, line, 9.0, TEXT_LEFT, baseline)
            baseline += 13.5
        baseline += 0.7

    _draw_centered(c, "-: उमेदवारांना सूचना :-", BODY_BOLD, 12, 146.2)
    baseline = 174.04
    for item in config.instructions:
        for line in _wrap_tokens(_runs(item, BODY), 10.2, TEXT_WIDTH):
            _draw_token_line(c, line, 10.2, TEXT_LEFT, baseline)
            baseline += 16.31

    draw_page_footer(c, config.footer_text)
