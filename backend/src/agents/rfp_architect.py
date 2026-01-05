from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.vectorstores import Chroma
import os

# Use unified AI client with fallback support
from backend.src.utils.ai_client import get_chat_llm
from backend.src.utils.embeddings import get_embeddings

# --- Domain Models ---
class LineItem(BaseModel):
    item_id: str = Field(description="The item number or ID")
    description: str = Field(description="Description of the work item")
    quantity: Optional[str] = Field(default=None, description="Quantity specified")
    unit: Optional[str] = Field(default=None, description="Unit of measurement")
    pre_filled_unit_cost: Optional[str] = Field(default=None, description="Pre-filled Unit Cost if present")
    extra_fields: Dict[str, str] = Field(default_factory=dict, description="Any other columns found in the table (e.g., 'Notes', 'Material Ref'). Key=Header Name, Value=Content")

class Category(BaseModel):
    name: str = Field(description="Category name")
    items: List[LineItem] = Field(description="List of line items")

class ProposalSchema(BaseModel):
    title: str = Field(description="Title of the table")
    rfp_headers: List[str] = Field(description="List of column headers found in the RFP table (e.g. 'Item', 'Description', 'Qty').")
    categories: List[Category] = Field(description="List of categories in the table")

# --- Agent Class ---
class DiscoveredSections(BaseModel):
    sections: List[str] = Field(description="List of exact Section Headers found in the Proposal/Pricing Form (e.g., 'I Structural', 'General Conditions')")

# --- Agent Class ---
class RFPArchitect:
    def __init__(self):
        # Use unified client with OpenAI-first, Groq fallback
        self.llm = get_chat_llm(model="gpt-4o", temperature=0)
        self.parser = JsonOutputParser(pydantic_object=ProposalSchema)
        self.discovery_parser = JsonOutputParser(pydantic_object=DiscoveredSections)
        self.chroma_path = os.path.abspath(os.path.join(os.getcwd(), "data/chromadb"))
        # Use unified embeddings with OpenAI-first, HuggingFace fallback
        self.embedding = get_embeddings()
        
    def get_rfp_context(self, query="Proposal Submission Form Bid Sheet Price Table General Conditions Structural Balcony Restoration Painting Stucco Column/Posts Chase Exterior Façade Additions"):
        """Retrieves relevant chunks from ChromaDB for the schema."""
        db = Chroma(persist_directory=self.chroma_path, embedding_function=self.embedding, collection_name="RFP_Context")
        results = db.similarity_search(query, k=25) # High k to capture all pages
        
        print("\n--- Debug: Retrieved Chunks (Sorted by Page) ---")
        results.sort(key=lambda x: x.metadata.get('page', 0))
        for i, doc in enumerate(results):
             print(f"Chunk {i+1}: Page {doc.metadata.get('page')} (len: {len(doc.page_content)})")
        print("-------------------------------\n")
        
        return "\n\n".join([doc.page_content for doc in results])

    def discover_sections(self, rfp_content: str) -> List[str]:
        """Scans the RFP to identify the list of Pricing Sections dynamically."""
        print("--- Architect Agent: Discovering Sections ---")
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Senior Quantity Surveyor. Scan the RFP text and identify the TABLE OF CONTENTS of the 'Proposal Submission' or 'Pricing' section.\n"
                       "Return a list of the EXACT Section Headers found (e.g., 'I Structural', 'II Balcony', 'General Conditions').\n"
                       "Look for:\n"
                       " - Main Scope Sections (I, II, III...)\n"
                       " - General Conditions / Mobilization\n"
                       " - Additions / Alternates / Unit Prices / Options\n"
                       "\n"
                       "Do not invent sections. Only list what is explicitly present as a pricing table header.\n"
                       "\n"
                       "{format_instructions}"),
            ("user", "RFP Context:\n{rfp_content}\n\nTask: List ALL Pricing/Proposal Section Headers, including Additions.")
        ])
        
        chain = prompt | self.llm | self.discovery_parser
        try:
            result = chain.invoke({
                "rfp_content": rfp_content,
                "format_instructions": self.discovery_parser.get_format_instructions()
            })
            sections = result.get("sections", [])
            print(f"DEBUG: Discovered Sections: {sections}")
            return sections
        except Exception as e:
            print(f"Discovery failed: {e}")
            return []

    def extract_section_batch(self, rfp_content: str, section_names: List[str]) -> ProposalSchema:
        """Extracts a specific batch of sections."""
        print(f"--- Architect Agent: Extracting Batch {section_names} ---")
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Senior Quantity Surveyor. Extract the Detailed Proposal Table for the specific sections requested.\n"
                       "You must extract ONLY these sections:\n"
                       "{target_sections}\n"
                       "\n"
                       "RULES:\n"
                       "1. Identify the TABLE HEADERS used in the RFP (e.g., 'Item', 'Description', 'Qty'). List them in 'rfp_headers'.\n"
                       "2. Extract Item ID, Description, Unit, Quantity.\n"
                       "3. If there are extra columns (e.g. 'Notes'), put them in 'extra_fields'.\n"
                       "4. If 'Unit Cost' or 'Quantity' is pre-filled/fixed in the text, extract it. Otherwise null.\n"
                       "5. Do NOT skip items. Capture every line item.\n"
                       "6. Maintain exact hierarchy.\n"
                       "\n"
                       "IMPORTANT: Output must match the schema: {{ 'title': '...', 'rfp_headers': ['...'], 'categories': [ ... ] }}\n"
                       "\n"
                       "{format_instructions}"),
            ("user", "RFP Context:\n{rfp_content}\n\nTask: Extract ONLY the sections: {target_sections}")
        ])
        
        chain = prompt | self.llm | self.parser
        try:
            result = chain.invoke({
                "rfp_content": rfp_content,
                "target_sections": ", ".join(section_names),
                "format_instructions": self.parser.get_format_instructions()
            })
            return ProposalSchema(**result)
        except Exception as e:
            print(f"Batch extraction failed for {section_names}: {e}")
            return ProposalSchema(title="Error", categories=[])

    def generate_schema(self, custom_instructions: str = None) -> ProposalSchema:
        """
        Generates the bid form schema utilizing Dynamic Discovery and Batch Extraction.
        """
        # 1. Retrieve Context
        rfp_content = self.get_rfp_context()
        
        # 2. Dynamic Discovery
        discovered_sections = self.discover_sections(rfp_content)
        
        if not discovered_sections:
            print("WARNING: No sections discovered. Falling back to generic extraction.")
            # Fallback (Legacy/Generic)
            discovered_sections = ["General Extraction"] 
        
        # 3. Batch Extraction (Batch size 3 to ensure focus/accuracy)
        BATCH_SIZE = 3
        all_categories = []
        
        collected_headers = []
        for i in range(0, len(discovered_sections), BATCH_SIZE):
            batch = discovered_sections[i : i + BATCH_SIZE]
            partial_schema = self.extract_section_batch(rfp_content, batch)
            all_categories.extend(partial_schema.categories)
            if partial_schema.rfp_headers and not collected_headers:
                collected_headers = partial_schema.rfp_headers
        
        if not collected_headers:
            collected_headers = ["Item", "Description", "Unit", "Quantity", "Unit Cost", "Total"]
            
        final_schema = ProposalSchema(title="Proposal Submission Form", categories=all_categories, rfp_headers=collected_headers) 
        return final_schema

# --- Test ---
if __name__ == "__main__":
    architect = RFPArchitect()
    schema = architect.generate_schema()
    print(schema.model_dump_json(indent=2))
