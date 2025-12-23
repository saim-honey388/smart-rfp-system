from datetime import datetime, date
from typing import Optional, List
from uuid import uuid4

from sqlmodel import Field, SQLModel, Column, JSON, Relationship


class RfpModel(SQLModel, table=True):
    __tablename__ = "rfps"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    title: str
    description: Optional[str] = None
    requirements: List[dict] = Field(
        sa_column=Column(JSON), default_factory=list, description="List of requirement dicts"
    )
    budget: Optional[float] = None
    currency: str = "USD"
    deadline: Optional[date] = None
    status: str = Field(default="open", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    proposals: List["ProposalModel"] = Relationship(back_populates="rfp")


class ProposalModel(SQLModel, table=True):
    __tablename__ = "proposals"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    rfp_id: str = Field(foreign_key="rfps.id", index=True)
    contractor: str
    contractor_email: Optional[str] = None
    price: Optional[float] = None
    currency: str = "USD"
    start_date: Optional[date] = None
    summary: Optional[str] = None
    experience: Optional[str] = None
    methodology: Optional[str] = None
    warranties: Optional[str] = None
    timeline_details: Optional[str] = None
    extracted_text: Optional[str] = None
    status: str = Field(default="submitted", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    rfp: Optional[RfpModel] = Relationship(back_populates="proposals")

