import requests
import json

# Use the RFP ID from the logs: 7f4f6136-16ed-47be-a16c-b0aecccbbb5d
rfp_id = "7f4f6136-16ed-47be-a16c-b0aecccbbb5d"
url = f"http://localhost:8000/api/analysis/rfp/{rfp_id}/dimensions"

try:
    print(f"Requesting dimensions for RFP: {rfp_id}")
    res = requests.post(url)
    print(f"Status Code: {res.status_code}")
    if res.status_code == 200:
        data = res.json()
        print(json.dumps(data, indent=2))
        
        dims = data.get("dimensions", [])
        has_cost = any(d['id'] == 'cost' for d in dims)
        print(f"\nHas 'cost' dimension: {has_cost}")
    else:
        print("Response:", res.text)

except Exception as e:
    print(f"Error: {e}")
