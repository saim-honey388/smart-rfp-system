from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser
from langchain_community.vectorstores import Chroma
from backend.src.agents.rfp_architect import ProposalSchema, Category, LineItem
from backend.src.agents.ingestion import ingest_document # Reuse ingestion logic
import os
import shutil

# Use unified AI client with fallback support
from backend.src.utils.ai_client import get_chat_llm
from backend.src.utils.embeddings import get_embeddings

# --- Domain Models (Filled) ---
class FilledLineItem(LineItem):
    unit_cost: Optional[float] = Field(description="The unit cost provided by the vendor. Null if not found.")
    total_cost: Optional[float] = Field(description="The total cost provided by the vendor. Null if not found.")

class FilledCategory(Category):
    items: List[FilledLineItem]

class FilledProposal(ProposalSchema):
    vendor_name: str = Field(description="Name of the vendor")
    categories: List[FilledCategory]
    grand_total: Optional[float] = Field(description="The final Grand Total")

# --- Agent Class ---
class BidEstimator:
    def __init__(self):
        # Use unified client with OpenAI-first, Groq fallback
        self.llm = get_chat_llm(model="gpt-4o", temperature=0)
        self.parser = JsonOutputParser(pydantic_object=FilledProposal)
        self.chroma_path = os.path.abspath(os.path.join(os.getcwd(), "data/chromadb"))
        # Use unified embeddings with OpenAI-first, HuggingFace fallback
        self.embedding = get_embeddings()

    def process_proposal(self, pdf_path: str, blank_schema: ProposalSchema) -> FilledProposal:
        """
        Ingests a proposal PDF and extracts values matching the Schema.
        Follows RFPArchitect pattern: Ingest -> Retrieve Context -> LLM Extraction.
        """
        import re
        vendor_name = os.path.basename(pdf_path).replace(".pdf", "")
        safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', vendor_name)[:63]
        collection_name = f"Proposal_{safe_name}"
        
        # 1. Ingest (Force Refresh)
        print(f"--- Processing Proposal: {vendor_name} ---")
        
        # Ingestion Logic (Same as Architect/Ingestion script)
        # We delete existing to ensure clean slate
        db_reset = Chroma(persist_directory=self.chroma_path, embedding_function=self.embedding, collection_name=collection_name)
        try:
            db_reset.delete_collection()
        except:
            pass
            
        ingest_document(pdf_path, collection_name, chunk_size=1000, chunk_overlap=200)
        
        # 2. Retrieve Context (Mirroring Architect's High K strategy)
        db = Chroma(persist_directory=self.chroma_path, embedding_function=self.embedding, collection_name=collection_name)
        
        # Broad query to catch the pricing table anywhere
        query = "Bid Form Proposal Price Sheet Schedule of Values Unit Cost Total"
        relevant_docs = db.similarity_search(query, k=30) 
        
        print("\n--- Debug: Retrieved Chunks (Sorted by Page) ---")
        relevant_docs.sort(key=lambda x: x.metadata.get('page', 0))
        for i, doc in enumerate(relevant_docs):
             # Short preview log
             print(f"Chunk {i+1}: Page {doc.metadata.get('page')} (len: {len(doc.page_content)})")

        context_text = "\n\n".join([d.page_content for d in relevant_docs])
        # print(f"DEBUG Full Context: {context_text[:500]}...") # kept minimal
        
        # 3. Extraction (Mirroring Architect's Batch/Prompt style)
        print(f"--- Estimator Agent: Extracting Values for {vendor_name} ---")
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a Senior Construction Estimator. \n"
                       "You are given a 'Blank Bid Components Schema' (The Template) and a 'Vendor Proposal' (The DataSource).\n"
                       "Your Goal: Fill the Template with the Vendor's ACTUAL PRICING.\n"
                       "\n"
                       "RULES:\n"
                       "1. **Find the Data**: Look for the Bid Form/Pricing Table in the context. It normally follows the header structure.\n"
                       "2. **Map by Item**: Match 'Item ID' (1, 2, 3...) or 'Description' to the row in the Vendor's table.\n"
                       "3. **Extract Values**: \n"
                       "   - `unit_cost`: The price per unit.\n"
                       "   - `total_cost`: The extended total.\n"
                       "   - `quantity` / `unit`: If the vendor changed these, overwrite the valid. Otherwise use the schema's.\n"
                       "4. **Handle Garbage/Noise**: If the text contains artifacts (e.g. '/10/29411'), look for the *numerical currency values* (e.g. '$12,500') associated with the item.\n"
                       "   - If the vendor provided a 'Lump Sum' for a whole section, assign it to the first item.\n"
                       "5. **Identify Vendor**: Extract the Vendor Name.\n"
                       "\n"
                       "{format_instructions}"),
            ("user", "TEMPLATE SCHEMA:\n{schema}\n\nVENDOR CONTEXT:\n{context}")
        ])
        
        chain = prompt | self.llm | self.parser
        
        try:
            result = chain.invoke({
                "schema": blank_schema.model_dump_json(),
                "context": context_text,
                "format_instructions": self.parser.get_format_instructions()
            })
            return FilledProposal(**result)
        except Exception as e:
            print(f"Extraction failed for {vendor_name}: {e}")
            return None

# --- Test ---
if __name__ == "__main__":
    from backend.src.agents.rfp_architect import RFPArchitect
    
    # 1. Get Schema
    architect = RFPArchitect()
    schema = architect.generate_schema() # Get standard schema
    
    # 2. Extract from a specific proposal
    estimator = BidEstimator()
    sample_proposal = "ilovepdf_split-range/AV -  Bid Analysis & Bids-2-12.pdf" 
    
    if os.path.exists(sample_proposal):
        filled = estimator.process_proposal(sample_proposal, schema)
        if filled:
            print(filled.model_dump_json(indent=2))
    else:
        print(f"Sample proposal {sample_proposal} not found.")
