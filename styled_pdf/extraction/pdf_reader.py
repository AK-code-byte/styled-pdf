"""PDF text and metadata extraction using PyMuPDF."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class TextBlock:
    text: str
    bbox: tuple[float, float, float, float]  # x0, y0, x1, y1 in points
    font_name: str
    font_size: float
    is_bold: bool
    is_italic: bool
    color_hex: str  # e.g. "#1a2b3c"


@dataclass
class PageMetadata:
    page_num: int  # 1-indexed
    width: float   # in points
    height: float
    text_blocks: list[TextBlock] = field(default_factory=list)
    has_images: bool = False
    is_likely_scanned: bool = False


def _pack_to_hex(color_int: int) -> str:
    """Convert PyMuPDF packed int color to hex string."""
    r = (color_int >> 16) & 0xFF
    g = (color_int >> 8) & 0xFF
    b = color_int & 0xFF
    return f"#{r:02x}{g:02x}{b:02x}"


def extract_pages(pdf_path: str | Path) -> list[PageMetadata]:
    """Extract metadata for all pages in a PDF."""
    doc = fitz.open(str(pdf_path))
    pages: list[PageMetadata] = []

    for page_index in range(len(doc)):
        page = doc[page_index]
        rect = page.rect
        page_meta = PageMetadata(
            page_num=page_index + 1,
            width=rect.width,
            height=rect.height,
        )

        # Check for embedded images
        image_list = page.get_images(full=False)
        page_meta.has_images = len(image_list) > 0

        # Extract text blocks with font info
        raw = page.get_text("rawdict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        blocks: list[TextBlock] = []

        for block in raw.get("blocks", []):
            if block.get("type") != 0:  # type 0 = text
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "").strip()
                    if not text:
                        continue
                    flags = span.get("flags", 0)
                    blocks.append(TextBlock(
                        text=text,
                        bbox=tuple(span["bbox"]),
                        font_name=span.get("font", ""),
                        font_size=round(span.get("size", 12.0), 2),
                        is_bold=bool(flags & 2**4),   # bold flag
                        is_italic=bool(flags & 2**1),  # italic flag
                        color_hex=_pack_to_hex(span.get("color", 0)),
                    ))

        page_meta.text_blocks = blocks
        pages.append(page_meta)

    doc.close()
    return pages
