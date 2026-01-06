
import re
import sys

def decode_cid_text(text, mapping=None):
    """
    Decodes text containing (cid:X) patterns using a provided mapping.
    """
    if mapping is None:
        # Heuristic mapping derived from comparing known values:
        # (cid:0)(cid:2)(cid:3)(cid:4)(cid:5) -> $4.10
        # 0 -> $
        # 2 -> 4
        # 3 -> .
        # 4 -> 1
        # 5 -> 0
        mapping = {
            "0": "$",
            "1": ",",  # Guessing standard separator
            "2": "4",
            "3": ".",
            "4": "1",
            "5": "0",
            # Add more based on other values if known, e.g. from total $1,122,772.91
            # But the detailed table and summary might use different fonts!
        }
    
    print("--- Decoding Configuration ---")
    print(f"Mapping: {mapping}")
    
    def replacer(match):
        cid = match.group(1)
        if cid in mapping:
            return mapping[cid]
        return f"[?{cid}?]" # Unknown CID
        
    # Regex to find (cid:123)
    pattern = re.compile(r'\(cid:(\d+)\)')
    
    decoded = pattern.sub(replacer, text)
    return decoded

if __name__ == "__main__":
    # Test with the value we saw in logs: (cid:0)(cid:2)(cid:3)(cid:4)(cid:5)
    # And maybe some others extracted from the PDF analysis
    
    sample_data = [
        "(cid:0)(cid:2)(cid:3)(cid:4)(cid:5)",       # Expected: $4.10
        "(cid:0)(cid:2)(cid:3)(cid:4)(cid:5)(cid:6)", # Expected: $4.100? or something else
        "(cid:5)(cid:20)(cid:15)(cid:17)(cid:23)",    # Valid Quantity? 
    ]
    
    # If user provided a file, read it
    if len(sys.argv) > 1:
        try:
            with open(sys.argv[1], 'r') as f:
                content = f.read()
                print(f"--- Reading from {sys.argv[1]} ---")
                print("Original:")
                print(content[:200] + "...")
                print("\nDecoded:")
                print(decode_cid_text(content))
        except Exception as e:
            print(f"Error reading file: {e}")
            
    else:
        print("--- Running Test Samples ---")
        for sample in sample_data:
            print(f"Original: {sample}")
            print(f"Decoded:  {decode_cid_text(sample)}")
            print("-" * 20)
