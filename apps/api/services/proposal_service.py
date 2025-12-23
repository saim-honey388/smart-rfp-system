from typing import List, Optional

from sqlmodel import select

from apps.api.models.db import get_session
from apps.api.models.entities import ProposalModel
from apps.api.schemas.proposal import Proposal, ProposalCreate


def list_proposals(rfp_id: Optional[str] = None) -> List[Proposal]:
    with get_session() as session:
        stmt = select(ProposalModel).order_by(ProposalModel.created_at.desc())
        if rfp_id:
            stmt = stmt.where(ProposalModel.rfp_id == rfp_id)
        proposals = session.exec(stmt).all()
        return [Proposal.model_validate(p) for p in proposals]


def create_proposal(payload: ProposalCreate) -> Proposal:
    data = payload.model_dump()
    proposal = ProposalModel(**data)
    with get_session() as session:
        session.add(proposal)
        session.commit()
        session.refresh(proposal)
        return Proposal.model_validate(proposal)


def get_proposal(proposal_id: str) -> Optional[Proposal]:
    with get_session() as session:
        proposal = session.get(ProposalModel, proposal_id)
        return Proposal.model_validate(proposal) if proposal else None


def update_extracted_text(proposal_id: str, text: str) -> None:
    """Attach extracted text to a proposal after PDF ingest."""
    with get_session() as session:
        proposal = session.get(ProposalModel, proposal_id)
        if not proposal:
            return
        proposal.extracted_text = text
        session.add(proposal)
        session.commit()



def set_status(proposal_id: str, status: str) -> Optional[Proposal]:
    """Update proposal status (e.g., approved, rejected, expired)."""
    with get_session() as session:
        proposal = session.get(ProposalModel, proposal_id)
        if not proposal:
            return None
        proposal.status = status
        session.add(proposal)
        session.commit()
        session.refresh(proposal)
        return Proposal.model_validate(proposal)


def update_proposal_details(proposal_id: str, updates: dict) -> None:
    """Update proposal qualitative fields from AI analysis."""
    with get_session() as session:
        proposal = session.get(ProposalModel, proposal_id)
        if not proposal:
            return
        
        # update fields if present in updates dict
        for key, value in updates.items():
            if hasattr(proposal, key):
                setattr(proposal, key, value)
        
        session.add(proposal)
        session.commit()


