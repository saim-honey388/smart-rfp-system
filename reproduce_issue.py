
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.append(os.getcwd())

from backend.src.agents.ingestion import ingest_document
from backend.src.agents.form_structure_analyzer import FormStructureAnalyzer, ProposalFormStructure

def debug_pdf_extraction():
    # PATH TO PDF
    pdf_path = "/home/linux/Projects/RFP System/ilovepdf_split-range/AV -  Bid Analysis & Bids-2-12.pdf"
    collection_name = "DEBUG_TEST_COLLECTION"
    
    print(f"--- 1. Ingesting PDF: {pdf_path} ---")
    ingest_document(pdf_path, collection_name=collection_name, reset=True)
    
    # RFP SECTIONS (Hardcoded from what we know about this RFP)
    rfp_sections = [
        "I Structural", 
        "II Balcony, Exterior corridor, and Landing Restoration",
        "III Column/Posts Chase (Stucco) Repairs"
    ]
    rfp_columns = ['Item', 'Description of Work', 'Quantity', 'Unit', 'Unit Cost', 'Total']
    
    custom_query = " ".join(rfp_sections) + " " + " ".join(rfp_columns)
    print(f"\n--- 2. Custom Query: {custom_query} ---")
    
    # ANALYZER
    analyzer = FormStructureAnalyzer()
    
    # GET CONTEXT
    print("\n--- 3. Getting Proposal Form Context ---")
    context = analyzer.get_proposal_form_context(
        collection_name=collection_name,
        k=20,
        custom_query=custom_query
    )
    
    print("\n\n" + "="*50)
    print("WHAT THE AI ACTUALLY SEES (CONTEXT):")
    print("="*50)
    print(context)
    print("="*50 + "\n\n")
    
    # TRY EXTRACTION
    print("--- 4. Attempting Extraction ---")
    structure = ProposalFormStructure(
        form_title="Proposal Form",
        tables=[], # Not used heavily by row extractor
        fixed_columns=["Item", "Description"],
        vendor_columns=["Quantity", "Unit", "Unit Cost", "Total"],
        sections=rfp_sections
    )
    
    rows = analyzer.extract_form_rows(context, structure)
    
    print(f"\n--- 5. Extracted {len(rows)} Rows ---")
    for i, row in enumerate(rows[:5]):
        print(f"Row {i+1}: {row}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    debug_pdf_extraction()
