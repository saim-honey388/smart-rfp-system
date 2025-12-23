from typing import List, Optional

from pydantic import BaseModel, Field


class Finding(BaseModel):
    kind: str
    summary: str
    score: Optional[float] = None


class ReviewResult(BaseModel):
    proposal_id: str
    coverage_pct: Optional[float] = Field(None, description="Requirement coverage %")
    price_score: Optional[float] = Field(None, description="Price score 0-100")
    scope_score: Optional[float] = Field(None, description="Scope score 0-100")
    clarity_score: Optional[float] = Field(None, description="Clarity score 0-100")
    schedule_score: Optional[float] = Field(None, description="Schedule score 0-100")
    overall_score: Optional[float] = Field(None, description="Overall score 0-100")
    risk: Optional[str] = None
    findings: List[Finding] = Field(default_factory=list)


class ComparisonRow(BaseModel):
    proposal_id: str
    contractor: str
    price: Optional[float] = None
    coverage: Optional[float] = None
    risk: Optional[str] = None
    overall_score: Optional[float] = None
    experience: Optional[str] = None
    methodology: Optional[str] = None
    warranties: Optional[str] = None
    timeline_details: Optional[str] = None


class Comparison(BaseModel):
    rfp_id: str
    rows: List[ComparisonRow] = Field(default_factory=list)

