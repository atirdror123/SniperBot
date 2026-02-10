"""
Force Sync Debug V2
Attempts simplfied Market Order if Bracket fails.
"""
from alpaca_client import get_alpaca_client
import sys

# Target Missing Stocks
TARGETS = [
    {"ticker": "GPRK", "qty": 235},
    {"ticker": "TSM", "qty": 9}
]

client = get_alpaca_client()

print("="*60)
print("🛠️ FORCE SYNC V2 (Fallback Mode)")
print("="*60)

for t in TARGETS:
    ticker = t['ticker']
    qty = t['qty']
    print(f"\n🔎 {ticker}...")

    # 1. Check Duplicates
    try:
        orders = client.get_orders(status="open") 
        existing = next((o for o in orders if o.symbol == ticker), None)
        if existing:
            print(f"     ⚠️ PENDING: {existing.id}")
            continue
    except: pass
    
    existing_pos = client.get_position(ticker)
    if existing_pos:
         print(f"     ⚠️ OWNED: {existing_pos.qty}")
         continue

    # 2. Try Standard Bracket
    print("  Attempt 1: Bracket Order...")
    try:
        order = client.submit_bracket_order(ticker, qty)
        print(f"     ✅ BRACKET SUBMITTED: {order.id}")
        continue
    except Exception as e:
        print(f"     ❌ Bracket Failed: {e}")
        if hasattr(e, 'response'): print(f"     API: {e.response.text}")

    # 3. Fallback: Simple Market Order (No Stop Loss)
    print("  Attempt 2: Simple Market Order (Fallback)...")
    try:
        order = client.submit_market_order(ticker, qty, side="buy")
        print(f"     ✅ MARKET ORDER SUBMITTED: {order.id}")
        print("     ⚠️ WARNING: No Stop Loss attached.")
    except Exception as e:
        print(f"     ❌ Market Order Failed: {e}")
        if hasattr(e, 'response'): print(f"     API: {e.response.text}")

print("\n" + "="*60)
