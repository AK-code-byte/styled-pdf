"""Anthropic API client wrapper with retry logic."""

from __future__ import annotations

import asyncio
import json
import logging

import anthropic

logger = logging.getLogger(__name__)

MAX_RETRIES = 2


class ClaudeClient:
    """Async Claude client for page analysis."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 4096,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def analyze_page(
        self,
        base64_image: str,
        user_prompt: str,
        system_prompt: str,
        retry_prompt: str,
    ) -> dict:
        """Send a page image + prompt to Claude and return parsed JSON response.

        Retries up to MAX_RETRIES times on invalid JSON.
        """
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": base64_image,
                        },
                    },
                    {"type": "text", "text": user_prompt},
                ],
            }
        ]

        for attempt in range(MAX_RETRIES + 1):
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=system_prompt,
                messages=messages,
            )
            raw_text = response.content[0].text

            try:
                # Strip markdown fences if Claude ignores instructions
                text = raw_text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                return json.loads(text)
            except (json.JSONDecodeError, IndexError) as exc:
                if attempt < MAX_RETRIES:
                    logger.warning("Invalid JSON on attempt %d, retrying...", attempt + 1)
                    messages.append({"role": "assistant", "content": raw_text})
                    messages.append({"role": "user", "content": retry_prompt})
                else:
                    raise ValueError(
                        f"Claude returned invalid JSON after {MAX_RETRIES + 1} attempts"
                    ) from exc

        raise RuntimeError("Unreachable")  # pragma: no cover

    async def close(self) -> None:
        await self._client.close()
