"""Quick test of FMP API endpoints"""
import os
import requests
from dotenv import load_dotenv
load_dotenv()

key = os.getenv('FMP_API_KEY')
print(f"FMP API Key: {key[:10]}..." if key else "NO KEY FOUND!")

base = "https://financialmodelingprep.com/api"

endpoints = [
    ("/v3/ratios-ttm/AAPL", "Fundamentals (ratios)"),
    ("/v3/profile/AAPL", "Company Profile"),
    ("/v3/quote/AAPL", "Quote"),
    ("/v4/insider-trading?symbol=AAPL&limit=5", "Insider Trading"),
    ("/v3/institutional-holder/AAPL", "Institutional Holders"),
    ("/v4/institutional-ownership?symbol=AAPL", "Inst Ownership"),
    ("/v3/key-metrics-ttm/AAPL", "Key Metrics"),
]

print("\n" + "="*50)
print("Testing FMP API Endpoints")
print("="*50)

for ep, name in endpoints:
    url = f"{base}{ep}{'&' if '?' in ep else '?'}apikey={key}"
    try:
        r = requests.get(url, timeout=10)
        status = r.status_code
        preview = ""
        if status == 200:
            data = r.json()
            if data:
                preview = f" | Got {len(data)} items" if isinstance(data, list) else " | Got data"
            else:
                preview = " | Empty response"
        elif status == 403:
            preview = " | ACCESS DENIED (upgrade needed)"
        print(f"{name:<25} | {status} {preview}")
    except Exception as e:
        print(f"{name:<25} | ERROR: {e}")
