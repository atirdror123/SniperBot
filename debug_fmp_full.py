import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_screener():
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        print("Error: No API Key found.")
        return

    # 1. Minimal Test (Just limit)
    url = f"https://financialmodelingprep.com/api/v3/stock-screener?limit=1&apikey={api_key}"
    print(f"Testing URL: .../stock-screener?limit=1&apikey=HIDDEN")
    
    try:
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
        print(f"Response: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

    # 2. Full Params Test (As used in bot)
    print("\nTesting Full Params...")
    params = {
        "marketCapMoreThan": 100000000,
        "priceMoreThan": 2,
        "volumeMoreThan": 50000,
        "exchange": "NASDAQ,NYSE,AMEX",
        "isEtf": "false",
        "limit": 5,
        "apikey": api_key
    }
    url2 = "https://financialmodelingprep.com/api/v3/stock-screener"
    try:
        resp = requests.get(url2, params=params)
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
             print(f"Response: {resp.text}")
        else:
             print("Success! (First 50 chars):", resp.text[:50])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_screener()
