from pathlib import Path
from datetime import date

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from apps.api.config.settings import settings
from apps.api.schemas.proposal import Proposal, ProposalCreate
from apps.api.schemas.review import ReviewResult
from apps.api.services import notification_service, proposal_service, rfp_service
from services.ingest.extractor import extract_text
from services.ingest.parser import extract_emails
from services.ingest.ai_extractor import extract_details_with_ai

router = APIRouter(tags=["proposals"])


@router.get("/proposals", response_model=list[Proposal])
def list_proposals(rfp_id: str | None = None):
    return proposal_service.list_proposals(rfp_id=rfp_id)


@router.post("/proposals", response_model=Proposal, status_code=201)
def create_proposal(payload: ProposalCreate):
    if not rfp_service.get_rfp(payload.rfp_id):
        raise HTTPException(status_code=404, detail="RFP not found")
    return proposal_service.create_proposal(payload)


@router.post("/proposals/upload", response_model=Proposal, status_code=201)
async def upload_proposal(
    rfp_id: str = Form(...),
    contractor: str = Form(...),
    price: float | None = Form(None),
    currency: str = Form("USD"),
    start_date: str | None = Form(None),
    summary: str | None = Form(None),
    contractor_email: str | None = Form(None),
    file: UploadFile = File(...),
):
    """Create a proposal plus upload a PDF for AI to read."""
    if not rfp_service.get_rfp(rfp_id):
        raise HTTPException(status_code=404, detail="RFP not found")

    payload = ProposalCreate(
        rfp_id=rfp_id,
        contractor=contractor,
        contractor_email=contractor_email,
        price=price,
        currency=currency,
        start_date=start_date,
        summary=summary,
    )
    proposal = proposal_service.create_proposal(payload)

    # Save file to storage and extract text
    base = Path(settings.storage_path) / "proposals" / rfp_id
    base.mkdir(parents=True, exist_ok=True)
    pdf_path = base / f"{proposal.id}.pdf"
    with pdf_path.open("wb") as f:
        f.write(await file.read())

    text = extract_text(str(pdf_path))

    # --- AI Data Extraction ---
    # If key fields are missing, try to extract them from the document text
    if not (contractor and price and start_date and summary):
        extracted_data = extract_details_with_ai(text)
        
        # Populate missing fields if extraction was successful
        if not contractor or contractor.lower() in ("n/a", "not captured", "unknown"):
             if val := extracted_data.get("contractor_name"):
                 contractor = val
        
        if price is None:
             if val := extracted_data.get("price"):
                 price = val
                 
        if currency == "USD": # Default value, check if AI found something different
             if val := extracted_data.get("currency"):
                 currency = val
                 
        if not start_date:
             if val := extracted_data.get("start_date"):
                 start_date = val

        if not summary:
             if val := extracted_data.get("summary"):
                 summary = val
        
        # New fields extraction (experience, methodology, warranties, timeline_details)
        experience = extracted_data.get("experience")
        methodology = extracted_data.get("methodology")
        warranties = extracted_data.get("warranties")
        timeline_details = extracted_data.get("timeline_details")

    # Extract an email address from the PDF if one was not provided.
    if not contractor_email:
        emails = extract_emails(text)
        if emails:
            contractor_email = emails[0]
    
    proposal_service.update_extracted_text(proposal.id, text)
    
    # Update fields that might have been populated by AI or extraction
    # We always update if we have new values to ensure persistence
    refreshed = proposal_service.get_proposal(proposal.id)
    if refreshed:
        from apps.api.models.db import get_session
        from apps.api.models.entities import ProposalModel
        with get_session() as session:
            db_p = session.get(ProposalModel, proposal.id)
            if db_p:
                if contractor_email:
                    db_p.contractor_email = contractor_email
                
                # Update other fields if they were extracted and differ
                if contractor and contractor != db_p.contractor:
                    db_p.contractor = contractor
                if price is not None and price != db_p.price:
                    db_p.price = price
                if currency and currency != db_p.currency:
                    db_p.currency = currency
                if start_date and start_date != db_p.start_date:
                    if isinstance(start_date, str):
                        try:
                            db_p.start_date = date.fromisoformat(start_date)
                        except ValueError:
                            pass
                    else:
                         db_p.start_date = start_date
                if summary and summary != db_p.summary:
                    db_p.summary = summary
                
                # Update new extended fields
                if experience:
                    db_p.experience = experience
                if methodology:
                    db_p.methodology = methodology
                if warranties:
                    db_p.warranties = warranties
                if timeline_details:
                    db_p.timeline_details = timeline_details
                    
                session.add(db_p)
                session.commit()

    # Return refreshed proposal with extracted_text set
    return proposal_service.get_proposal(proposal.id)


@router.get("/proposals/{proposal_id}", response_model=Proposal)
def get_proposal(proposal_id: str):
    proposal = proposal_service.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.post("/proposals/{proposal_id}/approve", response_model=Proposal)
def approve_proposal(proposal_id: str):
    proposal = proposal_service.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    rfp = rfp_service.get_rfp(proposal.rfp_id)
    updated = proposal_service.set_status(proposal_id, "approved")
    if rfp and updated:
        notification_service.send_approval_email(
            rfp_title=rfp.title,
            contractor_email=updated.contractor_email or "",
            contractor_name=updated.contractor,
        )
    return updated


@router.post("/proposals/{proposal_id}/reject", response_model=Proposal)
def reject_proposal(proposal_id: str):
    proposal = proposal_service.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    rfp = rfp_service.get_rfp(proposal.rfp_id)
    updated = proposal_service.set_status(proposal_id, "rejected")
    if rfp and updated:
        # Use latest AI review to drive the explanation email.
        from apps.api.services import review_service

        review_dict = review_service.get_review_summary(proposal_id)
        if review_dict:
            review = ReviewResult.model_validate(review_dict)
            notification_service.send_rejection_email(
                rfp_title=rfp.title,
                contractor_email=updated.contractor_email or "",
                contractor_name=updated.contractor,
                review=review,
            )
    return updated

