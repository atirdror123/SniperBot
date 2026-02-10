"""
Fix existing database data - add missing stocks and correct values
"""
import os
from dotenv import load_dotenv
import requests

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

POSITION_SIZE = 2000

# 1. Check what's currently in the database
print("=== CHECKING DATABASE ===")
api_url = f"{url}/rest/v1/sniper_trades?select=ticker,entry_price,quantity,ai_score,status,created_at&order=created_at.desc&limit=10"
resp = requests.get(api_url, headers=headers, timeout=10)
print(f"Status: {resp.status_code}")
data = resp.json()
print(f"Recent trades ({len(data)}):")
for row in data:
    print(f"  {row.get('ticker')}: Price=${row.get('entry_price')}, Qty={row.get('quantity')}, Score={row.get('ai_score')}, Status={row.get('status')}")

# 2. The 3 stocks from the scan with their original data
# From the screenshot: GPRK (163), TSM (153), VIST (153)
stocks_to_fix = [
    {"ticker": "GPRK", "entry_price": 8.49, "ai_score_raw": 163},
    {"ticker": "TSM", "entry_price": 0, "ai_score_raw": 153},  # Need to get price
    {"ticker": "VIST", "entry_price": 0, "ai_score_raw": 153},  # Need to get price
]

# Get current prices for TSM and VIST
import yfinance as yf
for stock in stocks_to_fix:
    if stock["entry_price"] == 0:
        try:
            ticker_data = yf.Ticker(stock["ticker"]).history(period="1d")
            if not ticker_data.empty:
                stock["entry_price"] = round(ticker_data['Close'].iloc[-1], 2)
                print(f"Got price for {stock['ticker']}: ${stock['entry_price']}")
        except Exception as e:
            print(f"Error getting price for {stock['ticker']}: {e}")

# 3. Fix/Insert each stock
print("\n=== FIXING DATA ===")
for stock in stocks_to_fix:
    ticker = stock["ticker"]
    entry_price = stock["entry_price"]
    
    if entry_price == 0:
        print(f"Skipping {ticker} - no price available")
        continue
    
    # Calculate correct values
    quantity = int(POSITION_SIZE // entry_price)
    invested_amount = round(quantity * entry_price, 2)
    
    # Normalize score: (raw / 200) * 100 (as per user's PRD formula)
    normalized_score = round((stock["ai_score_raw"] / 200) * 100, 1)
    
    print(f"{ticker}: Qty={quantity}, Invested=${invested_amount}, Score={normalized_score}")
    
    # Check if exists
    check_url = f"{url}/rest/v1/sniper_trades?ticker=eq.{ticker}&status=eq.OPEN"
    check_resp = requests.get(check_url, headers=headers, timeout=10)
    existing = check_resp.json()
    
    if existing:
        # Update existing
        update_url = f"{url}/rest/v1/sniper_trades?ticker=eq.{ticker}&status=eq.OPEN"
        update_data = {
            "quantity": quantity,
            "invested_amount": invested_amount,
            "ai_score": normalized_score
        }
        update_resp = requests.patch(update_url, headers=headers, json=update_data, timeout=10)
        print(f"  Updated {ticker}: {update_resp.status_code}")
    else:
        # Insert new
        insert_url = f"{url}/rest/v1/sniper_trades"
        insert_data = {
            "ticker": ticker,
            "entry_price": entry_price,
            "quantity": quantity,
            "invested_amount": invested_amount,
            "status": "OPEN",
            "ai_score": normalized_score,
            "stop_loss_price": round(entry_price * 0.97, 2),
            "take_profit_price": round(entry_price * 1.10, 2),
            "notes": f"Fixed via data repair script. Original raw score: {stock['ai_score_raw']}"
        }
        insert_resp = requests.post(insert_url, headers=headers, json=insert_data, timeout=10)
        print(f"  Inserted {ticker}: {insert_resp.status_code}")
        if insert_resp.status_code >= 400:
            print(f"    Error: {insert_resp.text}")

# 4. Verify final state
print("\n=== VERIFICATION ===")
verify_url = f"{url}/rest/v1/sniper_trades?status=eq.OPEN&select=ticker,entry_price,quantity,ai_score"
verify_resp = requests.get(verify_url, headers=headers, timeout=10)
final_data = verify_resp.json()
print(f"OPEN trades: {len(final_data)}")
for row in final_data:
    print(f"  {row.get('ticker')}: Price=${row.get('entry_price')}, Qty={row.get('quantity')}, Score={row.get('ai_score')}")
