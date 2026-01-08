"""AI client with OpenAI-first, Groq fallback support."""

import json
from typing import Any, Dict

# Use the unified AI client with automatic fallback
from backend.src.utils.ai_client import complete_with_fallback


def complete(system: str, prompt: str, temperature: float = 0.2) -> str:
    """
    Complete a chat request with automatic fallback.
    
    Uses OpenAI as primary provider, falls back to Groq on rate limit.
    """
    return complete_with_fallback(system, prompt, temperature)


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

