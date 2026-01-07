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
    
    # Proposal Form Fields (NEW)
    proposal_form_schema: dict = Field(
        sa_column=Column(JSON), default_factory=dict,
        description="Discovered/Generated proposal form structure (fixed_columns, vendor_columns, sections)"
    )
    proposal_form_rows: List[dict] = Field(
        sa_column=Column(JSON), default_factory=list,
        description="Line items from the proposal form (item_id, description, quantity, unit, etc.)"
    )
    comparison_matrix_cache: dict = Field(
        sa_column=Column(JSON), default_factory=dict,
        description="Cached column classification: {proposal_ids, fixed_columns, vendor_columns}"
    )

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
    
    # Enhanced extraction fields (stored as JSON arrays of bullet points)
    experience: List[str] = Field(
        sa_column=Column(JSON), default_factory=list, 
        description="Experience bullet points"
    )
    scope_understanding: List[str] = Field(
        sa_column=Column(JSON), default_factory=list,
        description="Scope understanding bullet points"
    )
    materials: List[str] = Field(
        sa_column=Column(JSON), default_factory=list,
        description="Materials/equipment bullet points"
    )
    timeline: List[str] = Field(
        sa_column=Column(JSON), default_factory=list,
        description="Timeline/schedule bullet points"
    )
    warranty: List[str] = Field(
        sa_column=Column(JSON), default_factory=list,
        description="Warranty terms bullet points"
    )
    safety: List[str] = Field(
        sa_column=Column(JSON), default_factory=list,
        description="Safety practices bullet points"
    )
    cost_breakdown: List[str] = Field(
        sa_column=Column(JSON), default_factory=list,
        description="Cost breakdown bullet points"
    )
    termination_term: List[str] = Field(
        sa_column=Column(JSON), default_factory=list,
        description="Termination terms bullet points"
    )
    references: List[str] = Field(
        sa_column=Column(JSON), default_factory=list,
        description="References bullet points"
    )
    
    # Legacy fields (kept for backward compatibility)
    methodology: Optional[str] = None
    warranties: Optional[str] = None
    timeline_details: Optional[str] = None
    
    extracted_text: Optional[str] = None
    dimensions: dict = Field(
        sa_column=Column(JSON), default_factory=dict, description="Dictionary of dynamic dimension key-value pairs"
    )
    # Proposal Form Data (NEW)
    proposal_form_data: List[dict] = Field(
        sa_column=Column(JSON), default_factory=list,
        description="Vendor's filled proposal form values (item_id, unit_cost, total, etc.)"
    )
    status: str = Field(default="submitted", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    rfp: Optional[RfpModel] = Relationship(back_populates="proposals")


class SavedComparisonModel(SQLModel, table=True):
    __tablename__ = "saved_comparisons"

    id: str = Field(default_factory=lambda: str(uuid4()), primary_key=True)
    rfp_id: str = Field(foreign_key="rfps.id", index=True)
    dimensions: List[str] = Field(
        sa_column=Column(JSON), default_factory=list, description="List of dimension IDs"
    )
    proposal_ids: List[str] = Field(
        sa_column=Column(JSON), default_factory=list, description="List of proposal IDs in snippet"
    )
    # NEW: Cache AI comparison scores to avoid re-running AI on reload
    scores_cache: dict = Field(
        sa_column=Column(JSON), default_factory=dict,
        description="Cached AI comparison scores: {proposals: [{id, vendor, scores, overall_score}]}"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)



