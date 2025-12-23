
import sys
import os
from dotenv import load_dotenv

# Add project root to path
sys.path.append("/home/linux/Projects/RFP System")

# Load env vars
load_dotenv("/home/linux/Projects/RFP System/.env")

from services.ingest.extractor import extract_text
from services.ingest.ai_extractor import extract_details_with_ai

pdf_path = "/home/linux/Projects/RFP System/Property Proposal 1.pdf"

print(f"Extracting text from: {pdf_path}")
try:
    text = extract_text(pdf_path)
    print(f"Extracted {len(text)} characters.")
except Exception as e:
    print(f"Error extracting text: {e}")
    sys.exit(1)

print("\nrunning AI extraction...")
try:
    details = extract_details_with_ai(text)
    print("\nExtracted Details:")
    print(details)
except Exception as e:
    print(f"Error in AI extraction: {e}")
