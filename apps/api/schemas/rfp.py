from datetime import datetime, date
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class Requirement(BaseModel):
    id: str
    text: str


class RfpBase(BaseModel):
    title: str = Field(..., example="Office Renovation RFP")
    description: Optional[str] = Field(None, example="Full fit-out of level 4")
    requirements: List[Requirement] = Field(default_factory=list)
    budget: int = Field(..., example=50000, description="Total budget, at least 500, in steps of 500.")
    currency: str = Field(default="USD")
    deadline: Optional[date] = None

    @field_validator("budget")
    @classmethod
    def validate_budget(cls, v: int) -> int:
        if v < 500:
            raise ValueError("Budget must be at least 500.")
        if v % 500 != 0:
            raise ValueError("Budget must increase in steps of 500.")
        return v


class RfpCreate(RfpBase):
    pass


class Rfp(RfpBase):
    id: str
    status: str = Field(default="open")
    created_at: datetime

    class Config:
        from_attributes = True

