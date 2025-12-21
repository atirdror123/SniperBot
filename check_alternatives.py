import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_alternatives():
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        print("No API Key.")
        return

    endpoints = [
        ("Stock News (Sentiment)", f"https://financialmodelingprep.com/api/v4/stock-news-sentiments-rss-feed?limit=1&apikey={api_key}"),
        ("General News", f"https://financialmodelingprep.com/api/v3/stock_news?limit=1&apikey={api_key}"),
        ("Analyst Estimates", f"https://financialmodelingprep.com/api/v3/analyst-estimates/AAPL?limit=1&apikey={api_key}"),
        ("Key Metrics (TTM)", f"https://financialmodelingprep.com/api/v3/key-metrics-ttm/AAPL?limit=1&apikey={api_key}"),
        ("Insider Trading", f"https://financialmodelingprep.com/api/v4/insider-trading?limit=1&apikey={api_key}")
    ]

    print(f"Testing FMP Key: {api_key[:5]}...")
    
    for name, url in endpoints:
        print(f"\nTesting {name}...")
        try:
            resp = requests.get(url, timeout=5)
            print(f"Status: {resp.status_code}")
            if resp.status_code == 200:
                data = resp.json()
                if data:
                    print("SUCCESS: Data found.")
                else:
                    print("EMPTY: returns []")
            else:
                print(f"FAIL: {resp.text[:100]}")
        except Exception as e:
            print(f"ERROR: {e}")

if __name__ == "__main__":
    test_alternatives()
