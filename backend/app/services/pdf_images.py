"""Reuses encoded PDF images across admit cards.

Every card draws the same ~100 small images (shaped Devanagari labels,
timetable text, header banner, stamp). reportlab normally decodes and
re-compresses each image for every new PDF, which made that the slowest part
of generating a card. Here each image is encoded once per process and the
same (read-only) image object is registered in every card's PDF — the output
is byte-for-byte the same image, just without the repeated work."""

import hashlib
import os
import threading
from io import BytesIO

from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfdoc
from reportlab.pdfgen import canvas

_cache: dict[str, tuple[str, pdfdoc.PDFImageXObject, object]] = {}
_lock = threading.Lock()
_MAX_ENTRIES = 1000  # ~100 are the fixed template; the rest are per-student (e.g. Marathi names)


def _build(key: str, source) -> tuple[str, pdfdoc.PDFImageXObject, object]:
    name = f"cached{key}"
    img = pdfdoc.PDFImageXObject(name, source, mask="auto")
    img.name = name
    smask = getattr(img, "_smask", None)
    if smask is not None:
        del img._smask
    return name, img, smask


def _entry(key: str, make_source):
    entry = _cache.get(key)
    if entry is None:
        with _lock:
            entry = _cache.get(key)
            if entry is None:
                entry = _build(key, make_source())
                if len(_cache) >= _MAX_ENTRIES:
                    _cache.clear()
                _cache[key] = entry
    return entry


def _register(doc, obj, reg_name: str):
    """Adds an already-built object to this document under `reg_name` (what
    pdfdoc.Reference does for a new object; Reference itself refuses objects
    that were first registered in another document)."""
    if reg_name in doc.idToObject:
        return
    number = doc.objectcounter = doc.objectcounter + 1
    doc.idToObjectNumberAndVersion[reg_name] = (number, 0)
    doc.numberToId[number] = reg_name
    doc.idToObject[reg_name] = obj


def _place(c: canvas.Canvas, entry, x: float, y: float, width: float, height: float):
    name, img, smask = entry
    doc = c._doc
    reg_name = doc.getXObjectName(name)
    if reg_name not in doc.idToObject:
        if smask is not None:
            mask_reg_name = doc.getXObjectName(smask.name)
            _register(doc, smask, mask_reg_name)
            # A name reference (resolved per document), so sharing is safe.
            img.smask = pdfdoc.PDFObjectReference(mask_reg_name)
        _register(doc, img, reg_name)
    c._currentPageHasImages = 1
    c.saveState()
    c.translate(x, y)
    c.scale(width, height)
    c._code.append(f"/{reg_name} Do")
    c.restoreState()
    c._formsinuse.append(name)


def draw_png(c: canvas.Canvas, png_bytes: bytes, x: float, y: float, width: float, height: float):
    """Draws in-memory PNG bytes (e.g. shaped text) at (x, y) with the given size."""
    key = hashlib.md5(png_bytes).hexdigest()
    _place(c, _entry(key, lambda: ImageReader(BytesIO(png_bytes))), x, y, width, height)


def draw_file(c: canvas.Canvas, path: str, x: float, y: float, width: float, height: float):
    """Draws an image file (JPEG/PNG); re-encoded only if the file changes."""
    stat = os.stat(path)
    key = hashlib.md5(f"{os.path.abspath(path)}|{stat.st_mtime_ns}|{stat.st_size}".encode()).hexdigest()
    _place(c, _entry(key, lambda: path), x, y, width, height)
