"""
Vendor Data Extractor Agent

Extracts filled values from vendor proposal PDFs using the RFP's discovered schema.
Maps vendor data to the blank proposal form structure for comparison.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
from backend.src.agents.form_structure_analyzer import (
    ProposalFormStructure,
    DiscoveredFormRow,
    FormStructureAnalyzer,
    sanitize_column_name
)
from backend.src.agents.ingestion import ingest_document
import os
import re

# Use unified AI client with fallback support
from backend.src.utils.ai_client import get_chat_llm
from backend.src.utils.embeddings import get_embeddings


# --- Vendor Extraction Models (DYNAMIC) ---

class ColumnValue(BaseModel):
    """A single column-value pair for dynamic form extraction."""
    column: str = Field(description="The column name (e.g., 'Unit Cost', 'Total', 'Quantity')")
    value: str = Field(description="The extracted value for this column")


class DynamicFilledRow(BaseModel):
    """A line item with dynamic column values based on RFP schema."""
    section: str = Field(default="", description="Section this row belongs to")
    item_id: str = Field(description="Item identifier matching RFP (1, 2, Ad1, etc.)")
    description: str = Field(description="Description of work (should match RFP)")
    values: List[ColumnValue] = Field(default_factory=list, description="All column values for this row")


class DynamicVendorData(BaseModel):
    """Complete extracted data from a vendor's proposal - fully dynamic."""
    vendor_name: str = Field(description="Name of the vendor/contractor")
    vendor_contact: str = Field(default="", description="Contact info if found")
    vendor_license: str = Field(default="", description="License number if found")
    filled_rows: List[DynamicFilledRow] = Field(default_factory=list, description="All line items with vendor's values")
    grand_total: str = Field(default="", description="Grand total if found")
    project_duration: str = Field(default="", description="Project duration if found")


# Legacy models for backward compatibility
class FilledFormRow(BaseModel):
    """A line item from a vendor's filled proposal (legacy - use DynamicFilledRow)."""
    section: str = Field(default="", description="Section this row belongs to")
    item_id: str = Field(description="Item identifier matching RFP")
    description: str = Field(description="Description of work")
    # Dynamic values stored as dict for flexibility
    values: Dict[str, str] = Field(default_factory=dict, description="Column values keyed by column name")


class VendorProposalData(BaseModel):
    """Complete extracted data from a vendor's proposal."""
    proposal_id: str = Field(description="Unique proposal identifier")
    rfp_id: str = Field(description="Parent RFP identifier")
    vendor_name: str = Field(description="Name of the vendor/contractor")
    vendor_contact: str = Field(default="", description="Contact info if found")
    vendor_license: str = Field(default="", description="License number if found")
    filled_rows: List[FilledFormRow] = Field(default_factory=list, description="All line items with vendor's values")
    grand_total: str = Field(default="", description="Grand total if found")
    project_duration: str = Field(default="", description="Project duration if found")


# --- Vendor Data Extractor Agent ---

class VendorDataExtractor:
    """
    Agent that extracts filled values from vendor proposal PDFs.
    
    Uses the RFP's discovered schema to match and extract vendor data,
    ensuring proper alignment for comparison.
    """
    
    def __init__(self, model: Optional[str] = None, temperature: float = 0):
        # Use unified client with OpenAI-first, Groq fallback
        self.llm = get_chat_llm(model=model, temperature=temperature)
        self.chroma_path = os.path.abspath(os.path.join(os.getcwd(), "data/chromadb"))
        # Use unified embeddings with OpenAI-first, HuggingFace fallback
        self.embedding = get_embeddings()
    
    def _get_collection_name(self, vendor_name: str) -> str:
        """Generate a safe collection name for the vendor."""
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', vendor_name)[:50]
        return f"Proposal_{safe_name}"
    
    def ingest_proposal(self, pdf_path: str, vendor_name: str) -> str:
        """
        Ingests a vendor proposal PDF into ChromaDB.
        
        Returns the collection name for retrieval.
        """
        collection_name = self._get_collection_name(vendor_name)
        
        # Delete existing collection to ensure fresh data
        try:
            db = Chroma(
                persist_directory=self.chroma_path,
                embedding_function=self.embedding,
                collection_name=collection_name
            )
            db.delete_collection()
        except:
            pass
        
        # Ingest the PDF
        print(f"--- Vendor Extractor: Ingesting {vendor_name} proposal ---")
        ingest_document(pdf_path, collection_name, chunk_size=1000, chunk_overlap=200)
        
        return collection_name
    
    def get_proposal_context(self, collection_name: str, k: int = 30) -> str:
        """
        Retrieves proposal content from ChromaDB.
        """
        db = Chroma(
            persist_directory=self.chroma_path,
            embedding_function=self.embedding,
            collection_name=collection_name
        )
        
        query = "Bid Form Proposal Price Sheet Unit Cost Total Amount Schedule of Values"
        results = db.similarity_search(query, k=k)
        results.sort(key=lambda x: x.metadata.get('page', 0))
        
        print(f"  Retrieved {len(results)} chunks from {collection_name}")
        
        return "\n\n".join([doc.page_content for doc in results])
    
    def extract_vendor_data(
        self,
        proposal_context: str,
        rfp_structure: ProposalFormStructure,
        vendor_name: str,
        proposal_id: str,
        rfp_id: str
    ) -> VendorProposalData:
        """
        Extracts vendor's filled values using the RFP's DYNAMIC structure as a guide.
        
        Columns to extract are determined by rfp_structure.vendor_columns.
        """
        print(f"--- Vendor Extractor: Extracting data for {vendor_name} ---")
        
        # Get the vendor columns to extract (dynamic based on RFP)
        vendor_columns = rfp_structure.vendor_columns
        print(f"  Vendor columns to extract: {vendor_columns}")
        
        # Create structured LLM with dynamic model
        structured_llm = self.llm.with_structured_output(DynamicVendorData)
        
        # Build reference from RFP structure - handle case where rows may not exist
        rfp_items = []
        rfp_rows = getattr(rfp_structure, 'rows', []) or []
        for row in rfp_rows[:20]:  # Limit for context
            rfp_items.append(f"  - [{row.item_id}] {row.description[:80]}...")
        rfp_items_str = "\n".join(rfp_items) if rfp_items else "No specific line items available"
        
        # Build column extraction instructions dynamically
        column_instructions = "\n".join([f"   - {col}" for col in vendor_columns])
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are extracting pricing data from a vendor's proposal.

The RFP has the following form structure:
- Sections: {sections}
- Fixed Columns (from RFP): {fixed_columns}
- VENDOR COLUMNS TO EXTRACT: {vendor_columns}

REFERENCE: These are the line items from the RFP (match your extraction to these):
{rfp_items}

YOUR TASK:
1. Identify the vendor name and contact info
2. Find the filled pricing table/bid form in the proposal
3. For EACH line item from the RFP, extract the vendor's values:
   - Match by Item ID (1, 2, 3...) or Description
   - For EACH row, extract values for these specific columns:
{column_instructions}
   - Store each column value as a ColumnValue with "column" = column name and "value" = extracted value
4. Extract Grand Total and Project Duration if present

IMPORTANT:
- Match items to the RFP structure - use the same Item IDs
- If a value is "TBD", blank, or missing: use empty string ""
- Extract actual dollar amounts (e.g., "$4.10", "$131,137.50")
- Include the section for each row
- The values array should have one ColumnValue for EACH vendor column"""),
            ("user", """Vendor Proposal Content:

{proposal_content}

Extract all pricing data for vendor_name="{vendor_name}".""")
        ])
        
        chain = prompt | structured_llm
        
        try:
            result = chain.invoke({
                "proposal_content": proposal_context,
                "sections": ", ".join(rfp_structure.sections),
                "fixed_columns": ", ".join(rfp_structure.fixed_columns),
                "vendor_columns": ", ".join(vendor_columns),
                "column_instructions": column_instructions,
                "rfp_items": rfp_items_str,
                "vendor_name": vendor_name
            })
            print(f"  ✓ Extracted {len(result.filled_rows)} rows, Grand Total: {result.grand_total}")
            
            # Convert DynamicVendorData to VendorProposalData (legacy format)
            legacy_rows = []
            for row in result.filled_rows:
                # Convert List[ColumnValue] to Dict[str, str]
                values_dict = {cv.column: cv.value for cv in row.values}
                legacy_rows.append(FilledFormRow(
                    section=row.section,
                    item_id=row.item_id,
                    description=row.description,
                    values=values_dict
                ))
            
            return VendorProposalData(
                proposal_id=proposal_id,
                rfp_id=rfp_id,
                vendor_name=result.vendor_name,
                vendor_contact=result.vendor_contact,
                vendor_license=result.vendor_license,
                filled_rows=legacy_rows,
                grand_total=result.grand_total,
                project_duration=result.project_duration
            )
        except Exception as e:
            print(f"  ✗ Extraction failed: {e}")
            raise

    
    def extract_from_pdf(
        self,
        pdf_path: str,
        rfp_structure: ProposalFormStructure,
        proposal_id: str,
        rfp_id: str,
        vendor_name: Optional[str] = None
    ) -> VendorProposalData:
        """
        Full pipeline: Ingest PDF and extract vendor data.
        
        Args:
            pdf_path: Path to vendor proposal PDF
            rfp_structure: The discovered RFP form structure
            proposal_id: Unique ID for this proposal
            rfp_id: Parent RFP ID
            vendor_name: Optional vendor name (will be extracted if not provided)
        """
        # Use filename as vendor name if not provided
        if not vendor_name:
            vendor_name = os.path.basename(pdf_path).replace(".pdf", "")
        
        # Step 1: Ingest
        collection_name = self.ingest_proposal(pdf_path, vendor_name)
        
        # Step 2: Get context
        context = self.get_proposal_context(collection_name)
        
        # Step 3: Extract
        return self.extract_vendor_data(
            context, 
            rfp_structure, 
            vendor_name,
            proposal_id,
            rfp_id
        )


# --- Utility Functions ---

def align_vendor_to_rfp(
    rfp_rows: List[DiscoveredFormRow],
    vendor_rows: List[FilledFormRow]
) -> List[Dict[str, Any]]:
    """
    Align vendor's filled rows to the RFP's blank rows by Item ID.
    
    Returns a list of aligned rows with both RFP and vendor data.
    """
    aligned = []
    
    # Create lookup by item_id for vendor rows
    vendor_lookup = {row.item_id: row for row in vendor_rows}
    
    for rfp_row in rfp_rows:
        vendor_row = vendor_lookup.get(rfp_row.item_id)
        
        aligned.append({
            "section": rfp_row.section,
            "item_id": rfp_row.item_id,
            "description": rfp_row.description,
            "rfp_quantity": rfp_row.quantity,
            "rfp_unit": rfp_row.unit,
            "rfp_unit_cost": rfp_row.unit_cost,
            "rfp_total": rfp_row.total,
            "vendor_unit_cost": vendor_row.unit_cost if vendor_row else None,
            "vendor_total": vendor_row.total if vendor_row else None,
            "vendor_quantity": vendor_row.quantity if vendor_row else None,
            "vendor_unit": vendor_row.unit if vendor_row else None,
        })
    
    return aligned


# --- Test ---
if __name__ == "__main__":
    print("=== Testing Vendor Data Extractor ===\n")
    
    # First, get RFP structure
    from backend.src.agents.form_structure_analyzer import FormStructureAnalyzer
    
    analyzer = FormStructureAnalyzer()
    rfp_analysis = analyzer.analyze_rfp("RFP_Context")
    
    print(f"\nRFP has {len(rfp_analysis.rows)} rows, {len(rfp_analysis.structure.sections)} sections")
    
    # Test with a vendor proposal
    extractor = VendorDataExtractor()
    
    test_proposal = "ilovepdf_split-range/AV -  Bid Analysis & Bids-2-12.pdf"
    if os.path.exists(test_proposal):
        vendor_data = extractor.extract_from_pdf(
            pdf_path=test_proposal,
            rfp_structure=rfp_analysis.structure,
            proposal_id="test-001",
            rfp_id="rfp-audubon",
            vendor_name="TestVendor"
        )
        
        print(f"\n--- Vendor Data ---")
        print(f"Vendor: {vendor_data.vendor_name}")
        print(f"Grand Total: {vendor_data.grand_total}")
        print(f"Rows extracted: {len(vendor_data.filled_rows)}")
        
        for row in vendor_data.filled_rows[:5]:
            print(f"  [{row.item_id}] {row.description[:40]}... | {row.unit_cost} | {row.total}")
    else:
        print(f"Test proposal not found: {test_proposal}")

