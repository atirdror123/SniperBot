"""
Sync Legacy Trades to Alpaca
Manually submits orders for the 3 missing stocks so they appear on the dashboard.
"""
import time
from alpaca_client import get_alpaca_client

# The 3 stocks from our database repair
TRADES_TO_SYNC = [
    {"ticker": "GPRK", "qty": 235},
    {"ticker": "TSM", "qty": 9},
    {"ticker": "VIST", "qty": 34}
]

def sync_trades():
    print("="*50)
    print("🚀 SYNCING LEGACY TRADES TO ALPACA")
    print("="*50)
    
    try:
        client = get_alpaca_client()
    except Exception as e:
        print(f"❌ Failed to connect to Alpaca: {e}")
        return

    for trade in TRADES_TO_SYNC:
        ticker = trade['ticker']
        qty = trade['qty']
        
        print(f"\nProcessing {ticker} (Qty: {qty})...")
        
        # Check if already owned
        existing = client.get_position(ticker)
        if existing:
            print(f"  ⚠️ Already own {existing.qty} shares of {ticker}. Skipping.")
            continue
            
        try:
            # Submit Market Buy
            # Note: We are buying at CURRENT market price, so P/L will start at 0
            order = client.submit_bracket_order(
                ticker=ticker,
                qty=qty,
                stop_loss_pct=0.05,
                take_profit_pct=0.10
            )
            print(f"  ✅ BUY Order Submitted: {ticker} x{qty}")
            print(f"     Order ID: {order.id}")
            
        except Exception as e:
            print(f"  ❌ Failed to submit order for {ticker}: {e}")
        
        time.sleep(1) # rate limit politeness

    print("\n" + "="*50)
    print("✅ SYNC COMPLETE - Refresh Dashboard!")
    print("="*50)

if __name__ == "__main__":
    sync_trades()
