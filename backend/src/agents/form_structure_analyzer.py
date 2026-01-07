"""
Form Structure Analyzer Agent

This agent analyzes RFP PDFs to dynamically discover the proposal form structure.
It identifies:
- Tables (pricing sections, general conditions, additions)
- Column headers
- Fixed vs vendor-specific columns
- Section hierarchy

Uses LangChain's with_structured_output() for reliable schema extraction.
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, create_model
from langchain_community.vectorstores import Chroma
from langchain_core.prompts import ChatPromptTemplate
import os

# Use unified AI client with fallback support
from backend.src.utils.ai_client import get_chat_llm
from backend.src.utils.embeddings import get_embeddings


# --- Discovery Models ---

class DiscoveredColumn(BaseModel):
    """A column discovered in a proposal form table."""
    name: str = Field(description="Exact column header name as it appears in the table")
    column_type: str = Field(description="Type: 'identifier' (Item#), 'description', 'quantity', 'unit', 'price', 'total', 'percentage', 'other'")
    is_fixed: bool = Field(description="True if this column is the same across all vendors (e.g., Item, Description). False if it repeats per vendor (e.g., Unit Cost, Total)")
    sample_values: Optional[List[str]] = Field(default=None, description="2-3 sample values from this column")


class DiscoveredTable(BaseModel):
    """A table discovered in the RFP proposal form."""
    table_title: str = Field(description="Title of the table (e.g., 'AUDUBON VILLAS CONDOMINIUM - REPAIR SPECIFICATIONS')")
    table_type: str = Field(description="Type: 'pricing_section', 'general_conditions', 'additions', 'summary'")
    columns: List[DiscoveredColumn] = Field(description="All columns in this table")
    section_headers: Optional[List[str]] = Field(default=None, description="Section headers within table (e.g., 'I Structural', 'II Balcony Restoration')")


class DiscoveredFormRow(BaseModel):
    """A single row from the proposal form (line item)."""
    section: Optional[str] = Field(default=None, description="Section this row belongs to")
    item_id: Optional[str] = Field(default=None, description="Item identifier (1, 2, Ad1, etc.)")
    description: Optional[str] = Field(default=None, description="Description of work")
    # Dynamic values dict - stores ALL column values with original column names
    values: Optional[Dict[str, str]] = Field(default=None, description="All column values keyed by column name")
    # Legacy fields for backward compatibility
    quantity: Optional[str] = Field(default=None, description="Quantity value")
    unit: Optional[str] = Field(default=None, description="Unit of measure")
    unit_cost: Optional[str] = Field(default=None, description="Unit cost value")
    total: Optional[str] = Field(default=None, description="Total value")


class ProposalFormStructure(BaseModel):
    """Complete structure of the proposal submission form discovered from RFP."""
    form_title: str = Field(description="Main title of the proposal form")
    tables: List[DiscoveredTable] = Field(description="All tables found in the proposal form")
    fixed_columns: List[str] = Field(description="Column names that are SAME across all vendors (typically Item, Description)")
    vendor_columns: List[str] = Field(description="Column names that REPEAT for each vendor (typically Quantity, Unit, Unit Cost, Total)")
    sections: List[str] = Field(description="All section names found (e.g., 'I Structural', 'II Balcony')")


class FullProposalFormAnalysis(BaseModel):
    """Complete analysis result including structure and rows (not for OpenAI structured output)."""
    structure: ProposalFormStructure
    rows: List[DiscoveredFormRow] = []


class ExtractedRows(BaseModel):
    """Container for extracted form rows (avoids List issue in structured output)."""
    rows: List[DiscoveredFormRow]


# --- Form Structure Analyzer Agent ---

class FormStructureAnalyzer:
    """
    Agent that analyzes RFP documents to discover proposal form structure dynamically.
    
    This replaces the hardcoded schema approach with AI-driven discovery.
    """
    
    def __init__(self, model: str = "gpt-4o", temperature: float = 0):
        # Use unified client with OpenAI-first, Groq fallback
        self.llm = get_chat_llm(model=model, temperature=temperature)
        self.chroma_path = os.path.abspath(os.path.join(os.getcwd(), "data/chromadb"))
        # Use unified embeddings with OpenAI-first, HuggingFace fallback
        self.embedding = get_embeddings()
    
    def get_proposal_form_context(self, collection_name: str = "RFP_Context", k: int = 15, custom_query: str = None) -> str:
        """
        Retrieves proposal form pages from ChromaDB.
        
        IMPROVED STRATEGY:
        1. Find the most relevant 'anchor' pages using semantic search.
        2. Identify the likely start of the proposal form.
        3. Retrieve a generous window of CONTIGUOUS pages (e.g., start_page to start_page + 10)
           to ensure we capture multi-page tables without gaps.
           
        Args:
            collection_name: ChromaDB collection to search
            k: Number of results to retrieve
            custom_query: Optional custom search query (e.g., RFP's section names for vendor proposals)
        """
        db = Chroma(
            persist_directory=self.chroma_path, 
            embedding_function=self.embedding, 
            collection_name=collection_name
        )
        
        # 1. Find Anchor Pages - use custom query if provided (e.g., RFP sections for vendors)
        if custom_query:
            query = custom_query
            print(f"DEBUG: Using custom query: {query[:100]}...")
        else:
            # Improved query - includes actual terms found in proposal forms
            query = "Proposal Submission Description of Work Quantity Unit Unit Cost Total Item SF LF LS Structural Repairs"
        results = db.similarity_search(query, k=k)
        
        if not results:
            return ""

        # CRITICAL: For vendor extraction (custom_query = RFP sections), 
        # use search results DIRECTLY - these match the RFP sections
        if custom_query:
            print("DEBUG: Using semantic search results directly for vendor extraction")
            print(f"DEBUG: Found {len(results)} matching chunks")
            for doc in results[:5]:
                p = doc.metadata.get('page')
                print(f" - Page {p}: {doc.page_content[:60]}...")
            
            # Return the chunks that match the RFP section query
            return "\n\n".join([doc.page_content for doc in results])

        # 2. For RFP extraction (no custom_query), identify relevant pages
        found_pages = set()
        print("DEBUG: Search Results Candidates:")
        for doc in results:
            p = doc.metadata.get('page')
            if p is not None:
                p_int = int(p)
                found_pages.add(p_int)
                print(f" - Page {p_int}: {doc.page_content[:50]}...")
        
        if not found_pages:
            return "\n\n".join([doc.page_content for doc in results])
            
        # IMPROVED STRATEGY: Fetch all found pages + subsequent page (for table continuity)
        # Instead of a single window, we fetch clusters of relevant content
        pages_to_fetch = set()
        for p in found_pages:
            pages_to_fetch.add(p)
            pages_to_fetch.add(p + 1)  # Add next page to capture tables spanning page headers
            
        sorted_pages = sorted(list(pages_to_fetch))
        print(f"DEBUG: Form Context: Fetching {len(sorted_pages)} relevant pages: {sorted_pages}")

        import re
        
        # DYNAMIC APPROACH: Prioritize chunks that look like form tables
        # Instead of just $ signs (which catch insurance text), look for table structure patterns
        table_patterns = [
            re.compile(r'\b(Unit Cost|Unit Price|Total|Quantity|Qty)\b', re.IGNORECASE),  # Column headers
            re.compile(r'\b\d+\s*(SF|LF|LS|EA|CY|SY)\b', re.IGNORECASE),  # Quantity with units
            re.compile(r'^[IVX]+\s+\w', re.MULTILINE),  # Roman numeral sections (I, II, III...)
            re.compile(r'^\s*\d+\s+\w{3,}', re.MULTILINE),  # Line items starting with number
        ]
        
        def score_chunk(text: str) -> int:
            """Score a chunk based on how likely it is to be a form table."""
            score = 0
            for pattern in table_patterns:
                if pattern.search(text):
                    score += 1
            return score
        
        all_chunks = []
        for p in sorted_pages:
            try:
                result = db.get(where={"page": p})
                page_texts = result['documents']
                if page_texts:
                    for text in page_texts:
                        all_chunks.append((score_chunk(text), p, text))
            except Exception as e:
                print(f"WARN: Failed to fetch page {p}: {e}")
        
        # Sort by score (highest first), then by page number
        all_chunks.sort(key=lambda x: (-x[0], x[1]))
        
        # Take all high-scoring chunks + some lower-scoring for context
        high_score_chunks = [c for c in all_chunks if c[0] >= 2]
        low_score_chunks = [c for c in all_chunks if c[0] < 2][:10]  # Limit low-score chunks
        
        selected_chunks = high_score_chunks + low_score_chunks
        
        print(f"DEBUG: Form Context: Retained {len(selected_chunks)} chunks from {len(sorted_pages)} pages")
        print(f"  - High-score table chunks: {len(high_score_chunks)}")
        print(f"  - Low-score context chunks: {len(low_score_chunks)}")
        
        # Return content without misleading separators
        return "\n\n".join([c[2] for c in selected_chunks])
    
    def discover_form_structure(self, rfp_context: str) -> ProposalFormStructure:
        """
        Analyzes RFP content to discover the proposal form structure dynamically.
        
        Uses with_structured_output() for reliable extraction.
        """
        print("--- Form Structure Analyzer: Discovering Form Structure ---")
        
        # Create structured LLM with ProposalFormStructure schema
        structured_llm = self.llm.with_structured_output(ProposalFormStructure)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an expert RFP Analyst specializing in construction bid documents.

Your task is to analyze the RFP proposal submission form and discover its structural schema.

ANALYSIS STEPS:
1. Find the "Proposal Submission" or "Bid Form" section
2. Identify the logical tables (e.g., Pricing Sections, Additions)
3. List the EXACT column headers found
4. Classify columns as FIXED (identifiers like Item, Description) vs VENDOR (values like Qty, Unit Cost, Total)
5. Extract section headers

COLUMN CLASSIFICATION RULES:
- FIXED columns: "Item", "Description", "Scope"
- VENDOR columns: "Quantity", "Unit", "Unit Cost", "Total", "%"

Do NOT extract the actual row data values here. Just define the structure (schema)."""),
            ("user", """RFP Document Content:

{rfp_content}

Analyze this RFP and extract the complete proposal form structure.""")
        ])
        
        chain = prompt | structured_llm
        
        try:
            result = chain.invoke({"rfp_content": rfp_context})
            print(f"  ✓ Discovered {len(result.tables)} tables, {len(result.sections)} sections")
            print(f"  ✓ Fixed columns: {result.fixed_columns}")
            print(f"  ✓ Vendor columns: {result.vendor_columns}")
            return result
        except Exception as e:
            print(f"  ✗ Discovery failed: {e}")
            raise
    
    def extract_form_rows(self, rfp_context: str, structure: ProposalFormStructure) -> List[DiscoveredFormRow]:
        """
        Extracts all line items from the proposal form using the discovered structure.
        """
        print("--- Form Structure Analyzer: Extracting Form Rows ---")
        
        # DEBUG: Print a sample of the context to see what the AI is receiving
        print(f"  DEBUG: Context length = {len(rfp_context)} chars")
        print(f"  DEBUG: Context sample (first 1000 chars):\n{rfp_context[:1000]}...")
        
        # Create structured LLM for row extraction using wrapper model
        structured_llm = self.llm.with_structured_output(ExtractedRows)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are extracting line items from a vendor's filled proposal or bid form.

CRITICAL: Extract line items that belong ONLY to the following sections:
{target_sections}

You must IGNORE any summary tables or general cost overviews that do not belong to these specific sections.

For EACH line item in these sections, extract:
1. section - which of the target sections it belongs to
2. item_id - the item number or name (1, 2, 3...)
3. description - the description of work
4. quantity - quantity (extract TBD if that's what is written, or value if available)
5. unit - unit (SF, LF, LS etc)
6. unit_cost - unit cost (extract raw numbers or cid codes if garbled, or null)
7. total - total price (extract raw numbers or cid codes if garbled, or null)

DATA EXTRACTION RULES:
- Focus ONLY on the rows under the target sections.
- **PRICE EXTRACTION (Strict Literal Mode):**
  - If the value is a number (e.g., "4.10", "$150.00"), extract the NUMERIC value.
  - If the value explicitly says "TBD", extract "TBD".
  - If the cell is empty or has unreadable encoding (garbage), extract null.
  - DO NOT GUESS. Extract exactly what is visible in the column.
- Use the discovered structure as that discovered from the RFP.
- DO NOT SKIP ROWS just because prices are null/TBD. We need the full item list.
"""),
            ("user", """Document Content:

{rfp_content}

Extract all line items for the sections: {target_sections}""")
        ])
        
        chain = prompt | structured_llm
        
        try:
            result = chain.invoke({
                "rfp_content": rfp_context,
                "target_sections": ", ".join(structure.sections) if structure.sections else "All sections found in the document"
            })
            print(f"  ✓ Extracted {len(result.rows)} line items")
            return result.rows
        except Exception as e:
            print(f"  ✗ Row extraction failed: {e}")
            return []
    
    def analyze_rfp(self, collection_name: str = "RFP_Context") -> FullProposalFormAnalysis:
        """
        Main entry point: Fully analyze an RFP and return its proposal form structure.
        
        Args:
            collection_name: ChromaDB collection containing the ingested RFP
            
        Returns:
            FullProposalFormAnalysis with structure and extracted rows
        """
        # Step 1: Get context from vector store
        context = self.get_proposal_form_context(collection_name)
        
        # Step 2: Discover structure
        structure = self.discover_form_structure(context)
        
        # Step 3: Extract all rows
        rows = self.extract_form_rows(context, structure)
        
        return FullProposalFormAnalysis(structure=structure, rows=rows)


# --- Dynamic Pydantic Model Generator ---

def sanitize_column_name(name: str) -> str:
    """Convert column name to valid Python identifier."""
    return name.lower().replace(" ", "_").replace("/", "_").replace("%", "percent").replace("#", "_num")


def create_dynamic_row_model(fixed_columns: List[str], vendor_columns: List[str], num_vendors: int = 1) -> type[BaseModel]:
    """
    Generate a Pydantic model at runtime based on discovered columns.
    
    For single vendor extraction:
        - All columns appear once
        
    For multi-vendor comparison:
        - Fixed columns appear once
        - Vendor columns repeat for each vendor
    """
    fields: Dict[str, Any] = {}
    
    # Add fixed columns (appear once)
    for col in fixed_columns:
        field_name = sanitize_column_name(col)
        fields[field_name] = (Optional[str], Field(default=None, description=f"Value for '{col}'"))
    
    if num_vendors == 1:
        # Single vendor: all columns appear once
        for col in vendor_columns:
            field_name = sanitize_column_name(col)
            fields[field_name] = (Optional[str], Field(default=None, description=f"Value for '{col}'"))
    else:
        # Multi-vendor: vendor columns repeat
        for i in range(num_vendors):
            vendor_prefix = f"vendor_{i+1}_"
            for col in vendor_columns:
                field_name = vendor_prefix + sanitize_column_name(col)
                fields[field_name] = (Optional[str], Field(default=None, description=f"Vendor {i+1} value for '{col}'"))
    
    return create_model("DynamicFormRow", **fields)


def create_comparison_row_model(structure: ProposalFormStructure, vendor_names: List[str]) -> type[BaseModel]:
    """
    Create a model specifically for multi-vendor comparison matrix.
    
    Args:
        structure: Discovered form structure
        vendor_names: List of vendor names ["DueAll", "IECON", "EmpireWorks"]
    """
    fields: Dict[str, Any] = {}
    
    # Add section field
    fields["section"] = (Optional[str], Field(default=None, description="Section name"))
    
    # Add fixed columns
    for col in structure.fixed_columns:
        field_name = sanitize_column_name(col)
        fields[field_name] = (Optional[str], Field(default=None, description=f"Fixed: {col}"))
    
    # Add vendor-specific columns for each vendor
    for vendor_name in vendor_names:
        vendor_prefix = sanitize_column_name(vendor_name) + "_"
        for col in structure.vendor_columns:
            field_name = vendor_prefix + sanitize_column_name(col)
            fields[field_name] = (Optional[str], Field(default=None, description=f"{vendor_name}: {col}"))
    
    return create_model("ComparisonRow", **fields)


# --- Test ---
if __name__ == "__main__":
    print("=== Testing Form Structure Analyzer ===\n")
    
    analyzer = FormStructureAnalyzer()
    
    try:
        structure = analyzer.analyze_rfp("RFP_Context")
        
        print("\n--- Results ---")
        print(f"Form Title: {structure.form_title}")
        print(f"Tables: {[t.table_title for t in structure.tables]}")
        print(f"Fixed Columns: {structure.fixed_columns}")
        print(f"Vendor Columns: {structure.vendor_columns}")
        print(f"Sections: {structure.sections}")
        print(f"Total Rows: {len(structure.rows)}")
        
        # Test dynamic model generation
        print("\n--- Dynamic Model Test ---")
        DynamicRow = create_dynamic_row_model(
            structure.fixed_columns, 
            structure.vendor_columns,
            num_vendors=1
        )
        print(f"Generated model fields: {list(DynamicRow.model_fields.keys())}")
        
        # Test comparison model
        ComparisonRow = create_comparison_row_model(
            structure,
            ["DueAll", "IECON", "EmpireWorks"]
        )
        print(f"Comparison model fields: {list(ComparisonRow.model_fields.keys())[:10]}...")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
