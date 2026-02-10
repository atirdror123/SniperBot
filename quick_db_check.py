"""Quick check of sniper_trades - minimal version"""
import os
from dotenv import load_dotenv

load_dotenv()

# Direct REST API call to avoid SDK hanging
import requests

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("Missing credentials")
    exit()

# Use REST API directly
api_url = f"{url}/rest/v1/sniper_trades?status=eq.OPEN&select=ticker,ai_score,entry_price,created_at"
headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

try:
    resp = requests.get(api_url, headers=headers, timeout=10)
    print(f"Status: {resp.status_code}")
    data = resp.json()
    print(f"OPEN trades found: {len(data)}")
    for row in data:
        print(f"  {row.get('ticker')}: Score={row.get('ai_score')}, Entry={row.get('entry_price')}")
except Exception as e:
    print(f"Error: {e}")
