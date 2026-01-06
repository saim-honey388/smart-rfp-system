
import sys
import pdfplumber
from pathlib import Path

def analyze_pdf_encoding(pdf_path, page_num=6):
    """
    Analyzes the font and encoding information of a specific page in a PDF.
    Focuses on potential table data.
    """
    print(f"--- Analyzing PDF: {pdf_path} ---")
    print(f"--- Focusing on Page Index: {page_num} (Page {page_num+1}) ---")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            if page_num >= len(pdf.pages):
                print(f"Error: PDF only has {len(pdf.pages)} pages.")
                return

            page = pdf.pages[page_num]
            
            # 1. Extract raw text
            text = page.extract_text()
            print("\n--- 1. Raw Text Extraction Sample ---")
            print(text[:500] + "..." if len(text) > 500 else text)

            # 2. Analyze Characters
            print("\n--- 2. Character Analysis (Sample of potential table data) ---")
            print(f"{'Char':<10} | {'Unicode (Hex)':<15} | {'Font Name':<30} | {'Encoding':<20} | {'CID/ID':<10}")
            print("-" * 95)
            
            chars = page.chars
            # Filter for characters that might be in the table (roughly middle of page or specific columns)
            # Or just print a distinctive sample
            
            count = 0
            found_problematic = False
            
            for char in chars:
                # We are looking for the problematic pattern seen earlier: (cid:0)(cid:2)...
                # In pdfplumber, a character that fails to map might show up as (cid:x) 
                # OR it might be a valid character object but with strange font properties.
                
                text_char = char.get("text")
                font_name = char.get("fontname", "Unknown")
                encoding = char.get("encoding", "Unknown")
                
                # Check for characters that look like they belong to the price column
                # Checking y-coordinates or just interesting chars
                
                # Let's print chars that have 'Identity-H' encoding or look suspicious
                if "Identity-H" in str(encoding) or count < 20: 
                    # Get unicode hex
                    unicode_hex = ' '.join(hex(ord(c)) for c in text_char)
                    
                    print(f"{repr(text_char):<10} | {unicode_hex:<15} | {font_name[:30]:<30} | {str(encoding):<20} | {char.get('upright')}")
                    count += 1
                
                if "(cid:" in text_char:
                     found_problematic = True
                     print(f"\n!!! FOUND CID LITERAL: {text_char} !!!")
                     print(f"Font: {font_name}, Encoding: {encoding}")

            print("\n--- 3. Font Summary ---")
            # Group by font
            fonts = {}
            for char in chars:
                f = char.get("fontname", "Unknown")
                if f not in fonts:
                    fonts[f] = {"count": 0, "encodings": set()}
                fonts[f]["count"] += 1
                fonts[f]["encodings"].add(str(char.get("encoding")))
            
            for f, data in fonts.items():
                print(f"Font: {f}")
                print(f"  Count: {data['count']}")
                print(f"  Encodings: {data['encodings']}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    # Default to the known problematic PDF if no arg provided
    target_pdf = "/home/linux/Projects/RFP System/drive-download-20251229T152332Z-1-001/AV -  Bid Analysis & Bids.pdf"
    
    if len(sys.argv) > 1:
        target_pdf = sys.argv[1]
        
    analyze_pdf_encoding(target_pdf, page_num=6) # Analyzes page 7 (index 6) where we saw issues
