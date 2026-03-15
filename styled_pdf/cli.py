"""CLI entry point for styled-pdf."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .aggregation.html_assembler import assemble_document
from .output.writer import write_output
from .pipeline import run_pipeline


def parse_page_range(spec: str, total_pages: int) -> list[int]:
    """Parse a page range spec like '1-5' or '1,3,5' into a list of page numbers."""
    pages: set[int] = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            start, end = part.split("-", 1)
            pages.update(range(int(start), int(end) + 1))
        else:
            pages.add(int(part))
    return sorted(p for p in pages if 1 <= p <= total_pages)


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="styled-pdf",
        description="Extract semantic HTML+CSS from a styled PDF using Claude vision.",
    )
    parser.add_argument("pdf_file", type=Path, help="Path to the input PDF file")
    parser.add_argument(
        "-o", "--output", type=Path, default=None,
        help="Output HTML file path (default: <input>.html)",
    )
    parser.add_argument(
        "--external-css", action="store_true",
        help="Write CSS to a separate .css file",
    )
    parser.add_argument(
        "--pages", type=str, default=None,
        help="Page range to process, e.g. '1-5' or '2,4,7'",
    )
    parser.add_argument(
        "--dpi", type=int, default=150,
        help="Image render DPI (default: 150)",
    )
    parser.add_argument(
        "--concurrency", type=int, default=3,
        help="Max concurrent Claude API calls (default: 3)",
    )
    parser.add_argument(
        "--model", type=str, default="claude-sonnet-4-6",
        help="Claude model to use (default: claude-sonnet-4-6)",
    )
    parser.add_argument(
        "--max-tokens", type=int, default=4096,
        help="Max tokens per page response (default: 4096)",
    )
    parser.add_argument(
        "--api-key", type=str, default=None,
        help="Anthropic API key (or set ANTHROPIC_API_KEY env var)",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Save intermediate images and raw responses to ./debug/",
    )
    parser.add_argument(
        "--verbose", action="store_true", default=True,
        help="Show per-page progress (default: on)",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress progress output",
    )

    args = parser.parse_args()

    # Configure logging
    if not args.quiet:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    # Validate input
    pdf_path: Path = args.pdf_file
    if not pdf_path.exists():
        print(f"Error: File not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    # Determine output path
    output_path: Path = args.output or pdf_path.with_suffix(".html")

    # Resolve API key
    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print(
            "Error: No API key found. Set ANTHROPIC_API_KEY or use --api-key.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Debug directory
    debug_dir: Path | None = Path("debug") if args.debug else None

    # Parse page range (we don't know total pages yet; parse after extraction)
    page_range_spec = args.pages

    # Run pipeline
    async def run():
        import fitz
        doc = fitz.open(str(pdf_path))
        total_pages = len(doc)
        doc.close()

        page_range: list[int] | None = None
        if page_range_spec:
            page_range = parse_page_range(page_range_spec, total_pages)
            if not page_range:
                print("Error: No valid pages in the specified range.", file=sys.stderr)
                sys.exit(1)

        results = await run_pipeline(
            pdf_path=pdf_path,
            api_key=api_key,
            model=args.model,
            max_tokens=args.max_tokens,
            dpi=args.dpi,
            concurrency=args.concurrency,
            page_range=page_range,
            debug_dir=debug_dir,
        )

        css_filename = output_path.with_suffix(".css").name
        html, css = assemble_document(
            page_results=results,
            title=pdf_path.stem,
            external_css=args.external_css,
            css_path=css_filename,
        )

        write_output(
            html=html,
            css=css,
            output_path=output_path,
            external_css=args.external_css,
        )

    asyncio.run(run())


if __name__ == "__main__":
    main()
