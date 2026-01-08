from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends

from backend.services import rfp_service, proposal_service
from backend.src.utils.llm_client import complete_json

router = APIRouter(prefix="/analysis", tags=["analysis"])

class Dimension(BaseModel):
    id: str
    name: str
    description: str
    weight: int = 10
    keywords: List[str] = []
    type: str = "dynamic"  # 'general' or 'dynamic'

class AnalysisResponse(BaseModel):
    dimensions: List[Dimension]

SYSTEM_PROMPT = """You are an expert RFP Analyst. Your goal is to extract distinct EVALUATION DIMENSIONS from a Request for Proposal (RFP).

Input:
You will receive the Title, Scope, and Requirements of an RFP.

Output:
A JSON object containing a list of `dimensions`.
Each dimension must have:
- `id`: unique snake_case identifier.
- `name`: Short, professional display name.
- `description`: Brief explanation.
- `weight`: Importance (1-10).
- `keywords`: List of 3-5 specific keywords.
- `type`: EXACTLY one of: "general" OR "dynamic".

Rules:
1. "general" dimensions: You MUST include these 6 standard entries:
    - id="experience", name="Experience", type="general", keywords=["experience", "years", "projects", "portfolio", "completed", "similar"]
    - id="cost", name="Cost", type="general", keywords=["price", "budget", "cost", "fee", "rate"]
    - id="materials_warranty", name="Materials/Warranty", type="general", keywords=["materials", "warranty", "guarantee", "quality", "grade"]
    - id="schedule", name="Schedule", type="general", keywords=["schedule", "timeline", "start", "completion", "days", "weeks"]
    - id="safety", name="Safety", type="general", keywords=["safety", "osha", "compliance", "training", "incident"]
    - id="responsiveness", name="Responsiveness", type="general", keywords=["responsive", "communication", "availability", "support"]
2. "dynamic" dimensions: Extract 3-5 Technical/Scope-specific dimensions.
    - These MUST be marked as `type: "dynamic"`.
    - Do NOT duplicate the 6 general dimensions above.
    - Example: "HVAC Expertise", "Emergency Response", "Stucco Repairs".
"""

@router.post("/rfp/{rfp_id}/dimensions", response_model=AnalysisResponse)
async def generate_dimensions(rfp_id: str):
    rfp = rfp_service.get_rfp(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")

    # Construct prompt
    requirements_text = "\n".join([f"- {req.text}" for req in rfp.requirements])
    
    prompt = f"""
    RFP Title: {rfp.title}
    
    Scope:
    {rfp.description}
    
    Requirements:
    {requirements_text}
    
    Budget: {rfp.budget}
    Deadline: {rfp.deadline}
    """

    try:
        response = complete_json(SYSTEM_PROMPT, prompt, temperature=0.2)
        return AnalysisResponse(**response)
    except Exception as e:
        print(f"Error generating dimensions: {e}")
        # Fallback if AI fails
        return AnalysisResponse(dimensions=[
            Dimension(id="experience", name="Experience", description="Vendor track record", type="general", keywords=["experience", "years", "projects"]),
            Dimension(id="cost", name="Cost", description="Total project cost", type="general", keywords=["price", "cost", "budget"]),
            Dimension(id="materials_warranty", name="Materials/Warranty", description="Material quality and warranty terms", type="general", keywords=["materials", "warranty", "guarantee"]),
            Dimension(id="schedule", name="Schedule", description="Project timeline", type="general", keywords=["schedule", "timeline", "completion"]),
            Dimension(id="safety", name="Safety", description="Safety practices and compliance", type="general", keywords=["safety", "osha", "compliance"]),
            Dimension(id="responsiveness", name="Responsiveness", description="Communication and availability", type="general", keywords=["responsive", "communication", "availability"])
        ])


# --- NEW: AI-Powered Comparison Analysis ---

class DimensionScore(BaseModel):
    score: int = Field(ge=0, le=100, description="Percentage score 0-100")
    label: str = Field(description="Strong/Adequate/Weak")
    reasoning: Optional[str] = None

class ProposalScores(BaseModel):
    id: str
    vendor: str
    scores: Dict[str, DimensionScore]
    overall_score: int

class CompareRequest(BaseModel):
    proposal_ids: List[str]
    dimensions: List[str]

class CompareResponse(BaseModel):
    rfp_title: str
    proposals: List[ProposalScores]

COMPARE_SYSTEM_PROMPT = """You are a STRICT and CRITICAL RFP Proposal Evaluator. 

Your task: Compare vendor proposals against RFP requirements and score each proposal on specified dimensions.

CRITICAL SCORING GUIDELINES (Be strict - this is a formal evaluation):
- 85-100: Exceptional - Extensively documented with specific details, exceeds requirements
- 70-84: Strong - Clearly meets requirements with good supporting evidence
- 55-69: Adequate - Meets basic requirements but lacks depth or specifics
- 40-54: Marginal - Some evidence but significant gaps or vague claims
- 20-39: Weak - Minimal evidence, mostly generic statements
- 1-19: Very Poor - Almost no relevant information
- 0: NOT MENTIONED - If field explicitly says "Not mentioned in proposal" or has no relevant data, score MUST be 0

STRICT EVALUATION RULES:
1. If a dimension has "Not mentioned in proposal" → Score = 0 (zero)
2. Generic marketing claims without specifics → Score max 40
3. Vague statements like "years of experience" without numbers → Score max 50
4. Only award 70+ if there are SPECIFIC, VERIFIABLE details
5. Be SKEPTICAL - require proof, not just claims
6. Compare against RFP requirements strictly

DIMENSION EVALUATION:
- experience: Require specific years, project names/types, certifications with dates
- cost: Compare to RFP budget - over budget = lower score
- materials_warranty: Require specific brand names, warranty terms in years/coverage
- schedule: Require specific dates, milestones, duration
- safety: Require certifications (OSHA number), incident rates, specific protocols
- responsiveness: Require specific response times, contact methods, availability hours

Return JSON:
{
  "proposals": [
    {
      "id": "exact proposal ID from input",
      "vendor": "Vendor Name",
      "scores": {
        "dimension_id": { "score": 65, "label": "Adequate", "reasoning": "Specific reason based on evidence" }
      },
      "overall_score": 60
    }
  ]
}
"""

@router.post("/rfp/{rfp_id}/compare", response_model=CompareResponse)
async def compare_proposals(rfp_id: str, body: CompareRequest):
    """
    AI-powered comparison of proposals against RFP requirements.
    Fetches all data from DB and returns percentage scores per dimension.
    """
    # Fetch RFP from DB
    rfp = rfp_service.get_rfp(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    
    # Fetch Proposals from DB
    all_proposals = proposal_service.list_proposals(rfp_id=rfp_id)
    selected_proposals = [p for p in all_proposals if p.id in body.proposal_ids]
    
    if not selected_proposals:
        raise HTTPException(status_code=400, detail="No valid proposals found")
    
    # Build RFP context
    requirements_text = "\n".join([f"- {req.text}" for req in rfp.requirements]) if rfp.requirements else "No requirements specified"
    
    rfp_context = f"""
## RFP: {rfp.title}
- Budget: {rfp.budget or 'TBD'} {rfp.currency}
- Deadline: {rfp.deadline or 'TBD'}
- Requirements:
{requirements_text}
"""
    
    # Build Proposal contexts from DB data
    proposals_context = ""
    for p in selected_proposals:
        proposals_context += f"""
---
## Proposal: {p.contractor} (ID: {p.id})
- Price: {p.price or 'Not specified'} {p.currency}
- Start Date: {p.start_date or 'Not specified'}

### Experience:
{_format_list(p.experience)}

### Scope Understanding:
{_format_list(p.scope_understanding)}

### Materials:
{_format_list(p.materials)}

### Timeline:
{_format_list(p.timeline)}

### Warranty:
{_format_list(p.warranty)}

### Safety:
{_format_list(p.safety)}

### Cost Breakdown:
{_format_list(p.cost_breakdown)}

### References:
{_format_list(p.references)}

### Summary:
{p.summary or 'No summary'}
"""
    
    # Build dimensions context
    dimensions_list = ", ".join(body.dimensions)
    
    prompt = f"""
{rfp_context}

# PROPOSALS TO EVALUATE:
{proposals_context}

# DIMENSIONS TO SCORE:
{dimensions_list}

Evaluate each proposal on each dimension. Return JSON with percentage scores (0-100) and labels.
"""
    
    try:
        response = complete_json(COMPARE_SYSTEM_PROMPT, prompt, temperature=0.2)
        
        # Parse and validate response
        proposals_result = []
        for p_data in response.get("proposals", []):
            scores_dict = {}
            for dim_id, score_data in p_data.get("scores", {}).items():
                if isinstance(score_data, dict):
                    scores_dict[dim_id] = DimensionScore(
                        score=score_data.get("score", 50),
                        label=score_data.get("label", "Adequate"),
                        reasoning=score_data.get("reasoning")
                    )
                else:
                    # Handle case where score is just a number
                    score = int(score_data) if isinstance(score_data, (int, float)) else 50
                    label = "Strong" if score >= 80 else ("Adequate" if score >= 50 else "Weak")
                    scores_dict[dim_id] = DimensionScore(score=score, label=label)
            
            proposals_result.append(ProposalScores(
                id=p_data.get("id", ""),
                vendor=p_data.get("vendor", ""),
                scores=scores_dict,
                overall_score=int(round(p_data.get("overall_score", 50)))  # Convert to int
            ))
        
        return CompareResponse(rfp_title=rfp.title, proposals=proposals_result)
        
    except Exception as e:
        print(f"Error in AI comparison: {e}")
        import traceback
        traceback.print_exc()
        
        # Fallback: return basic scores
        fallback_proposals = []
        for p in selected_proposals:
            scores = {}
            for dim in body.dimensions:
                scores[dim] = DimensionScore(score=50, label="Adequate", reasoning="AI analysis unavailable")
            fallback_proposals.append(ProposalScores(
                id=p.id,
                vendor=p.contractor,
                scores=scores,
                overall_score=50
            ))
        return CompareResponse(rfp_title=rfp.title, proposals=fallback_proposals)


def _format_list(items: List[str] | None) -> str:
    """Format a list of items as bullet points."""
    if not items:
        return "- Not mentioned in proposal"
    return "\n".join([f"- {item}" for item in items])
