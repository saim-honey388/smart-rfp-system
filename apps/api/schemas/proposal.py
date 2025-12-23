from datetime import datetime, date
from typing import Optional

from pydantic import BaseModel, Field


class ProposalBase(BaseModel):
    rfp_id: str
    contractor: str = Field(..., example="Acme Builders")
    contractor_email: Optional[str] = Field(None, example="bid-team@example.com")
    price: Optional[float] = Field(None, example=45000.0)
    currency: str = Field(default="USD")
    start_date: Optional[date] = None
    summary: Optional[str] = None
    experience: Optional[str] = Field(None, description="Contractor's relevant experience")
    methodology: Optional[str] = Field(None, description="Proposed methodology or approach")
    warranties: Optional[str] = Field(None, description="Warranty terms")
    timeline_details: Optional[str] = Field(None, description="Detailed timeline breakdown")
    extracted_text: Optional[str] = None


class ProposalCreate(ProposalBase):
    pass


class Proposal(ProposalBase):
    id: str
    status: str = Field(default="submitted")
    created_at: datetime

    class Config:
        from_attributes = True

