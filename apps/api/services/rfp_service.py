from typing import List, Optional

from sqlmodel import select

from apps.api.models.db import get_session
from apps.api.models.entities import RfpModel
from apps.api.schemas.rfp import Rfp, RfpCreate


def list_rfps() -> List[Rfp]:
    with get_session() as session:
        rfps = session.exec(select(RfpModel).order_by(RfpModel.created_at.desc())).all()
        return [Rfp.model_validate(r) for r in rfps]


def create_rfp(payload: RfpCreate) -> Rfp:
    data = payload.model_dump()
    rfp = RfpModel(**data)
    with get_session() as session:
        session.add(rfp)
        session.commit()
        session.refresh(rfp)
        return Rfp.model_validate(rfp)


def get_rfp(rfp_id: str) -> Optional[Rfp]:
    with get_session() as session:
        rfp = session.get(RfpModel, rfp_id)
        return Rfp.model_validate(rfp) if rfp else None

