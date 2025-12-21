import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("FMP_API_KEY")
symbol = "AAPL"
print(f"Testing FMP Key: {api_key[:5]}...")

def test(name, url):
    print(f"\n[{name}] {url}")
    try:
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Success!")
        else:
            print(f"Error: {resp.text[:200]}")
    except Exception as e:
        print(f"Ex: {e}")

# 1. Institutional (v4)
test("Institutional", f"https://financialmodelingprep.com/api/v4/institutional-ownership/symbol-ownership?symbol={symbol}&apikey={api_key}")

# 2. Insider (v4)
test("Insider", f"https://financialmodelingprep.com/api/v4/insider-trading?symbol={symbol}&limit=100&apikey={api_key}")

# 3. Social (stable?)
test("Social", f"https://financialmodelingprep.com/stable/social-sentiment/stock?symbol={symbol}&apikey={api_key}")

# 4. Ratios (stable)
test("Ratios", f"https://financialmodelingprep.com/stable/ratios-ttm?symbol={symbol}&apikey={api_key}")

# 5. Metrics (stable)
test("Metrics", f"https://financialmodelingprep.com/stable/key-metrics-ttm?symbol={symbol}&apikey={api_key}")
