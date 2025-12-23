from fastapi import APIRouter, HTTPException

from apps.api.schemas.rfp import Rfp, RfpCreate
from apps.api.services import rfp_service

router = APIRouter(tags=["rfps"])


@router.get("/rfps", response_model=list[Rfp])
def list_rfps():
    return rfp_service.list_rfps()


@router.post("/rfps", response_model=Rfp, status_code=201)
def create_rfp(payload: RfpCreate):
    return rfp_service.create_rfp(payload)


@router.get("/rfps/{rfp_id}", response_model=Rfp)
def get_rfp(rfp_id: str):
    rfp = rfp_service.get_rfp(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return rfp

