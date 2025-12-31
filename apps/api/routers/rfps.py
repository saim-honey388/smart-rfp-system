from fastapi import APIRouter, HTTPException, UploadFile, File

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


@router.post("/rfps/upload", status_code=201)
async def upload_rfp(file: UploadFile = File(...)):
    """
    Upload and extract data from an RFP PDF.
    Does NOT save to DB yet, just returns extracted data for the frontend editor.
    """
    from services.ingest.extractor import extract_text
    from services.ingest.rfp_extractor import extract_rfp_details
    import shutil
    import tempfile
    import os

    # Save to temp file to read
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # Extract text
        text = extract_text(tmp_path)
        
        # Extract details via AI
        details = extract_rfp_details(text)
        
        return details

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
