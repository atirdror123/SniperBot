import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("ALPACA_API_KEY")
secret_key = os.getenv("ALPACA_SECRET_KEY")
base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")

print(f"Testing connectivity to Alpaca...")
print(f"URL: {base_url}")
print(f"Key: {api_key[:5]}...")

headers = {
    "APCA-API-KEY-ID": api_key,
    "APCA-API-SECRET-KEY": secret_key
}

try:
    # Use the account endpoint directly via requests to debug
    # Alpaca V2 endpoint usually ends in /v2/account
    test_url = f"{base_url.rstrip('/')}/v2/account" if "/v2" not in base_url else f"{base_url.rstrip('/')}/account"
    print(f"Calling: {test_url}")
    
    resp = requests.get(test_url, headers=headers, timeout=10)
    print(f"Status Code: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"✅ Success! Equity: ${data.get('equity')}")
    else:
        print(f"❌ Error: {resp.text}")
except Exception as e:
    print(f"❌ Exception: {e}")
