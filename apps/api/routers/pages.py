from fastapi import APIRouter, HTTPException, Request
from fastapi.templating import Jinja2Templates

from apps.api.services import proposal_service, review_service, rfp_service

templates = Jinja2Templates(directory="apps/web/templates")

router = APIRouter(tags=["pages"], include_in_schema=False)


@router.get("/dashboard")
def dashboard(request: Request):
    rfps = rfp_service.list_rfps()
    proposals = proposal_service.list_proposals()
    total_rfps = len(rfps)
    open_rfps = len([r for r in rfps if r.status == "open"])
    expired_rfps = len([r for r in rfps if r.status == "expired"])
    total_proposals = len(proposals)

    # Aggregate stats per RFP for the detailed list
    enriched_rfps = []
    print(f"DEBUG: Total RFPs from service: {len(rfps)}")
    for r in rfps:
        p_list = proposal_service.list_proposals(rfp_id=r.id)
        accepted_count = len([p for p in p_list if p.status == "approved"])
        enriched_rfps.append({
            "rfp": r,
            "total_proposals": len(p_list),
            "accepted_proposals": accepted_count
        })
    print(f"DEBUG: Enriched RFPs count: {len(enriched_rfps)}")
    print(f"DEBUG: Enriched RFPs: {enriched_rfps}")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "total_rfps": total_rfps,
            "open_rfps": open_rfps,
            "expired_rfps": expired_rfps,
            "total_proposals": total_proposals,
            "all_rfps": enriched_rfps,  # Passed enriched data instead of raw rfps
        },
    )


@router.get("/rfps")
def rfp_list(request: Request):
    rfps = rfp_service.list_rfps()
    return templates.TemplateResponse(
        "rfp_list.html", {"request": request, "rfps": rfps}
    )


@router.get("/rfps/{rfp_id}")
def rfp_detail(request: Request, rfp_id: str):
    rfp = rfp_service.get_rfp(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    proposals = proposal_service.list_proposals(rfp_id=rfp_id)
    return templates.TemplateResponse(
        "rfp_detail.html",
        {"request": request, "rfp": rfp, "proposals": proposals},
    )


@router.get("/rfps/{rfp_id}/comparison")
def rfp_comparison(request: Request, rfp_id: str):
    comparison = review_service.build_comparison(rfp_id)
    return templates.TemplateResponse(
        "comparison.html",
        {"request": request, "comparison": comparison},
    )


@router.get("/proposals/{proposal_id}/chat")
def proposal_chat(request: Request, proposal_id: str):
    proposal = proposal_service.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "proposal": proposal},
    )

