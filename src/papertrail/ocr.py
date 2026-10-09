from __future__ import annotations

from pathlib import Path

import pytesseract
from pdf2image import convert_from_path
from PIL import Image


IMAGE_EXTENSIONS: frozenset[str] = frozenset({
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".bmp",
})

PDF_EXTENSION = ".pdf"

DEFAULT_LANG = "rus+eng"

RUS_THRESHOLD = 0.8
ENG_THRESHOLD = 0.2


def _cyrillic_ratio(text: str) -> float | None:
    letters = [c for c in text if c.isalpha()]
    if not letters:
        return None
    cyrillic = sum(1 for c in letters if "\u0400" <= c <= "\u04FF")
    return cyrillic / len(letters)


def detect_language(text: str) -> str:
    ratio = _cyrillic_ratio(text)
    if ratio is None:
        return "unknown"
    if ratio > RUS_THRESHOLD:
        return "rus"
    if ratio < ENG_THRESHOLD:
        return "eng"
    return "mixed"


def extract_text_from_image(path: Path, lang: str = DEFAULT_LANG) -> str:
    with Image.open(path) as img:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        return pytesseract.image_to_string(img, lang=lang)


def extract_text_from_pdf(path: Path, lang: str = DEFAULT_LANG) -> str:
    pages = convert_from_path(str(path), dpi=200)
    parts: list[str] = []
    try:
        for page in pages:
            text = pytesseract.image_to_string(page, lang=lang)
            if text.strip():
                parts.append(text)
    finally:
        for page in pages:
            page.close()
    return "\n\n".join(parts)


def extract_text(path: Path, lang: str = DEFAULT_LANG) -> str:
    suffix = path.suffix.lower()
    if suffix == PDF_EXTENSION:
        return extract_text_from_pdf(path, lang=lang)
    if suffix in IMAGE_EXTENSIONS:
        return extract_text_from_image(path, lang=lang)
    return ""
