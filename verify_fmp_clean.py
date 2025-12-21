import os
import requests
import time
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("FMP_API_KEY")
symbol = "AAPL"

def check(url):
    print(f"Checking: {url}")
    try:
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
    except Exception as e:
        print(f"Error: {e}")

# Insider
check(f"https://financialmodelingprep.com/api/v4/insider-trading?symbol={symbol}&limit=5&apikey={api_key}")
time.sleep(1)

# Institutional
check(f"https://financialmodelingprep.com/api/v4/institutional-ownership/symbol-ownership?symbol={symbol}&apikey={api_key}")
