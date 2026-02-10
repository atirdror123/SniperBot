"""
Retry Sync for GPRK and TSM
Submits orders for the missing stocks and prints FULL error details if they fail.
"""
import time
from alpaca_client import get_alpaca_client

# Only the missing ones
MISSING_TRADES = [
    {"ticker": "GPRK", "qty": 235},
    {"ticker": "TSM", "qty": 9}
]

def retry_sync():
    print("="*50)
    print("🚀 RETRYING GPRK AND TSM")
    print("="*50)
    
    try:
        client = get_alpaca_client()
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        return

    for trade in MISSING_TRADES:
        ticker = trade['ticker']
        qty = trade['qty']
        
        print(f"\nProcessing {ticker} (Qty: {qty})...")
        
        # 1. Check if Order already exists (Pending)
        try:
            orders = client.get_orders(status="open")
            existing_order = next((o for o in orders if o.symbol == ticker), None)
            if existing_order:
                print(f"  ⚠️ Found PENDING order for {ticker} (ID: {existing_order.id}). Skipping.")
                continue
        except Exception as e:
            print(f"  ⚠️ Could not check existing orders: {e}")

        # 2. Check Position
        existing_pos = client.get_position(ticker)
        if existing_pos:
            print(f"  ⚠️ Already own {existing_pos.qty} shares of {ticker}. Skipping.")
            continue
            
        # 3. Submit
        try:
            print(f"  📤 Submitting Bracket Order...")
            order = client.submit_bracket_order(
                ticker=ticker,
                qty=qty,
                stop_loss_pct=0.05,
                take_profit_pct=0.10
            )
            print(f"  ✅ SUCCESS: {ticker} Order ID: {order.id}")
            
        except Exception as e:
            print(f"  ❌ FAILED to submit {ticker}:")
            print(f"     Error: {e}")
            if hasattr(e, 'response'):
                print(f"     Response: {e.response.text}")
        
        time.sleep(1)

    print("\n" + "="*50)
    print("✅ RETRY COMPLETE")
    print("="*50)

if __name__ == "__main__":
    retry_sync()
