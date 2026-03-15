"""Assemble per-page HTML fragments into a complete HTML document."""

from __future__ import annotations

from ..analysis.page_analyzer import PageResult
from .css_merger import merge_css


def assemble_document(
    page_results: list[PageResult],
    title: str = "PDF Document",
    external_css: bool = False,
    css_path: str = "output.css",
) -> tuple[str, str]:
    """Assemble page results into (html_string, css_string).

    If external_css is True, the HTML will link to css_path instead of
    embedding a <style> block.
    """
    # Sort pages by page_num in case async processing returned out of order
    sorted_pages = sorted(page_results, key=lambda r: r.page_num)

    # Merge all CSS
    merged_css = merge_css([r.css for r in sorted_pages if r.css])

    # Build page divs
    page_divs = "\n\n".join(r.html for r in sorted_pages)

    # Build style section
    if external_css:
        style_section = f'  <link rel="stylesheet" href="{css_path}">'
    else:
        style_section = f"  <style>\n{_indent(merged_css, 4)}\n  </style>"

    html = f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_escape_html(title)}</title>
{style_section}
</head>
<body class="pdf-document">

{_indent(page_divs, 0)}

</body>
</html>
"""
    return html, merged_css


def _indent(text: str, spaces: int) -> str:
    if not spaces:
        return text
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in text.splitlines())


def _escape_html(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
