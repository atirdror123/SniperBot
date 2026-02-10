import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}"
}

print("Checking OPEN trades in sniper_trades...")
try:
    resp = requests.get(f"{url}/rest/v1/sniper_trades?status=eq.OPEN&select=ticker", headers=headers, timeout=10)
    data = resp.json()
    print(f"Count: {len(data)}")
    tickers = [r.get('ticker') for r in data]
    print(f"Tickers: {', '.join(tickers)}")
except Exception as e:
    print(f"Error: {e}")
