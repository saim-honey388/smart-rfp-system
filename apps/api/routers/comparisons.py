from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from sqlmodel import Session, select, desc

from apps.api.models.db import get_session
from apps.api.models.entities import SavedComparisonModel, RfpModel

router = APIRouter(tags=["comparisons"])
print("DEBUG: Loading comparisons router with get_db fix")

# --- Schemas ---
class SavedComparisonBase(BaseModel):
    rfp_id: str
    dimensions: List[str]
    proposal_ids: List[str]

class SavedComparisonRead(SavedComparisonBase):
    id: str
    rfp_title: Optional[str] = None

class SavedComparisonCreate(SavedComparisonBase):
    pass

# --- Dependency ---
def get_db():
    from apps.api.models.db import get_session
    with get_session() as session:
        yield session

# --- Endpoints ---

@router.get("/comparisons", response_model=List[SavedComparisonRead])
def list_comparisons(session: Session = Depends(get_db)):
    """List all saved comparisons, most recent first."""
    # Join with RFP to get title
    statement = select(SavedComparisonModel, RfpModel.title).join(RfpModel).order_by(desc(SavedComparisonModel.created_at))
    results = session.exec(statement).all()
    
    comparisons = []
    for comp, title in results:
        comp_read = SavedComparisonRead(
            id=comp.id,
            rfp_id=comp.rfp_id,
            dimensions=comp.dimensions,
            proposal_ids=comp.proposal_ids,
            rfp_title=title
        )
        comparisons.append(comp_read)
    
    return comparisons

@router.post("/comparisons", response_model=SavedComparisonRead)
def save_comparison(comparison: SavedComparisonCreate, session: Session = Depends(get_db)):
    """Save a comparison. If one exists for this RFP, update it."""
    # Check if exists
    existing = session.exec(select(SavedComparisonModel).where(SavedComparisonModel.rfp_id == comparison.rfp_id)).first()
    
    if existing:
        existing.dimensions = comparison.dimensions
        existing.proposal_ids = comparison.proposal_ids
        session.add(existing)
        session.commit()
        session.refresh(existing)
        saved_comp = existing
    else:
        saved_comp = SavedComparisonModel.from_orm(comparison)
        session.add(saved_comp)
        session.commit()
        session.refresh(saved_comp)
    
    # Get title for response
    rfp = session.get(RfpModel, saved_comp.rfp_id)
    return SavedComparisonRead(
        id=saved_comp.id,
        rfp_id=saved_comp.rfp_id,
        dimensions=saved_comp.dimensions,
        proposal_ids=saved_comp.proposal_ids,
        rfp_title=rfp.title if rfp else "Unknown RFP"
    )

@router.get("/comparisons/{rfp_id}", response_model=SavedComparisonRead)
def get_comparison(rfp_id: str, session: Session = Depends(get_db)):
    """Get the saved comparison for a specific RFP."""
    comp = session.exec(select(SavedComparisonModel).where(SavedComparisonModel.rfp_id == rfp_id)).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comparison not found")
        
    rfp = session.get(RfpModel, comp.rfp_id)
    
    return SavedComparisonRead(
        id=comp.id,
        rfp_id=comp.rfp_id,
        dimensions=comp.dimensions,
        proposal_ids=comp.proposal_ids,
        rfp_title=rfp.title if rfp else "Unknown RFP"
    )

@router.delete("/comparisons/{rfp_id}")
def delete_comparison(rfp_id: str, session: Session = Depends(get_db)):
    """Delete a saved comparison."""
    comp = session.exec(select(SavedComparisonModel).where(SavedComparisonModel.rfp_id == rfp_id)).first()
    if not comp:
        raise HTTPException(status_code=404, detail="Comparison not found")
    
    session.delete(comp)
    session.commit()
    return {"ok": True}
