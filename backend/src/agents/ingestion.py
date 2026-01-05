import os
import shutil
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma

# Use unified embeddings with fallback support
from backend.src.utils.embeddings import get_embeddings

# Paths
DATA_DIR = os.path.join(os.getcwd(), "data")
CHROMA_PATH = os.path.join(DATA_DIR, "chromadb")
DOCS_DIR = os.path.join(DATA_DIR, "documents")

def ingest_document(file_path: str, collection_name: str, chunk_size=1000, chunk_overlap=200, reset=False):
    """
    Ingests a PDF into a specific ChromaDB collection.
    If reset=True, clears existing documents in the collection first.
    """
    print(f"--- Ingesting {os.path.basename(file_path)} into '{collection_name}' (reset={reset}) ---")
    
    # ... (PDF Loading logic) ...

    # 1. Load PDF
    loader = PyPDFLoader(file_path)
    pages = loader.load()
    print(f"Loaded {len(pages)} pages.")

    # 2. Split Text
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(pages)
    print(f"Split into {len(chunks)} chunks.")

    # 3. Embed & Link to Chroma
    # Use unified embeddings with OpenAI-first, HuggingFace fallback
    embedding_function = get_embeddings()
    
    db = Chroma(
        persist_directory=CHROMA_PATH,
        embedding_function=embedding_function,
        collection_name=collection_name
    )
    
    if reset:
        try:
            # Fetch IDs to delete (limit to large number to ensure all are captured)
            current_ids = db.get(limit=20000)['ids']
            if current_ids:
                print(f"Clearing {len(current_ids)} existing documents from '{collection_name}'...")
                # Delete in batches to avoid max URL length issues if many docs
                batch_size = 5000
                for i in range(0, len(current_ids), batch_size):
                    batch_ids = current_ids[i:i+batch_size]
                    db.delete(batch_ids)
                db.persist() # Verify persistence
        except Exception as e:
            print(f"⚠ Warning during collection reset: {e}")
    
    # 4. Add to DB
    # We assume 'reset' or 'update' logic is handled by the caller or by Chroma's unique IDs if we provided them.
    # For now, we append.
    db.add_documents(chunks)
    db.persist()
    print(f"Successfully saved to {CHROMA_PATH}")

if __name__ == "__main__":
    # Test Run
    test_pdf = "drive-download-20251229T152332Z-1-001/AV - Bid Package Audubon Villas.pdf"
    if os.path.exists(test_pdf):
        ingest_document(test_pdf, "RFP_Context")
    else:
        print(f"File not found: {test_pdf}")
