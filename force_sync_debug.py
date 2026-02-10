"""
Force Sync Debug
Diagnose why GPRK and TSM are failing to submit.
Tests Price Fetching -> Order Submission step-by-step.
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
print("🛠️ FORCE SYNC DEBUGGER")
print("="*60)

for t in TARGETS:
    ticker = t['ticker']
    qty = t['qty']
    print(f"\n🔎 Analyzing {ticker}...")
    
    # 1. Test Price Fetch (CRITICAL: Bracket orders need price)
    print("  1. Fetching Live Price...")
    try:
        price = client.get_live_price(ticker)
        print(f"     Price: ${price}")
        
        if price <= 0:
            print("     ❌ PRICE ZERO/MISSING. Cannot submit bracket order.")
            # FALLBACK: Try to get last trade directly to see if data is the issue
            try:
                quote = client.get_quote(ticker)
                print(f"     Quote debug: {quote}")
            except Exception as e:
                print(f"     Quote error: {e}")
            continue
            
    except Exception as e:
        print(f"     ❌ Price Fetch Error: {e}")
        continue

    # 2. Check Existing
    print("  2. Checking Duplicates...")
    try:
        # We assume get_orders is fixed now
        orders = client.get_orders(status="open") 
        existing = next((o for o in orders if o.symbol == ticker), None)
        if existing:
            print(f"     ⚠️ Pending Order Exists: {existing.id} ({existing.status})")
            continue
    except Exception as e:
        print(f"     ⚠️ Check Error: {e}")

    # 3. Submit
    print("  3. Submitting Order...")
    try:
        order = client.submit_bracket_order(ticker, qty)
        print(f"     ✅ SUBMITTED! ID: {order.id}")
    except Exception as e:
        print(f"     ❌ SUBMISSION FAILED: {e}")
        if hasattr(e, 'response'):
            print(f"     API Response: {e.response.text}")

print("\n" + "="*60)
