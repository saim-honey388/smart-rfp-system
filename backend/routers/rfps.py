from typing import List
from io import BytesIO
from fastapi import APIRouter, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.responses import StreamingResponse

from backend.schemas.rfp import Rfp as RFP, RfpCreate as RFPCreate, RfpBase as RFPUpdate
from backend.services import rfp_service, proposal_service, report_service

router = APIRouter(tags=["rfps"])


@router.get("/rfps", response_model=list[RFP])
def list_rfps():
    return rfp_service.list_rfps()


@router.post("/rfps", response_model=RFP, status_code=201)
def create_rfp(payload: RFPCreate):
    print(f"DEBUG: Received RFP create payload: {payload.model_dump()}")
    return rfp_service.create_rfp(payload)


@router.delete("/rfps/{rfp_id}", status_code=204)
def delete_rfp(rfp_id: str):
    if not rfp_service.delete_rfp(rfp_id):
        raise HTTPException(status_code=404, detail="RFP not found")
    return {"ok": True}

@router.get("/rfps/{rfp_id}/pdf")
def download_rfp_pdf(rfp_id: str):
    rfp = rfp_service.get_rfp(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    
    buffer = BytesIO()
    report_service.generate_rfp_pdf(rfp, buffer)
    buffer.seek(0)
    
    filename = f"RFP_{rfp.title.replace(' ', '_')}.pdf"
    
    return StreamingResponse(
        buffer, 
        media_type="application/pdf", 
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/rfps/{rfp_id}", response_model=RFP)
def get_rfp(rfp_id: str):
    rfp = rfp_service.get_rfp(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
    return rfp


@router.post("/rfps/upload", status_code=201)
def upload_rfp(file: UploadFile = File(...)):
    """
    Upload and extract data from an RFP PDF.
    Now also extracts the proposal form structure for vendor submissions.
    Does NOT save to DB yet, just returns extracted data for the frontend editor.
    """ 
    from backend.services.ingest.extractor import extract_text
    from backend.services.ingest.rfp_extractor import extract_rfp_details
    from backend.src.agents.ingestion import ingest_document
    from backend.src.agents.form_structure_analyzer import FormStructureAnalyzer
    import shutil
    import tempfile
    import os

    # Save to temp file to read
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        # Step 1: Extract text
        text = extract_text(tmp_path)
        
        # Step 2: Extract basic RFP details via AI
        details = extract_rfp_details(text)
        
        # Step 3: Ingest to ChromaDB for proposal form extraction
        print("--- Ingesting RFP to ChromaDB for form extraction ---")
        ingest_document(tmp_path, "RFP_Upload_Context", chunk_size=1000, chunk_overlap=200, reset=True)
        
        # Step 4: Extract proposal form structure using new dynamic agent
        proposal_form_schema = {}
        proposal_form_rows = []
        
        try:
            analyzer = FormStructureAnalyzer()
            analysis = analyzer.analyze_rfp("RFP_Upload_Context")
            
            if analysis is not None:
                proposal_form_schema = analysis.structure.model_dump()
                proposal_form_rows = [r.model_dump() for r in analysis.rows]
                print(f"✓ Extracted proposal form: {len(analysis.rows)} rows, {len(analysis.structure.sections)} sections")
            else:
                print("ℹ No proposal form found in this RFP document - skipping form extraction")
        except Exception as form_err:
            print(f"⚠ Proposal form extraction failed (non-fatal): {form_err}")
            # Continue without proposal form - not all RFPs have structured forms
        
        # Return combined data
        return {
            **details,  # title, scope, requirements, budget, timeline
            "proposal_form_schema": proposal_form_schema,
            "proposal_form_rows": proposal_form_rows
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Extraction failed: {str(e)}")
    finally:
        # Cleanup
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
