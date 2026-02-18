
import os
import sys
import time
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

# Force load local modules
sys.path.append(os.getcwd())
try:
    from alpaca_client import get_alpaca_client
except ImportError:
    print("CRITICAL: alpaca_client.py not found or failed to import.")
    sys.exit(1)

load_dotenv()

def sync_db_to_alpaca():
    print("=" * 60)
    print("🔄 SYNCING MISSING STOCKS: DB -> ALPACA")
    print("=" * 60)

    # 1. Initialize Clients
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("Error: Supabase credentials missing.")
        return

    supabase = create_client(url, key)
    alpaca = get_alpaca_client()
    
    if not alpaca:
        print("Error: Alpaca client connection failed.")
        return

    # 2. Fetch DB 'OPEN' Trades
    print("\n1. Fetching OPEN trades from Database...")
    try:
        res = supabase.table("sniper_trades").select("*").eq("status", "OPEN").execute()
        db_trades = res.data
        print(f"   Found {len(db_trades)} active trades in DB.")
    except Exception as e:
        print(f"   Error fetching DB trades: {e}")
        return

    if not db_trades:
        print("   No open trades in DB. Nothing to sync.")
        return

    # 3. Fetch Alpaca Positions & Orders
    print("\n2. Fetching Alpaca State...")
    try:
        positions = alpaca.get_positions()
        orders = alpaca.get_orders(status="open")
        
        alpaca_tickers = {p.symbol for p in positions}
        pending_tickers = {o.symbol for o in orders}
        all_alpaca_tickers = alpaca_tickers.union(pending_tickers)
        
        print(f"   Alpaca Positions: {len(alpaca_tickers)} ({', '.join(alpaca_tickers)})")
        print(f"   Pending Orders:   {len(pending_tickers)} ({', '.join(pending_tickers)})")
        
    except Exception as e:
        print(f"   Error fetching Alpaca state: {e}")
        return

    # 4. Identify Missing Stocks
    missing = [t for t in db_trades if t['ticker'] not in all_alpaca_tickers]
    
    if not missing:
        print("\n✅ All DB trades are already in Alpaca. System is synced.")
        return

    print(f"\n⚠️ FOUND {len(missing)} UNSYNCED STOCKS:")
    for m in missing:
        print(f"   - {m['ticker']} (Entry: ${m['entry_price']})")

    # 5. Sync Missing Stocks
    print("\n🚀 EXECUTING SYNC...")
    for trade in missing:
        ticker = trade['ticker']
        qty = trade.get('quantity')
        entry = trade.get('entry_price')
        
        # Safety checks
        if not qty or qty <= 0:
            print(f"   ⚠️ Skipping {ticker}: Invalid quantity ({qty})")
            continue
            
        try:
            print(f"   Submitting {ticker} (Qty: {qty})...", end=" ")
            order = alpaca.submit_bracket_order(
                ticker=ticker,
                qty=int(qty),
                stop_loss_pct=0.05,  # 5% SL
                take_profit_pct=0.10, # 10% TP
                current_price=entry   # Use DB price as reference
            )
            print(f"✅ DONE (ID: {order.id})")
            time.sleep(0.5) # Rate limit niceity
            
        except Exception as e:
            print(f"❌ FAILED: {e}")

    print("\n" + "=" * 60)
    print("SYNC COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    sync_db_to_alpaca()
