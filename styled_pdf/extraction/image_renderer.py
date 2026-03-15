"""Render PDF pages to base64-encoded PNG images."""

from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path

from pdf2image import convert_from_path


def render_page_as_base64(
    pdf_path: str | Path,
    page_num: int,
    dpi: int = 150,
) -> str:
    """Render a single PDF page (1-indexed) to a base64 PNG string."""
    images = convert_from_path(
        str(pdf_path),
        dpi=dpi,
        first_page=page_num,
        last_page=page_num,
    )
    buf = BytesIO()
    images[0].save(buf, format="PNG")
    return base64.standard_b64encode(buf.getvalue()).decode()


def render_all_pages(
    pdf_path: str | Path,
    dpi: int = 150,
) -> list[str]:
    """Render all pages and return list of base64 PNG strings (1-indexed order)."""
    images = convert_from_path(str(pdf_path), dpi=dpi)
    result = []
    for img in images:
        buf = BytesIO()
        img.save(buf, format="PNG")
        result.append(base64.standard_b64encode(buf.getvalue()).decode())
    return result
