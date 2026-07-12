"""
llm/llm_client.py — thin Groq API wrapper.

Used by: intent_detector (fallback), entity_extractor (fallback),
         response agent (generation). All calls go through chat_complete().
"""
from __future__ import annotations

from typing import Any

from app.config.settings import settings

_client: Any | None = None


def _get_client():
    global _client
    if _client is None:
        from groq import Groq
        _client = Groq(api_key=settings.groq_api_key)
    return _client


def chat_complete(
    prompt: str,
    system: str = "You are a helpful assistant. Follow instructions exactly.",
    temperature: float = 0.0,
    max_tokens: int = 512,
) -> str:
    """Send a single-turn prompt and return the content string."""
    resp = _get_client().chat.completions.create(
        model=settings.groq_model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content.strip()


def chat_complete_json(prompt: str, system: str | None = None) -> str:
    """Like chat_complete but instructs the model to return valid JSON only."""
    sys = system or (
        "You are a precise JSON generator. Return ONLY valid JSON, no markdown, "
        "no preamble, no explanation."
    )
    return chat_complete(prompt, system=sys, temperature=0)
