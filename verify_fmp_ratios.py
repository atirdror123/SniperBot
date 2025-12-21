import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("FMP_API_KEY")
symbol = "AAPL"

url = f"https://financialmodelingprep.com/stable/ratios-ttm?symbol={symbol}&apikey={api_key}"
try:
    resp = requests.get(url)
    data = resp.json()
    print(f"Type: {type(data)}")
    if isinstance(data, list):
        print(f"List Length: {len(data)}")
        if len(data) > 0:
            print(f"Keys: {list(data[0].keys())}")
    elif isinstance(data, dict):
         print(f"Keys: {list(data.keys())}")
except Exception as e:
    print(f"Error: {e}")
