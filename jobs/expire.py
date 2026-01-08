"""Sweep and expire RFPs that are past their deadline."""

from datetime import date

from sqlmodel import select

from backend.models.db import get_session
from backend.models.entities import RfpModel, ProposalModel
from backend.services.notification_service import send_expiry_email


def run() -> int:
    """Mark all open RFPs whose deadline has passed as expired.

    Returns:
        Number of RFPs marked as expired.
    """
    today = date.today()
    updated = 0
    with get_session() as session:
        stmt = select(RfpModel).where(
            RfpModel.status == "open",
            RfpModel.deadline.is_not(None),
            RfpModel.deadline < today,
        )
        rfps = session.exec(stmt).all()
        for rfp in rfps:
            rfp.status = "expired"
            session.add(rfp)
            updated += 1
        session.commit()

        # Notify contractors whose proposals belong to these RFPs.
        for rfp in rfps:
            p_stmt = select(ProposalModel).where(ProposalModel.rfp_id == rfp.id)
            for proposal in session.exec(p_stmt).all():
                if proposal.contractor_email:
                    send_expiry_email(
                        rfp_title=rfp.title,
                        contractor_email=proposal.contractor_email,
                        contractor_name=proposal.contractor,
                    )
    return updated

