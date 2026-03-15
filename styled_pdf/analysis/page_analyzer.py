"""Per-page analysis: combine image + metadata and call Claude."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from ..extraction.pdf_reader import PageMetadata
from .claude_client import ClaudeClient
from .prompts import SYSTEM_PROMPT, build_retry_prompt, build_user_prompt

logger = logging.getLogger(__name__)


@dataclass
class PageResult:
    page_num: int
    html: str
    css: str
    style_tokens: dict
    error: str | None = None


async def analyze_page(
    client: ClaudeClient,
    page_meta: PageMetadata,
    base64_image: str,
    total_pages: int,
    style_tokens: dict | None = None,
) -> PageResult:
    """Analyze a single page and return HTML/CSS fragments."""
    user_prompt = build_user_prompt(page_meta, total_pages, style_tokens)
    retry_prompt = build_retry_prompt()

    try:
        result = await client.analyze_page(
            base64_image=base64_image,
            user_prompt=user_prompt,
            system_prompt=SYSTEM_PROMPT,
            retry_prompt=retry_prompt,
        )
        return PageResult(
            page_num=page_meta.page_num,
            html=result.get("html", ""),
            css=result.get("css", ""),
            style_tokens=result.get("style_tokens", {}),
        )
    except Exception as exc:
        logger.error("Page %d analysis failed: %s", page_meta.page_num, exc)
        return PageResult(
            page_num=page_meta.page_num,
            html=f'<div class="page page-{page_meta.page_num} page-error">'
                 f'<p>Error processing page {page_meta.page_num}: {exc}</p></div>',
            css="",
            style_tokens={},
            error=str(exc),
        )
