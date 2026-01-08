from pathlib import Path
from typing import Optional, Dict, Any

from backend.src.utils.llm_client import complete_json

PROMPT_PATH = Path(__file__).parent / "prompts" / "extract_details.txt"


def extract_details_with_ai(text: str) -> Dict[str, Any]:
    """
    Extracts structured data from proposal text using an LLM.
    Returns a dictionary with keys: contractor_name, price, currency, start_date, summary, experience, methodology, warranties, timeline_details.
    """
    if not text:
        return {}

    try:
        instructions = PROMPT_PATH.read_text(encoding="utf-8")
    except FileNotFoundError:
        # Fallback if prompt file is missing
        return {}
        
    system = "You are an expert proposal analyzer. Return STRICT JSON only."
    prompt = f"{instructions}\n\nProposal Text:\n{text}\n"

    try:
        return complete_json(system, prompt, temperature=0.0)
    except Exception:
        # Log error or handle gracefully
        return {}
