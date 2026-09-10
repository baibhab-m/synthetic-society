"""Thin async OpenAI-compatible HTTP client.

Works with anything that speaks the /v1/chat/completions schema:
OpenAI, OpenRouter, Groq, Together, DashScope (Qwen), Sarvam, OpenPipe,
vLLM, llama.cpp's server, etc.

We do not vendor the openai SDK to keep dependencies minimal and to make
it trivial to point at non-OpenAI endpoints without rewriting code.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import get_settings

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


class LLMClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None,
                 model: str | None = None) -> None:
        s = get_settings()
        self.base_url = (base_url or s.llm_base_url).rstrip("/")
        self.api_key = api_key or s.llm_api_key
        self.model = model or s.llm_model_name
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))

    async def aclose(self) -> None:
        await self._client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
        response_format: dict[str, str] | None = None,
        max_tokens: int = 1024,
    ) -> str:
        """Single-turn-or-multi-turn chat completion. Returns the assistant text."""

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            payload["response_format"] = response_format

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        r = await self._client.post(url, json=payload, headers=headers)
        if r.status_code >= 400:
            raise LLMError(f"LLM {r.status_code}: {r.text[:300]}")

        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as e:
            raise LLMError(f"Malformed LLM response: {json.dumps(data)[:300]}") from e

    async def chat_json(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Any:
        """Convenience: force JSON object response and parse it."""
        text = await self.chat(
            messages,
            temperature=temperature,
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
        )
        text = text.strip()
        # Some providers leak ```json fences; strip if present.
        if text.startswith("```"):
            text = text.strip("`")
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            log.warning("LLM returned non-JSON despite json_object mode: %r", text[:300])
            raise LLMError(f"Invalid JSON from LLM: {e}") from e