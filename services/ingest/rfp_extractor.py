
import json
import re
from datetime import datetime
from dateutil import parser as dateparser
from services.review.llm_client import complete_json


RFP_EXTRACTION_PROMPT = """
You are an expert at analyzing Request for Proposal (RFP) documents.
Your goal is to extract key structured data from the provided RFP text.

**CRITICAL INSTRUCTION: Understand Context & Synonyms**
- Dates may not be labeled "Start Date" or "End Date".
- **"Bid Package Date"**, "Issuance Date", or "RFP Date" usually implies the **Start Date**.
- **"Contractor Submittal Date"**, "Bid Due Date", "Closing Date", or "Deadline" implies the **End Date** (timeline_end).
- Use your intelligence to infer the meaning of dates based on the document context.

Extract the following fields:
1. **title**: A concise title for the RFP project (e.g., "HVAC Maintenance Services").
2. **scope**: A comprehensive summary of the project scope/description.
3. **requirements**: A list of key requirements or deliverables (array of strings).
4. **budget**: The estimated budget if mentioned (keep variable format like "$50k" or "TBD").
5. **timeline_start**: The effective start date, issuance date, or bid package date (YYYY-MM-DD or raw string).
6. **timeline_end**: The proposal due date, submittal date, or project completion date (YYYY-MM-DD or raw string).

**RFP Text:**
{text}

Respond with STRICT JSON only:
{
  "title": "...",
  "scope": "...",
  "requirements": ["...", "..."],
  "budget": "...",
  "timeline_start": "...",
  "timeline_end": "..."
}
"""


def normalize_date(date_str: str) -> str:
    """
    Normalize various date formats to YYYY-MM-DD.
    Returns 'TBD' if parsing fails or input is TBD.
    """
    if not date_str or date_str.upper() == "TBD":
        return "TBD"
    
    try:
        # Try parsing with dateutil (handles most formats)
        parsed = dateparser.parse(date_str, fuzzy=True)
        if parsed:
            return parsed.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        pass
    
    # Fallback: try common patterns manually
    patterns = [
        (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),  # Already correct format
        (r'(\d{2})/(\d{2})/(\d{4})', '%m/%d/%Y'),  # MM/DD/YYYY
        (r'(\d{2})-(\d{2})-(\d{4})', '%m-%d-%Y'),  # MM-DD-YYYY
    ]
    
    for pattern, fmt in patterns:
        match = re.search(pattern, date_str)
        if match:
            try:
                parsed = datetime.strptime(match.group(0), fmt)
                return parsed.strftime("%Y-%m-%d")
            except ValueError:
                continue
    
    return "TBD"


def extract_rfp_details(text: str) -> dict:
    """
    Extracts structured RFP details from raw text using LLM.
    """
    print(f"DEBUG: Starting AI extraction on text length: {len(text)} chars")
    try:
        # Prompt construction
        prompt = RFP_EXTRACTION_PROMPT.replace("{text}", text[:15000]) # Limit context just in case

        response = complete_json(prompt, "", temperature=0.2)
        print(f"DEBUG: AI Raw Response: {json.dumps(response, indent=2)}")
        
        # Ensure default keys if LLM misses them
        defaults = {
            "title": "Untitled RFP",
            "scope": "No scope detected.",
            "requirements": [],
            "budget": "TBD",
            "timeline_start": "TBD",
            "timeline_end": "TBD"
        }
        
        result = {**defaults, **response}
        
        # Normalize dates to YYYY-MM-DD format
        result["timeline_start"] = normalize_date(result.get("timeline_start", "TBD"))
        result["timeline_end"] = normalize_date(result.get("timeline_end", "TBD"))
        
        print(f"DEBUG: Final Extracted Result: {result.get('title')} | Start: {result.get('timeline_start')} | End: {result.get('timeline_end')}")
        return result

    except Exception as e:
        print(f"RFP Extraction Error: {e}")
        return {
            "title": "Extraction Failed",
            "scope": f"Could not process document: {str(e)}",
            "requirements": [],
            "budget": "TBD",
            "timeline_start": "TBD",
            "timeline_end": "TBD"
        }
