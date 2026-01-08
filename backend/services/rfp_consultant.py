import json
from backend.schemas.chat import RFPState
# from backend.src.utils.llm_client import complete_json

SYSTEM_PROMPT = """You are an expert RFP Consultant AI. Your goal is to help the user define a robust Request for Proposal (RFP).
You will receive the CURRENT STATE of the RFP and the user's latest message.

Your responsibilities:
1. **Analyze** the user's input to extract these 5 key fields if present:
   - **Title**: A clear, professional title for the RFP.
   - **Scope**: A detailed description of the project scope.
   - **Requirements**: A list of specific deliverables or requirements.
   - **Budget**: The estimated budget (e.g., "$50,000" or "TBD").
   - **Timeline End**: The due date in YYYY-MM-DD format (use last day of month if unspecified).

2. **Update** the `updated_state` object. If the user provides new info, overwrite the corresponding field. If they don't mention a field, KEEP the value from `current_state`.
   - **Crucial:** If the user provides a detailed block of text, extract ALL 5 fields from it if possible. Do not wait to ask for them one by one if the information is already there.

3. **Reply** to the user conversationally (`reply` field).
   - If fields are missing, ask for them politely (one or two at a time).
   - If the user provided everything, verify it and suggest next steps (like "This looks great! Review the draft on the right.").
   - Keep answers professional, encouraging, and concise.

4. **Proposal Form (OPTIONAL)**: Once ALL 5 fields are filled, ask the user:
   "Would you like me to generate a Proposal Submission Form that vendors can fill out with their pricing?"
   - If user says YES (or similar affirmative), set `generate_proposal_form: true`
   - If user says NO, set `generate_proposal_form: false`
   - If the question hasn't been asked yet about proposal form, set `generate_proposal_form: null`

**Current RFP State:**
{current_state_json}

**Respond with STRICT JSON ONLY:**
{{
  "reply": "Your conversational response here...",
  "updated_state": {{
      "title": "...",
      "scope": "...",
      "requirements": ["req1", "req2"],
      "budget": "...",
      "timeline_end": "..."
  }},
  "generate_proposal_form": null
}}
"""

from backend.src.utils.ai_client import get_chat_llm
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Optional, List

# Define explicit state model for structured output (mirrors RFPState from schemas)
class RFPStateOutput(BaseModel):
    """Explicit RFP state for OpenAI structured output compatibility."""
    title: str = Field(default="", description="RFP title")
    scope: str = Field(default="", description="Project scope")
    requirements: List[str] = Field(default_factory=list, description="List of requirements")
    budget: str = Field(default="", description="Budget amount")
    timeline_end: str = Field(default="", description="Due date in YYYY-MM-DD format")

# Define the expected output structure with explicit types (OpenAI native structured output)
class RFPConsultantResponse(BaseModel):
    reply: str = Field(description="Conversational response to the user")
    updated_state: RFPStateOutput = Field(description="The updated RFP state object")
    generate_proposal_form: Optional[bool] = Field(default=None, description="Whether to generate a proposal form")

def consult_on_rfp(message: str, current_state: RFPState, history: list[dict]) -> dict:
    """
    Sends message + state to LLM, returns {reply: str, updated_state: dict, generate_proposal_form: bool|null}
    """
    import traceback
    
    try:
        # Debug logging
        try:
            with open("/tmp/rfp_debug.log", "a") as f:
                f.write(f"Incoming message: {message}\n")
                f.write(f"Current State: {current_state}\n")
        except:
            pass

        state_json = current_state.model_dump_json()
        
        # Construct conversation history string
        history_text = ""
        for msg in history[-20:]:
            role = "AI" if msg.get("role") == "ai" else "User"
            text = msg.get("text", "")
            history_text += f"{role}: {text}\n"

        # Initialize LLM with default settings (GPT-4o)
        llm = get_chat_llm(temperature=0.7)
        # Use OpenAI native structured output (requires explicit Pydantic models, no generic dict)
        structured_llm = llm.with_structured_output(RFPConsultantResponse)
        
        # Use LangChain variable substitution for current_state_json instead of string replacement
        # This prevents the JSON braces in state_json from confusing the PromptTemplate
        prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("user", """Conversation History:
{history_text}

User's Latest Message:
{message}""")
        ])
        
        chain = prompt | structured_llm
        
        response = chain.invoke({
            "current_state_json": state_json,
            "history_text": history_text,
            "message": message
        })
        
        # Convert Pydantic result back to dict
        return response.model_dump()

    except Exception as e:
        import traceback
        try:
            with open("/tmp/rfp_debug.log", "a") as f:
                f.write(f"ERROR: {str(e)}\n")
                f.write(traceback.format_exc())
        except:
            pass
            
        print(f"AI Error: {e}")
        # Fallback if AI fails
        return {
            "reply": "I'm having trouble processing that specific request. Please try again later.",
            "updated_state": current_state.model_dump(),
            "generate_proposal_form": None
        }


def generate_proposal_form_for_rfp(rfp_title: str, rfp_scope: str, requirements: list[str]) -> dict:
    """
    Generates a proposal submission form based on RFP data from AI Consultant flow.
    Called when user agrees to create a proposal form.
    
    Returns: {proposal_form_schema: dict, proposal_form_rows: list}
    """
    from backend.src.agents.form_generator import AIFormGenerator
    
    try:
        generator = AIFormGenerator()
        form = generator.generate_form(
            rfp_title=rfp_title,
            rfp_scope=rfp_scope,
            rfp_requirements=requirements,
            project_type=None  # Will be inferred from title/scope
        )
        
        return {
            "proposal_form_schema": {
                "form_title": form.form_title,
                "fixed_columns": form.fixed_columns,
                "vendor_columns": form.vendor_columns,
                "sections": form.sections,
                "tables": [t.model_dump() for t in form.tables]
            },
            "proposal_form_rows": [r.model_dump() for r in form.rows]
        }
    except Exception as e:
        print(f"Proposal form generation failed: {e}")
        return {
            "proposal_form_schema": {},
            "proposal_form_rows": []
        }
