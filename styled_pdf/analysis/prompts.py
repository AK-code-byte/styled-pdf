"""Prompt templates for Claude page analysis."""

from __future__ import annotations

import json
from dataclasses import asdict

from ..extraction.pdf_reader import PageMetadata

SYSTEM_PROMPT = """\
You are an expert HTML/CSS developer specializing in converting PDF page images \
into pixel-accurate semantic HTML. You receive a PDF page as an image and optionally \
pre-extracted text metadata with font information.

Rules:
- Output ONLY a valid JSON object. No prose, no markdown fences, no extra text.
- JSON schema: {"html": "<string>", "css": "<string>", "style_tokens": {...}}
- html: A single <div class="page page-N"> fragment. No <html>, <head>, or <body> tags.
- css: All CSS rules needed for this page's html. Use BEM-style class names.
- style_tokens: {"fonts": ["font-name", ...], "colors": ["#hex", ...], "heading_classes": ["class-name", ...]}
- Use semantic elements: <h1>-<h6>, <p>, <ul>, <ol>, <table>, <figure>, <aside>, <nav>, <header>, <footer>.
- Multi-column layouts: use CSS Grid or Flexbox, NOT <table> for layout.
- Data tables: use proper <table><thead><tbody><tr><th><td> structure.
- Font sizes: convert visual size to rem units (base 16px). E.g. 24pt ≈ 2rem.
- Colors: extract exact hex values from the image.
- Preserve all text content exactly as it appears.
- For images/figures: use <figure><img alt="description"></figure>.
- Spacing: use margin/padding in rem or px that visually matches the original.
- Do NOT use inline styles. All styling goes in the css field.
"""


def build_user_prompt(
    page_meta: PageMetadata,
    total_pages: int,
    style_tokens: dict | None = None,
) -> str:
    """Build the user prompt for a text-based or scanned page."""
    parts: list[str] = []
    parts.append(f"Page {page_meta.page_num} of {total_pages}.")
    parts.append(f"Page dimensions: {page_meta.width:.1f}pt × {page_meta.height:.1f}pt.")

    if style_tokens:
        parts.append(
            "\nEstablished style tokens from this document (reuse these exact class names "
            "and values where applicable):\n" + json.dumps(style_tokens, indent=2)
        )

    if page_meta.is_likely_scanned:
        parts.append(
            "\nThis is a scanned/image-based page. No pre-extracted text is available. "
            "Use the image as the sole source of truth. Extract all text via visual recognition."
        )
    else:
        meta_dict = {
            "text_blocks": [
                {
                    "text": b.text,
                    "bbox": b.bbox,
                    "font_name": b.font_name,
                    "font_size": b.font_size,
                    "is_bold": b.is_bold,
                    "is_italic": b.is_italic,
                    "color": b.color_hex,
                }
                for b in page_meta.text_blocks
            ],
            "has_images": page_meta.has_images,
        }
        parts.append(
            "\nPre-extracted text and layout metadata from the PDF parser "
            "(use font names/sizes as authoritative values; image is ground truth for layout and color):\n"
            + json.dumps(meta_dict, indent=2)
        )

    parts.append(
        f"\nConvert this page to semantic HTML + CSS. "
        f"Wrap everything in <div class=\"page page-{page_meta.page_num}\">."
    )

    return "\n".join(parts)


def build_retry_prompt() -> str:
    return (
        "Your previous response was not valid JSON. "
        "Return ONLY the JSON object with keys 'html', 'css', and 'style_tokens'. "
        "No markdown fences, no extra text."
    )
