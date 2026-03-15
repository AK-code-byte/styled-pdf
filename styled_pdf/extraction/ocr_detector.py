"""Heuristic to detect whether a PDF page needs OCR (i.e., is scanned/image-based)."""

from __future__ import annotations

from .pdf_reader import PageMetadata

# If fewer than this many characters are extracted from a non-blank page,
# treat it as scanned.
SCANNED_TEXT_THRESHOLD = 50


def mark_scanned_pages(pages: list[PageMetadata]) -> list[PageMetadata]:
    """Set is_likely_scanned on pages where text extraction is sparse."""
    for page in pages:
        total_chars = sum(len(b.text) for b in page.text_blocks)
        page.is_likely_scanned = total_chars < SCANNED_TEXT_THRESHOLD
    return pages
