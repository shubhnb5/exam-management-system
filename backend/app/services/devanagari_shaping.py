"""Proper Devanagari text shaping for PDF generation.

reportlab has no OpenType shaping engine (no HarfBuzz), so it draws Devanagari
glyph-by-glyph in raw Unicode storage order — it cannot form real
conjuncts/ligatures, e.g. "र" + halant + "व" never becomes the proper
subjoined "र्व" form, it just draws a full "र" with a detached halant mark
next to "व". Fixing that requires an actual shaping engine, so this module
shapes text with HarfBuzz, rasterizes the shaped glyphs with FreeType, and
hands callers a ready-to-embed image plus the metrics needed to position it
exactly like reportlab would position a text baseline.

Two reportlab Flowables are provided for drop-in use wherever a `Paragraph`
would otherwise mangle Indic text: `ShapedTextFlowable` for single-line table
cells, and `ShapedParagraphFlowable` for multi-line word-wrapped paragraphs
(list items, body text).
"""

import re
from io import BytesIO

import freetype
import uharfbuzz as hb
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Flowable

_DEVANAGARI_RE = re.compile(r"[ऀ-ॿ]")

# Rasterize at a fixed, generously large pixel size and scale the result down
# to the requested point size afterwards — keeps output crisp regardless of
# the final font size.
_RENDER_PX = 200

_hb_font_cache: dict[str, tuple[hb.Font, int]] = {}
_ft_face_cache: dict[str, freetype.Face] = {}


def contains_devanagari(text: str) -> bool:
    return bool(_DEVANAGARI_RE.search(text or ""))


def _get_hb_font(font_path: str) -> tuple[hb.Font, int]:
    cached = _hb_font_cache.get(font_path)
    if cached:
        return cached
    with open(font_path, "rb") as f:
        face = hb.Face(f.read())
    font = hb.Font(face)
    upem = face.upem
    font.scale = (upem, upem)
    _hb_font_cache[font_path] = (font, upem)
    return font, upem


def _get_ft_face(font_path: str) -> freetype.Face:
    face = _ft_face_cache.get(font_path)
    if face is None:
        face = freetype.Face(font_path)
        _ft_face_cache[font_path] = face
    return face


def _shape_to_mask(text: str, font_path: str) -> tuple[Image.Image, float]:
    """Shapes `text` and rasterizes it into a tightly-cropped single-channel
    (alpha) image at `_RENDER_PX`. Returns (image, baseline_offset_px) where
    baseline_offset_px is the distance from the image's top edge down to the
    text baseline."""
    hb_font, upem = _get_hb_font(font_path)
    ft_face = _get_ft_face(font_path)
    ft_face.set_pixel_sizes(0, _RENDER_PX)
    scale = _RENDER_PX / upem

    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf)

    pen_x = 0.0
    glyphs = []
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        ft_face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER)
        slot = ft_face.glyph
        bmp = slot.bitmap
        # Copy bitmap data out immediately — FreeType reuses one glyph slot
        # across load_glyph() calls, so deferring this read would make every
        # glyph end up reflecting whichever glyph was loaded last.
        w, rows, pitch = bmp.width, bmp.rows, bmp.pitch
        data = bytes(bmp.buffer)
        left, top = slot.bitmap_left, slot.bitmap_top
        gx = pen_x + pos.x_offset * scale
        gy = pos.y_offset * scale
        glyphs.append((w, rows, pitch, data, left, top, gx, gy))
        pen_x += pos.x_advance * scale

    ascent = ft_face.size.ascender / 64
    descent = ft_face.size.descender / 64
    canvas_w = max(int(round(pen_x)), 1)
    canvas_h = max(int(round(ascent - descent)), 1)
    baseline_y = ascent

    mask = Image.new("L", (canvas_w, canvas_h), 0)
    for w, rows, pitch, data, left, top, gx, gy in glyphs:
        if w == 0 or rows == 0:
            continue
        glyph_img = Image.frombuffer("L", (w, rows), data, "raw", "L", pitch, 1)
        px = int(round(gx)) + left
        py = int(round(baseline_y)) - top - int(round(gy))
        mask.paste(glyph_img, (px, py), glyph_img)

    return mask, baseline_y


def render_shaped_png(text: str, font_path: str, font_size_pt: float) -> tuple[bytes, float, float, float]:
    """Shapes and rasterizes `text`, returning
    (png_bytes, width_pt, height_pt, baseline_from_top_pt) scaled to
    `font_size_pt`. The PNG is black-on-transparent, ready for `drawImage`."""
    mask, baseline_px = _shape_to_mask(text, font_path)
    pt_per_px = font_size_pt / _RENDER_PX

    rgba = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    black = Image.new("RGBA", mask.size, (0, 0, 0, 255))
    rgba.paste(black, (0, 0), mask)

    buf = BytesIO()
    rgba.save(buf, format="PNG")
    return (
        buf.getvalue(),
        mask.width * pt_per_px,
        mask.height * pt_per_px,
        baseline_px * pt_per_px,
    )


def measure_shaped_width_pt(text: str, font_path: str, font_size_pt: float) -> float:
    """Shapes `text` and returns its advance width in points, without
    rasterizing — used for word-wrapping, where many candidate line widths
    need to be checked before settling on where to actually break."""
    hb_font, upem = _get_hb_font(font_path)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(hb_font, buf)
    total_units = sum(pos.x_advance for pos in buf.glyph_positions)
    return (total_units / upem) * font_size_pt


def wrap_shaped_lines(text: str, font_path: str, font_size_pt: float, max_width_pt: float) -> list[str]:
    """Greedily word-wraps `text` to fit within `max_width_pt`, measuring each
    candidate line with the real shaped width rather than a per-character
    estimate. A single word wider than max_width_pt is kept on its own line
    rather than split (no mid-word hyphenation)."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}" if current else word
        if not current or measure_shaped_width_pt(candidate, font_path, font_size_pt) <= max_width_pt:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines or [""]


class ShapedTextFlowable(Flowable):
    """A single-line reportlab Flowable for Devanagari table-cell text,
    standing in for `Paragraph` wherever reportlab's own text drawing would
    mangle Indic conjuncts. Does not wrap across multiple lines — if the
    shaped text is wider than the available cell width it's scaled down to
    fit rather than clipped or wrapped."""

    def __init__(self, text: str, font_path: str, font_size: float):
        super().__init__()
        self.png_bytes, self.img_w, self.img_h, self.baseline = render_shaped_png(text, font_path, font_size)
        self.leading = font_size * 1.35

    def wrap(self, available_width, available_height):
        if self.img_w > available_width > 0:
            shrink = available_width / self.img_w
            self.img_w *= shrink
            self.img_h *= shrink
            self.baseline *= shrink
        self.width = self.img_w
        self.height = max(self.leading, self.img_h)
        return self.width, self.height

    def draw(self):
        y = (self.height - self.img_h) / 2
        self.canv.drawImage(
            ImageReader(BytesIO(self.png_bytes)), 0, y, width=self.img_w, height=self.img_h, mask="auto"
        )


class ShapedParagraphFlowable(Flowable):
    """A word-wrapped, multi-line reportlab Flowable for Devanagari body text
    (list items, paragraphs) — standing in for `Paragraph` wherever the text
    needs to flow across several lines. Each line is shaped and rasterized
    independently; wrapping decisions are made from real shaped widths, not a
    per-character width estimate, so it wraps at the same point a human
    reader would expect."""

    def __init__(self, text: str, font_path: str, font_size: float, leading: float | None = None):
        super().__init__()
        self.text = text
        self.font_path = font_path
        self.font_size = font_size
        self.leading = leading or font_size * 1.45
        self._lines: list[tuple[bytes, float, float, float]] = []

    def wrap(self, available_width, available_height):
        line_texts = wrap_shaped_lines(self.text, self.font_path, self.font_size, available_width)
        self._lines = [render_shaped_png(t, self.font_path, self.font_size) for t in line_texts]
        self.width = available_width
        self.height = self.leading * len(self._lines)
        return self.width, self.height

    def draw(self):
        y = self.height - self.leading
        for png_bytes, w, h, _baseline in self._lines:
            self.canv.drawImage(
                ImageReader(BytesIO(png_bytes)), 0, y + (self.leading - h) / 2, width=w, height=h, mask="auto"
            )
            y -= self.leading
