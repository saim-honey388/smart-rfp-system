"""AI client using OpenAI API (configurable)."""

import json
from typing import Any, Dict

import httpx
from openai import OpenAI

from apps.api.config.settings import settings


def _client() -> OpenAI:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not set.")
    # Create httpx client explicitly to avoid proxies parameter issues
    http_client = httpx.Client(timeout=60.0)
    return OpenAI(api_key=settings.openai_api_key, http_client=http_client)


def complete(system: str, prompt: str, temperature: float = 0.2) -> str:
    client = _client()
    resp = client.chat.completions.create(
        model=settings.openai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


def complete_json(system: str, prompt: str, temperature: float = 0.2) -> Dict[str, Any]:
    """Ask the model for JSON and parse it safely."""
    content = complete(system, prompt, temperature=temperature)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        # Try to extract a fenced JSON block if present.
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = content[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                pass
        raise

