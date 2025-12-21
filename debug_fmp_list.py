import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_list():
    api_key = os.getenv("FMP_API_KEY")
    url = f"https://financialmodelingprep.com/api/v3/available-traded/list?apikey={api_key}"
    print(f"Testing URL: .../available-traded/list?apikey=HIDDEN")
    
    try:
        resp = requests.get(url)
        print(f"Status: {resp.status_code}")
        if resp.status_code != 200:
             print(f"Response: {resp.text}")
        else:
             data = resp.json()
             print(f"Success! Got {len(data)} items.")
             print("Sample:", data[:2])
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_list()
