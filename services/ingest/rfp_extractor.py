
import json
from services.review.llm_client import complete_json

RFP_EXTRACTION_PROMPT = """
You are an expert at analyzing Request for Proposal (RFP) documents.
Your goal is to extract key structured data from the provided RFP text.

Extract the following fields:
1. **title**: A concise title for the RFP project (e.g., "HVAC Maintenance Services").
2. **scope**: A comprehensive summary of the project scope/description.
3. **requirements**: A list of specific requirements or deliverables (array of strings).
4. **budget**: The estimated budget if mentioned (keep variable format like "$50k" or "TBD").
5. **timeline_end**: The proposal due date or project completion date (YYYY-MM-DD if possible, else "TBD").

**RFP Text:**
{text}

Respond with STRICT JSON only:
{
  "title": "...",
  "scope": "...",
  "requirements": ["...", "..."],
  "budget": "...",
  "timeline_end": "..."
}
"""

def extract_rfp_details(text: str) -> dict:
    """
    Extracts structured RFP details from raw text using LLM.
    """
    try:
        # Prompt construction
        prompt = RFP_EXTRACTION_PROMPT.replace("{text}", text[:15000]) # Limit context just in case

        response = complete_json(prompt, "", temperature=0.2)
        
        # Ensure default keys if LLM misses them
        defaults = {
            "title": "Untitled RFP",
            "scope": "No scope detected.",
            "requirements": [],
            "budget": "TBD",
            "timeline_end": "TBD"
        }
        
        return {**defaults, **response}

    except Exception as e:
        print(f"RFP Extraction Error: {e}")
        return {
            "title": "Extraction Failed",
            "scope": f"Could not process document: {str(e)}",
            "requirements": [],
            "budget": "TBD",
            "timeline_end": "TBD"
        }
