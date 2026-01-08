"""Compute which RFPs are approaching their deadline (for reminders)."""

from datetime import date, timedelta

from sqlmodel import select

from backend.models.db import get_session
from backend.models.entities import RfpModel


def run(days_before: int = 2) -> list[dict]:
    """Return a list of RFPs that are close to deadline.

    You can hook this into a real email system later.
    """
    today = date.today()
    target = today + timedelta(days=days_before)
    results: list[dict] = []
    with get_session() as session:
        stmt = select(RfpModel).where(
            RfpModel.status == "open",
            RfpModel.deadline.is_not(None),
            RfpModel.deadline == target,
        )
        for rfp in session.exec(stmt).all():
            results.append(
                {
                    "rfp_id": rfp.id,
                    "title": rfp.title,
                    "deadline": rfp.deadline.isoformat() if rfp.deadline else None,
                }
            )
    return results

