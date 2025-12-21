import requests
import json

def test_nasdaq():
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        resp = requests.get(url, headers=headers)
        data = resp.json()
        rows = data.get('data', {}).get('rows', [])
        print(f"Rows found: {len(rows)}")
        
        if rows:
            print("--- First Row Sample ---")
            print(json.dumps(rows[0], indent=2))
            
            # Test Parsing
            row = rows[0]
            cap_str = row.get('marketCap', '0')
            price_str = row.get('lastsale', '$0.00')
            print(f"\nRaw Cap: '{cap_str}'")
            print(f"Raw Price: '{price_str}'")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_nasdaq()
