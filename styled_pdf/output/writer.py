"""Write HTML and CSS output files."""

from __future__ import annotations

from pathlib import Path


def write_output(
    html: str,
    css: str,
    output_path: Path,
    external_css: bool = False,
) -> None:
    """Write HTML (and optionally CSS) to disk."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html, encoding="utf-8")

    if external_css and css:
        css_path = output_path.with_suffix(".css")
        css_path.write_text(css, encoding="utf-8")
        print(f"CSS written to: {css_path}")

    print(f"HTML written to: {output_path}")
