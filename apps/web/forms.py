"""Lightweight helpers for server-side forms (placeholder)."""

def normalize_requirement_lines(text: str) -> list[dict]:
    """Split textarea text into requirement dicts."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    return [{"id": f"req-{i+1}", "text": ln} for i, ln in enumerate(lines)]

