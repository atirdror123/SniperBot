"""
Fix database - MINIMAL version with hardcoded values, no yfinance
Data from user's scan screenshot: GPRK (163), TSM (153), VIST (153)
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("ERROR: Missing SUPABASE_URL or SUPABASE_KEY")
    exit(1)

headers = {
    "apikey": key,
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "Prefer": "return=representation"
}

POSITION_SIZE = 2000

# Hardcoded from scan results (prices from Yahoo on 2026-01-30)
stocks = [
    {"ticker": "GPRK", "entry_price": 8.49, "raw_score": 163},
    {"ticker": "TSM", "entry_price": 203.50, "raw_score": 153},
    {"ticker": "VIST", "entry_price": 58.75, "raw_score": 153},
]

print("=== FIXING DATABASE ===\n")

for stock in stocks:
    ticker = stock["ticker"]
    entry_price = stock["entry_price"]
    
    # Calculate correct values
    quantity = int(POSITION_SIZE // entry_price)
    invested_amount = round(quantity * entry_price, 2)
    normalized_score = round((stock["raw_score"] / 200) * 100, 1)  # User's formula
    
    print(f"{ticker}:")
    print(f"  Price: ${entry_price}")
    print(f"  Qty: {quantity} shares (${POSITION_SIZE} / ${entry_price})")
    print(f"  Invested: ${invested_amount}")
    print(f"  Score: {normalized_score} (was {stock['raw_score']})")
    
    # Check if exists
    check_url = f"{url}/rest/v1/sniper_trades?ticker=eq.{ticker}&status=eq.OPEN&select=id"
    try:
        check_resp = requests.get(check_url, headers=headers, timeout=5)
        existing = check_resp.json() if check_resp.status_code == 200 else []
    except Exception as e:
        print(f"  ERROR checking: {e}")
        continue
    
    if existing:
        # Update
        update_url = f"{url}/rest/v1/sniper_trades?ticker=eq.{ticker}&status=eq.OPEN"
        update_data = {"quantity": quantity, "invested_amount": invested_amount, "ai_score": normalized_score}
        try:
            resp = requests.patch(update_url, headers=headers, json=update_data, timeout=5)
            print(f"  UPDATED: {resp.status_code}")
        except Exception as e:
            print(f"  ERROR updating: {e}")
    else:
        # Insert
        insert_url = f"{url}/rest/v1/sniper_trades"
        insert_data = {
            "ticker": ticker,
            "entry_price": entry_price,
            "quantity": quantity,
            "invested_amount": invested_amount,
            "status": "OPEN",
            "ai_score": normalized_score,
            "stop_loss_price": round(entry_price * 0.97, 2),
            "take_profit_price": round(entry_price * 1.10, 2)
        }
        try:
            resp = requests.post(insert_url, headers=headers, json=insert_data, timeout=5)
            print(f"  INSERTED: {resp.status_code}")
            if resp.status_code >= 400:
                print(f"    {resp.text[:200]}")
        except Exception as e:
            print(f"  ERROR inserting: {e}")
    print()

# Verify
print("=== VERIFICATION ===")
try:
    verify_url = f"{url}/rest/v1/sniper_trades?status=eq.OPEN&select=ticker,quantity,ai_score"
    verify_resp = requests.get(verify_url, headers=headers, timeout=5)
    data = verify_resp.json()
    print(f"OPEN trades: {len(data)}")
    for r in data:
        print(f"  {r.get('ticker')}: Qty={r.get('quantity')}, Score={r.get('ai_score')}")
except Exception as e:
    print(f"Verification error: {e}")

print("\nDone! Refresh dashboard.")
