"""
Manual Data Recovery Script
============================
Run this to manually insert missing stocks into the database and sync to Alpaca.

Usage:
    python recover_data.py TICKER1 TICKER2 TICKER3 ...

Example:
    python recover_data.py GPRK TSM VIST NVDA AMD
"""
import os
import sys
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Configuration
POSITION_SIZE = 2000  # Virtual Bank: $2,000 per position

# Alpaca Integration (optional)
try:
    from alpaca_client import get_alpaca_client
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False


def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def recover_stocks(tickers: list):
    """Insert missing stocks into database and optionally sync to Alpaca."""
    print("=" * 60)
    print("MANUAL DATA RECOVERY")
    print(f"Tickers to recover: {tickers}")
    print("=" * 60)
    
    supabase = get_supabase()
    
    # Check for Alpaca
    alpaca_client = None
    if ALPACA_AVAILABLE and os.getenv('ALPACA_API_KEY'):
        try:
            alpaca_client = get_alpaca_client()
            print("🏦 ALPACA CONNECTED\n")
        except Exception as e:
            print(f"⚠️ Alpaca not available: {e}\n")
    
    success_count = 0
    
    for ticker in tickers:
        print(f"\n📈 Processing {ticker}...")
        
        try:
            # Get current price
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1d')
            
            if hist.empty:
                print(f"  ❌ No price data for {ticker}")
                continue
            
            current_price = hist['Close'].iloc[-1]
            quantity = int(POSITION_SIZE // current_price)
            invested_amount = round(quantity * current_price, 2)
            
            print(f"  Price: ${current_price:.2f}")
            print(f"  Quantity: {quantity} shares")
            print(f"  Investment: ${invested_amount:.2f}")
            
            # Prepare trade data
            trade_data = {
                'ticker': ticker,
                'entry_price': current_price,
                'quantity': quantity,
                'invested_amount': invested_amount,
                'status': 'OPEN',
                'stop_loss_price': current_price * 0.95,  # 5% stop loss
                'take_profit_price': current_price * 1.10,  # 10% take profit
                'ai_score': 0,  # Unknown - manual recovery
                'notes': f'MANUAL RECOVERY - {datetime.now().isoformat()}',
                'raw_features': {'recovery': True, 'recovered_at': datetime.now().isoformat()}
            }
            
            # Insert to database
            supabase.table('sniper_trades').insert(trade_data).execute()
            print(f"  ✅ Saved to database")
            
            # Sync to Alpaca if available
            if alpaca_client:
                try:
                    order = alpaca_client.submit_bracket_order(
                        ticker=ticker,
                        qty=quantity,
                        stop_loss_pct=0.05,
                        take_profit_pct=0.10
                    )
                    print(f"  ✅ Alpaca order submitted: {order.id}")
                except Exception as e:
                    print(f"  ⚠️ Alpaca order failed: {e}")
            
            success_count += 1
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print("\n" + "=" * 60)
    print(f"RECOVERY COMPLETE: {success_count}/{len(tickers)} stocks recovered")
    print("=" * 60)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python recover_data.py TICKER1 TICKER2 ...")
        print("Example: python recover_data.py GPRK TSM VIST")
        sys.exit(1)
    
    tickers = [t.upper() for t in sys.argv[1:]]
    recover_stocks(tickers)
