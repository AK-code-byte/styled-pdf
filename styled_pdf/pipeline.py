"""Main pipeline: orchestrates PDF → HTML conversion."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

from tqdm import tqdm

from .analysis.claude_client import ClaudeClient
from .analysis.page_analyzer import PageResult, analyze_page
from .extraction.image_renderer import render_all_pages
from .extraction.ocr_detector import mark_scanned_pages
from .extraction.pdf_reader import extract_pages

logger = logging.getLogger(__name__)


async def run_pipeline(
    pdf_path: Path,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-6",
    max_tokens: int = 4096,
    dpi: int = 150,
    concurrency: int = 3,
    page_range: list[int] | None = None,
    debug_dir: Path | None = None,
) -> list[PageResult]:
    """Run the full PDF → HTML pipeline and return per-page results.

    Args:
        pdf_path: Path to the input PDF.
        api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var).
        model: Claude model ID.
        max_tokens: Max tokens per Claude response.
        dpi: Render DPI for page images.
        concurrency: Max simultaneous Claude API calls.
        page_range: 1-indexed list of pages to process. None = all pages.
        debug_dir: If set, save debug artifacts (images, raw responses) here.
    """
    # Stage 1: Extract PDF metadata
    logger.info("Extracting PDF metadata...")
    all_pages = extract_pages(pdf_path)
    all_pages = mark_scanned_pages(all_pages)

    # Filter to requested page range
    if page_range:
        pages = [p for p in all_pages if p.page_num in page_range]
    else:
        pages = all_pages

    if not pages:
        raise ValueError("No pages to process.")

    total_pages = len(all_pages)

    # Stage 2: Render page images
    logger.info("Rendering %d page(s) at %d DPI...", len(pages), dpi)
    all_images = render_all_pages(pdf_path, dpi=dpi)
    # all_images is 0-indexed; page_num is 1-indexed
    page_images = {p.page_num: all_images[p.page_num - 1] for p in pages}

    # Debug: save images
    if debug_dir:
        debug_dir.mkdir(parents=True, exist_ok=True)
        import base64
        for page_num, b64 in page_images.items():
            img_path = debug_dir / f"page_{page_num}_image.png"
            img_path.write_bytes(base64.standard_b64decode(b64))

    # Stage 3-4: Analyze pages with Claude
    client = ClaudeClient(api_key=api_key, model=model, max_tokens=max_tokens)
    semaphore = asyncio.Semaphore(concurrency)
    results: list[PageResult] = []
    style_tokens: dict | None = None

    async def process_page(page_meta, image_b64):
        nonlocal style_tokens
        async with semaphore:
            result = await analyze_page(
                client=client,
                page_meta=page_meta,
                base64_image=image_b64,
                total_pages=total_pages,
                style_tokens=style_tokens if page_meta.page_num > pages[0].page_num else None,
            )
            return result

    with tqdm(total=len(pages), desc="Analyzing pages", unit="page") as pbar:
        # Process page 1 first to extract style tokens for continuity
        first_page = pages[0]
        first_result = await process_page(first_page, page_images[first_page.page_num])
        results.append(first_result)
        if first_result.style_tokens:
            style_tokens = first_result.style_tokens
        pbar.update(1)

        if debug_dir:
            (debug_dir / f"page_{first_page.page_num}_response.json").write_text(
                json.dumps({"html": first_result.html, "css": first_result.css,
                            "style_tokens": first_result.style_tokens}, indent=2),
                encoding="utf-8",
            )

        # Process remaining pages concurrently
        remaining = pages[1:]
        if remaining:
            tasks = [
                process_page(p, page_images[p.page_num])
                for p in remaining
            ]
            for coro in asyncio.as_completed(tasks):
                result = await coro
                results.append(result)
                pbar.update(1)

                if debug_dir:
                    (debug_dir / f"page_{result.page_num}_response.json").write_text(
                        json.dumps({"html": result.html, "css": result.css,
                                    "style_tokens": result.style_tokens}, indent=2),
                        encoding="utf-8",
                    )

    await client.close()
    return results
