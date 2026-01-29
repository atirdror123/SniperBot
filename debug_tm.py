"""Debug why time machine skipped everything."""
import yfinance as yf
from datetime import datetime, timedelta

ticker = 'NVDA'
print(f"Checking {ticker}...")

stock = yf.Ticker(ticker)

# 1. Check History
print("\n1. Price History:")
try:
    hist = stock.history(period="2mo")
    print(f"  Rows: {len(hist)}")
    if not hist.empty:
        print(f"  Last: {hist.iloc[-1]['Close']}")
        target = datetime.now() - timedelta(days=30)
        print(f"  Target Date: {target}")
        idx = hist.index.get_indexer([target], method='nearest')[0]
        print(f"  Found Index: {idx}")
        print(f"  Price then: {hist.iloc[idx]['Close']}")
except Exception as e:
    print(f"  Error: {e}")

# 2. Check Insider
print("\n2. Insider Data:")
try:
    df = stock.insider_transactions
    if df is not None and not df.empty:
        print(f"  Rows: {len(df)}")
        print(df.head())
        # Check if dates are in text
        print("\n  Text Preview:")
        print(df.head().to_string())
    else:
        print("  Empty or None")
except Exception as e:
    print(f"  Error: {e}")
