from __future__ import annotations

import asyncio
import logging

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


async def llm_complete(
    prompt: str,
    system: str = "",
    model_tier: str = "standard",
) -> str:
    """Provider-transparent LLM call. Raises LLMError on failure."""
    if settings.llm_provider == "anthropic":
        return await _anthropic(prompt, system, model_tier)
    return await _ollama(prompt, system)


async def _ollama(prompt: str, system: str) -> str:
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": settings.ollama_model,
        "messages": messages,
        "stream": False,
    }

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{settings.ollama_base_url}/api/chat",
                    json=payload,
                )
                resp.raise_for_status()
                data = resp.json()
                return data["message"]["content"]
        except httpx.TimeoutException:
            if attempt == 0:
                logger.warning("Ollama timeout — retrying")
                await asyncio.sleep(2)
                continue
            raise LLMError("Ollama timed out after retry")
        except Exception as exc:
            raise LLMError(f"Ollama error: {exc}") from exc

    raise LLMError("Ollama failed after retries")


async def _anthropic(prompt: str, system: str, model_tier: str) -> str:
    if not settings.anthropic_api_key:
        raise LLMError("ANTHROPIC_API_KEY not set")

    model = (
        "claude-opus-4-8" if model_tier == "reasoning" else "claude-sonnet-4-6"
    )

    try:
        import anthropic as _anthropic_sdk
        client = _anthropic_sdk.AsyncAnthropic(api_key=settings.anthropic_api_key)
        kwargs: dict = {
            "model": model,
            "max_tokens": 2048,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        message = await client.messages.create(**kwargs)
        return message.content[0].text
    except Exception as exc:
        raise LLMError(f"Anthropic error: {exc}") from exc
