from fastapi import APIRouter, HTTPException

from apps.api.schemas.review import Comparison
from apps.api.services import review_service
from apps.api.services.rfp_service import get_rfp

router = APIRouter(tags=["reviews"])


@router.get("/rfps/{rfp_id}/comparison", response_model=Comparison)
def get_comparison(rfp_id: str):
    if not get_rfp(rfp_id):
        raise HTTPException(status_code=404, detail="RFP not found")
    return review_service.build_comparison(rfp_id)


@router.get("/proposals/{proposal_id}/review")
def get_review(proposal_id: str):
    review = review_service.get_review_summary(proposal_id)
    if not review:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return review

