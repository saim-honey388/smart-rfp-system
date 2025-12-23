from statistics import mean
from typing import Optional

from apps.api.schemas.review import Comparison, ComparisonRow, ReviewResult, Finding
from apps.api.services import proposal_service, rfp_service
from services.review.llm_client import complete_json

from pathlib import Path

PROMPT_PATH = Path("services/review/prompts/evaluate_proposal.txt")


def _evaluate_with_ai(requirements: list[dict], proposal_text: str, summary_hint: str | None) -> dict:
    req_text = "\n".join([f"- {r.text}" for r in requirements]) if requirements else "None provided."
    system = "You are an RFP proposal evaluator. Return STRICT JSON only."
    instructions = PROMPT_PATH.read_text(encoding="utf-8")
    prompt = (
        f"{instructions}\n\n"
        "RFP requirements:\n"
        f"{req_text}\n\n"
        "Proposal text:\n"
        f"{proposal_text or 'Not provided.'}\n\n"
        "Existing summary (may be empty):\n"
        f"{summary_hint or ''}\n"
    )
    return complete_json(system, prompt)



def build_comparison(rfp_id: str) -> Comparison:
    rfp = rfp_service.get_rfp(rfp_id)
    requirements = rfp.requirements if rfp else []
    proposals = proposal_service.list_proposals(rfp_id=rfp_id)
    prices = [p.price for p in proposals if p.price is not None]
    median_price = mean(prices) if prices else None

    rows = []
    for p in proposals:
        # 1. Run AI Evaluation
        try:
            ai = _evaluate_with_ai(requirements, p.extracted_text or "", p.summary)
        except Exception as e:
            print(f"DEBUG: Review Error for proposal {p.id}: {e}")
            ai = {}

        # 2. Extract Fields
        coverage = ai.get("coverage_pct")
        risk = ai.get("risk")
        price = ai.get("price") if ai.get("price") is not None else p.price
        overall_score = ai.get("overall_score")
        
        # New text fields
        updates = {
            "experience": ai.get("experience") or p.experience,
            "methodology": ai.get("methodology") or p.methodology,
            "warranties": ai.get("warranties") or p.warranties,
            "timeline_details": ai.get("timeline_details") or p.timeline_details,
            "summary": ai.get("summary") or p.summary
        }
        
        # 3. Save to DB (Cache/Persist)
        # We only update if we got new values from AI, otherwise keep existing
        has_updates = any(
            ai.get(k) and ai.get(k) != getattr(p, k) 
            for k in ["experience", "methodology", "warranties", "timeline_details", "summary"]
        )
        
        if has_updates:
            proposal_service.update_proposal_details(p.id, updates)
            # Update local object for the view
            for k, v in updates.items():
                setattr(p, k, v)

        rows.append(
            ComparisonRow(
                proposal_id=p.id,
                contractor=p.contractor,
                price=price,
                coverage=coverage,
                risk=risk,
                overall_score=overall_score,
                experience=p.experience,
                methodology=p.methodology,
                warranties=p.warranties,
                timeline_details=p.timeline_details,
            )
        )
    return Comparison(rfp_id=rfp_id, rows=rows)



def get_review_summary(proposal_id: str) -> Optional[dict]:
    proposal = proposal_service.get_proposal(proposal_id)
    if not proposal:
        return None
    rfp = rfp_service.get_rfp(proposal.rfp_id)
    requirements = rfp.requirements if rfp else []
    try:
        ai = _evaluate_with_ai(requirements, proposal.extracted_text or "", proposal.summary)
    except Exception as e:
        print(f"DEBUG: Single Review Error: {e}")
        ai = {}

    result = ReviewResult(
        proposal_id=proposal_id,
        coverage_pct=ai.get("coverage_pct"),
        price_score=ai.get("price_score"),
        scope_score=ai.get("scope_score"),
        clarity_score=ai.get("clarity_score"),
        schedule_score=ai.get("schedule_score"),
        overall_score=ai.get("overall_score"),
        risk=ai.get("risk"),
        findings=[
            Finding(kind="summary", summary=ai.get("summary") or proposal.summary or "No summary available.")
        ],
    )

    return result.model_dump()

