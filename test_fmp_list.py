import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv("FMP_API_KEY")

url = f"https://financialmodelingprep.com/api/v3/stock/list?apikey={key}"
print(f"Fetching: {url}")

try:
    resp = requests.get(url, timeout=30)
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Total Count: {len(data)}")
        if len(data) > 0:
            print(f"Sample: {data[0]}")
            
            # Count NYSE/NASDAQ
            count = 0
            for item in data:
                ex = item.get('exchangeShortName', '')
                if ex in ['NYSE', 'NASDAQ', 'AMEX']:
                    count += 1
            print(f"US Market Count: {count}")
    else:
        print(resp.text[:200])
except Exception as e:
    print(e)
