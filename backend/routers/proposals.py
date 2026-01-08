from pathlib import Path
from datetime import date

from fastapi import APIRouter, HTTPException, UploadFile, File, Form

from apps.api.config.settings import settings
from apps.api.schemas.proposal import Proposal, ProposalCreate
from apps.api.schemas.review import ReviewResult
from apps.api.services import notification_service, proposal_service, rfp_service
from services.ingest.extractor import extract_text
from services.ingest.parser import extract_emails
from services.ingest.ai_extractor import extract_details_with_ai

router = APIRouter(tags=["proposals"])


def parse_price_to_float(value) -> float | None:
    """
    Safely parse a price value to float.
    Handles: '$1,295,648.70', '1295648.70', 1295648.70, None
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        # Remove $, commas, whitespace
        cleaned = value.replace('$', '').replace(',', '').strip()
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None



@router.get("/proposals", response_model=list[Proposal])
def list_proposals(rfp_id: str | None = None):
    return proposal_service.list_proposals(rfp_id=rfp_id)


@router.post("/proposals", response_model=Proposal, status_code=201)
def create_proposal(payload: ProposalCreate):
    if not rfp_service.get_rfp(payload.rfp_id):
        raise HTTPException(status_code=404, detail="RFP not found")
    return proposal_service.create_proposal(payload)


@router.post("/proposals/upload", response_model=Proposal, status_code=201)
async def upload_proposal(
    rfp_id: str = Form(...),
    contractor: str = Form(...),
    price: float | None = Form(None),
    currency: str = Form("USD"),
    start_date: str | None = Form(None),
    summary: str | None = Form(None),
    contractor_email: str | None = Form(None),
    file: UploadFile = File(...),
):
    """Create a proposal plus upload a PDF for AI to read."""
    if not rfp_service.get_rfp(rfp_id):
        raise HTTPException(status_code=404, detail="RFP not found")

    payload = ProposalCreate(
        rfp_id=rfp_id,
        contractor=contractor,
        contractor_email=contractor_email,
        price=price,
        currency=currency,
        start_date=start_date,
        summary=summary,
    )
    proposal = proposal_service.create_proposal(payload)

    # Save file to storage and extract text
    base = Path(settings.storage_path) / "proposals" / rfp_id
    base.mkdir(parents=True, exist_ok=True)
    pdf_path = base / f"{proposal.id}.pdf"
    with pdf_path.open("wb") as f:
        f.write(await file.read())

    text = extract_text(str(pdf_path))

    # --- AI Data Extraction ---
    # ALWAYS extract all fields for comparison purposes
    # AI will extract: contractor_name, price, summary, experience, methodology, warranties, timeline_details
    extracted_data = extract_details_with_ai(text)
    
    # --- New Multi-Agent High-Precision Extraction ---
    from backend.services.analysis_agent import AnalysisAgent
    agent = AnalysisAgent()
    try:
        table_data = await agent.extract_table(str(pdf_path))
        if "error" not in table_data:
            # Override/Merge with high-precision data
            extracted_data["price"] = table_data.get("grand_total")
            extracted_data["contractor_name"] = table_data.get("vendor_name")
            # Store the detailed categories as 'dimensions' which the DB model supports
            extracted_data["dimensions"] = table_data.get("categories")
            print(f"DEBUG: Integrated Agent Data: Price={extracted_data['price']}")
    except Exception as e:
        print(f"Agent Extraction Failed: {e}")
    
    # --- Extract Vendor's Filled Proposal Form using RFP's SCHEMA ---
    # The vendor uses the EXACT SAME form as the RFP - just with their values filled in
    # So we use the RFP's schema (already extracted) to extract vendor values
    vendor_form_data = []
    vendor_form_schema = None
    try:
        from backend.src.agents.form_structure_analyzer import FormStructureAnalyzer, ProposalFormStructure
        from backend.src.agents.ingestion import ingest_document
        
        # Get the RFP's form schema (already extracted when RFP was uploaded)
        rfp = rfp_service.get_rfp(rfp_id)
        rfp_schema = rfp.proposal_form_schema if rfp else None
        
        if rfp_schema and rfp_schema.get('fixed_columns'):
            print(f"--- Extracting vendor form using RFP's SCHEMA (not re-discovering) ---")
            print(f"  RFP Schema: fixed={rfp_schema.get('fixed_columns')}, vendor={rfp_schema.get('vendor_columns')}")
            
            # Ingest vendor proposal PDF into a unique collection
            vendor_collection = f"Vendor_Proposal_{proposal.id}"
            ingest_document(str(pdf_path), collection_name=vendor_collection, reset=True)
            
            # Use FormStructureAnalyzer but with RFP's schema
            analyzer = FormStructureAnalyzer()
            
            # Build a DYNAMIC query from the RFP's sections and columns
            # This ensures we find the correct table that matches the RFP structure
            rfp_sections = rfp_schema.get('sections', [])
            rfp_columns = rfp_schema.get('fixed_columns', []) + rfp_schema.get('vendor_columns', [])
            custom_query = " ".join(rfp_sections[:5]) + " " + " ".join(rfp_columns) + " Item Description Unit Cost Total"
            print(f"  Using custom query from RFP: {custom_query[:80]}...")
            
            # Get context from vendor proposal using RFP's sections as query
            proposal_context = analyzer.get_proposal_form_context(
                collection_name=vendor_collection, 
                k=20,
                custom_query=custom_query
            )
            
            if proposal_context:
                # Create structure from RFP's schema (NOT re-discovering)
                structure = ProposalFormStructure(
                    form_title=rfp_schema.get('form_title', 'Proposal Form'),
                    tables=rfp_schema.get('tables', []),
                    fixed_columns=rfp_schema.get('fixed_columns', []),
                    vendor_columns=rfp_schema.get('vendor_columns', []),
                    sections=rfp_schema.get('sections', [])
                )
                
                # Extract rows using RFP's structure
                rows = analyzer.extract_form_rows(proposal_context, structure)
                
                # Convert to dict format for storage
                vendor_form_data = [row.model_dump() for row in rows]
                vendor_form_schema = rfp_schema  # Use RFP's schema
                
                print(f"✓ Extracted {len(vendor_form_data)} vendor form rows using RFP's schema")
                print(f"  Columns used: {structure.vendor_columns}")
                
                # DEBUG: Print first 3 rows
                print(f"  DEBUG - First 3 extracted rows:")
                for i, row in enumerate(vendor_form_data[:3]):
                    print(f"    Row {i+1}: item_id={row.get('item_id')}, qty={row.get('quantity')}, unit={row.get('unit')}, unit_cost={row.get('unit_cost')}, total={row.get('total')}")
            else:
                print("⚠ No proposal form context found in vendor PDF")
        else:
            print("⚠ RFP has no form schema - falling back to auto-discovery")
            # Fallback to original behavior if RFP has no schema
            from backend.src.agents.form_structure_analyzer import FormStructureAnalyzer
            from backend.src.agents.ingestion import ingest_document
            
            vendor_collection = f"Vendor_Proposal_{proposal.id}"
            ingest_document(str(pdf_path), collection_name=vendor_collection, reset=True)
            
            analyzer = FormStructureAnalyzer()
            proposal_context = analyzer.get_proposal_form_context(collection_name=vendor_collection, k=20)
            
            if proposal_context:
                structure = analyzer.discover_form_structure(proposal_context)
                rows = analyzer.extract_form_rows(proposal_context, structure)
                vendor_form_data = [row.model_dump() for row in rows]
                vendor_form_schema = structure.model_dump()
                print(f"✓ Extracted {len(vendor_form_data)} vendor form rows (auto-discovered)")
            
    except Exception as form_err:
        print(f"⚠ Vendor form extraction failed (non-fatal): {form_err}")
        import traceback
        traceback.print_exc()
    
    extracted_data["proposal_form_data"] = vendor_form_data
    extracted_data["proposal_form_schema"] = vendor_form_schema

    
    # Populate missing fields if extraction was successful
    if not contractor or contractor.lower() in ("n/a", "not captured", "unknown", "ai will extract this"):
         if val := extracted_data.get("contractor_name"):
             contractor = val
    
    if price is None:
         if val := extracted_data.get("price"):
             price = parse_price_to_float(val)
             
    if currency == "USD":  # Default value, check if AI found something different
         if val := extracted_data.get("currency"):
             currency = val
             
    if not start_date:
         if val := extracted_data.get("start_date"):
             start_date = val

    if not summary:
         if val := extracted_data.get("summary"):
             summary = val
    
    # Extract all enhanced fields from AI extraction (now as JSON arrays)
    experience = extracted_data.get("experience", [])
    scope_understanding = extracted_data.get("scope_understanding", [])
    materials = extracted_data.get("materials", [])
    timeline = extracted_data.get("timeline", [])
    warranty = extracted_data.get("warranty", [])
    safety = extracted_data.get("safety", [])
    cost_breakdown = extracted_data.get("cost_breakdown", [])
    termination_term = extracted_data.get("termination_term", [])
    references = extracted_data.get("references", [])
    
    # Legacy fields (backward compatibility)
    methodology = extracted_data.get("methodology")
    warranties = extracted_data.get("warranties")
    timeline_details = extracted_data.get("timeline_details")

    # Extract an email address from the PDF if one was not provided.
    if not contractor_email:
        emails = extract_emails(text)
        if emails:
            contractor_email = emails[0]
    
    proposal_service.update_extracted_text(proposal.id, text)
    
    # Update fields that might have been populated by AI or extraction
    # We always update if we have new values to ensure persistence
    refreshed = proposal_service.get_proposal(proposal.id)
    if refreshed:
        from apps.api.models.db import get_session
        from apps.api.models.entities import ProposalModel
        with get_session() as session:
            db_p = session.get(ProposalModel, proposal.id)
            if db_p:
                if contractor_email:
                    db_p.contractor_email = contractor_email
                
                # Update other fields if they were extracted and differ
                if contractor and contractor != db_p.contractor:
                    db_p.contractor = contractor
                if price is not None and price != db_p.price:
                    parsed_price = parse_price_to_float(price)
                    if parsed_price is not None:
                        db_p.price = parsed_price
                if currency and currency != db_p.currency:
                    db_p.currency = currency
                if start_date and start_date != db_p.start_date:
                    if isinstance(start_date, str):
                        try:
                            db_p.start_date = date.fromisoformat(start_date)
                        except ValueError:
                            pass
                    else:
                         db_p.start_date = start_date
                if summary and summary != db_p.summary:
                    db_p.summary = summary
                
                # Update NEW enhanced extraction fields (JSON arrays)
                if experience:
                    db_p.experience = experience if isinstance(experience, list) else [experience]
                if scope_understanding:
                    db_p.scope_understanding = scope_understanding if isinstance(scope_understanding, list) else [scope_understanding]
                if materials:
                    db_p.materials = materials if isinstance(materials, list) else [materials]
                if timeline:
                    db_p.timeline = timeline if isinstance(timeline, list) else [timeline]
                if warranty:
                    db_p.warranty = warranty if isinstance(warranty, list) else [warranty]
                if safety:
                    db_p.safety = safety if isinstance(safety, list) else [safety]
                if cost_breakdown:
                    db_p.cost_breakdown = cost_breakdown if isinstance(cost_breakdown, list) else [cost_breakdown]
                if termination_term:
                    db_p.termination_term = termination_term if isinstance(termination_term, list) else [termination_term]
                if references:
                    db_p.references = references if isinstance(references, list) else [references]
                
                # Legacy fields (backward compatibility)
                if methodology:
                    db_p.methodology = methodology
                if warranties:
                    db_p.warranties = warranties
                if timeline_details:
                    db_p.timeline_details = timeline_details

                # Save dynamic dimensions
                if dimensions := extracted_data.get("dimensions"):
                    if isinstance(dimensions, dict):
                        db_p.dimensions = dimensions
                
                # Save vendor proposal form data (NEW)
                if proposal_form_data := extracted_data.get("proposal_form_data"):
                    if isinstance(proposal_form_data, list):
                        db_p.proposal_form_data = proposal_form_data
                    
                session.add(db_p)
                session.commit()


    # Return refreshed proposal with extracted_text set
    return proposal_service.get_proposal(proposal.id)


@router.get("/proposals/{proposal_id}", response_model=Proposal)
def get_proposal(proposal_id: str):
    proposal = proposal_service.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    return proposal


@router.post("/proposals/{proposal_id}/approve", response_model=Proposal)
def approve_proposal(proposal_id: str):
    proposal = proposal_service.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    rfp = rfp_service.get_rfp(proposal.rfp_id)
    updated = proposal_service.set_status(proposal_id, "Accepted")
    if rfp and updated:
        # User requested to disable email sending
        # background_tasks.add_task(_send_approval_email_task, rfp, updated)
        pass
        
    return updated


@router.post("/proposals/{proposal_id}/reject", response_model=Proposal)
def reject_proposal(proposal_id: str):
    proposal = proposal_service.get_proposal(proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found")
    rfp = rfp_service.get_rfp(proposal.rfp_id)
    updated = proposal_service.set_status(proposal_id, "Rejected")
    if rfp and updated:
        # Use latest AI review to drive the explanation email.
        from apps.api.services import review_service

        review_dict = review_service.get_review_summary(proposal_id)
        if review_dict:
            review = ReviewResult.model_validate(review_dict)
            notification_service.send_rejection_email(
                rfp_title=rfp.title,
                contractor_email=updated.contractor_email or "",
                contractor_name=updated.contractor,
                review=review,
            )
    return updated


@router.get("/proposals/{rfp_id}/matrix")
async def get_proposal_matrix(rfp_id: str):
    """
    Returns a unified comparison matrix of the RFP line items 
    vs the filled values from each vendor proposal.
    
    COLUMN CLASSIFICATION:
    - Majority voting: >50% match with RFP → Fixed column
    - AI semantic check: For ambiguous columns
    - Cached per RFP + proposal set
    """
    from backend.services.column_classifier import (
        classify_columns_majority_voting,
        classify_with_ai_fallback,
        get_cached_classification,
        build_cache
    )
    from apps.api.models.db import get_session
    from apps.api.models.entities import RfpModel

    rfp = rfp_service.get_rfp(rfp_id)
    if not rfp:
        raise HTTPException(status_code=404, detail="RFP not found")
        
    proposals = proposal_service.list_proposals(rfp_id=rfp_id)
    rfp_rows = rfp.proposal_form_rows or []
    
    # Consensus Logic: If RFP has no rows, try to elect a structure from proposals
    if not rfp_rows and proposals:
        try:
            from backend.src.agents.comparison_matrix_builder import ComparisonMatrixBuilder
            from backend.src.agents.vendor_data_extractor import VendorProposalData, FilledFormRow
            
            # Convert DB proposals to VendorProposalData objects for the builder
            vendor_proposals = []
            for p in proposals:
                if p.proposal_form_data:
                    filled_rows = []
                    for row in p.proposal_form_data:
                        # Convert dict back to FilledFormRow key-value pairs
                        # Note: proposal_form_data in DB is a list of dicts with keys matching schema
                        # We need to adapt it to what FilledFormRow expects if it's different
                        # But ComparisonMatrixBuilder uses checking of 'values' dict mostly.
                        # Let's check how VendorProposalData expects it.
                        # It expects filled_rows to be list of DynamicFilledRow/FilledFormRow
                        
                        # Simplification: Assume the dict in DB *IS* the row data
                        # We need to map it to a structure with 'values' dict or similar
                        
                        # Strategy: Adapt DB dict to 'values' dict
                        values_dict = {
                            k: (str(v) if v is not None else "") 
                            for k, v in row.items() 
                            if k not in ["item_id", "description", "section"]
                        }
                        
                        filled_rows.append(FilledFormRow(
                            section=row.get("section", ""),
                            item_id=row.get("item_id", ""),
                            description=row.get("description", ""),
                            values=values_dict
                        ))
                    
                    vendor_proposals.append(VendorProposalData(
                        proposal_id=str(p.id),
                        rfp_id=str(rfp.id),
                        vendor_name=p.contractor or "Unknown",
                        filled_rows=filled_rows
                    ))
            
            # Elect structure
            if vendor_proposals:
                builder = ComparisonMatrixBuilder()
                elected_structure = builder._elect_structure_from_proposals(vendor_proposals)
                
                if elected_structure and elected_structure.rows:
                    print(f"✓ Elected consensus structure from proposals: {len(elected_structure.rows)} rows")
                    # Convert elected rows back to list of dicts for this endpoint
                    rfp_rows = [r.model_dump() for r in elected_structure.rows]
                    
                    # Also update valid columns if possible
                    # But the rest of the function determines that.
        except Exception as e:
            print(f"⚠ Consensus election failed: {e}")

    if not rfp_rows:
        return {
            "rfp_title": rfp.title,
            "fixed_columns": [],
            "vendor_columns": [],
            "proposals": [{"id": p.id, "vendor": p.contractor, "status": p.status} for p in proposals],
            "rows": [],
            "message": "No RFP proposal form rows found"
        }
    
    # Get proposal IDs with form data
    proposals_with_data = [p for p in proposals if p.proposal_form_data]
    proposal_ids_with_data = [p.id for p in proposals_with_data]
    
    # --- Check cache ---
    cached = get_cached_classification(rfp.comparison_matrix_cache or {}, proposal_ids_with_data)
    
    if cached:
        fixed_columns, vendor_columns = cached
        print(f"✓ Using cached classification: fixed={fixed_columns}, vendor={vendor_columns}")
    else:
        # --- Run classification ---
        print("→ Running column classification...")
        
        # Prepare vendor data for classifier
        vendor_data = [
            {"id": p.id, "proposal_form_data": p.proposal_form_data}
            for p in proposals
        ]
        
        # First try majority voting only (faster)
        fixed_columns, vendor_columns, ambiguous = classify_columns_majority_voting(
            rfp_rows, vendor_data, threshold=0.5
        )
        
        # If we have ambiguous columns, use AI fallback
        if ambiguous:
            print(f"  → Ambiguous columns detected: {ambiguous}, running AI check...")
            fixed_columns, vendor_columns = await classify_with_ai_fallback(
                rfp_rows, vendor_data, threshold=0.5
            )
        
        print(f"  ✓ Classification: fixed={fixed_columns}, vendor={vendor_columns}")
        
        # --- Save cache ---
        new_cache = build_cache(fixed_columns, vendor_columns, proposal_ids_with_data)
        with get_session() as session:
            db_rfp = session.get(RfpModel, rfp_id)
            if db_rfp:
                db_rfp.comparison_matrix_cache = new_cache
                session.add(db_rfp)
                session.commit()
                print(f"  ✓ Saved classification cache for RFP {rfp_id[:8]}")
    
    # --- Helper functions ---
    def get_vendor_row(proposal, item_id):
        """Find vendor row matching RFP item_id."""
        for row in (proposal.proposal_form_data or []):
            if str(row.get('item_id', '')).strip() == str(item_id).strip():
                return row
        return None
    
    def parse_number(value):
        if not value or str(value).upper() in ('TBD', 'N/A', '-', '$-', ''):
            return None
        try:
            cleaned = str(value).replace('$', '').replace(',', '').strip()
            return float(cleaned)
        except (ValueError, TypeError):
            return None
    
    # Find Total column for grand total
    total_column = next((c for c in vendor_columns if 'total' in c.lower()), None)
    vendor_grand_totals = {p.id: 0.0 for p in proposals}
    
    # --- Build matrix rows ---
    matrix_rows = []
    
    for rfp_row in rfp_rows:
        item_id = rfp_row.get('item_id')
        
        # Fixed values from RFP
        fixed_values = {col: rfp_row.get(col) for col in fixed_columns}
        
        # Vendor-specific values
        vendor_values = {}
        for p in proposals:
            vendor_row = get_vendor_row(p, item_id)
            values = {}
            
            for col in vendor_columns:
                if vendor_row:
                    values[col] = vendor_row.get(col) or "-"
                else:
                    values[col] = "Not Quoted"
            
            # Add to grand total
            if total_column and vendor_row:
                total_num = parse_number(vendor_row.get(total_column) or vendor_row.get('total'))
                if total_num is not None:
                    vendor_grand_totals[p.id] += total_num
            
            vendor_values[p.id] = values
        
        matrix_rows.append({
            "fixed_values": fixed_values,
            "vendor_values": vendor_values
        })
    
    # --- Grand Total row ---
    grand_total_fixed = {col: ("GRAND TOTAL" if col in ('description', 'item_id') else "") for col in fixed_columns}
    grand_total_vendor = {}
    
    for p in proposals:
        values = {}
        if total_column:
            values[total_column] = f"${vendor_grand_totals[p.id]:,.2f}"
        grand_total_vendor[p.id] = values
    
    matrix_rows.append({
        "is_grand_total": True,
        "fixed_values": grand_total_fixed,
        "vendor_values": grand_total_vendor
    })
        
    return {
        "rfp_title": rfp.title,
        "fixed_columns": fixed_columns,
        "vendor_columns": vendor_columns,
        "proposals": [{"id": p.id, "vendor": p.contractor, "status": p.status} for p in proposals],
        "rows": matrix_rows
    }


