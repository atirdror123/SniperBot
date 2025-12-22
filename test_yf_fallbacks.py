import yfinance as yf
import pandas as pd

tickers = ["AAPL", "NVDA"]

print("--- TESTING YFINANCE FALLBACKS ---")

for t in tickers:
    print(f"\n[{t}]")
    try:
        tick = yf.Ticker(t)
        
        # 1. Insider Transactions (Hunter)
        print("  > Fetching Insiders...")
        insiders = tick.insider_transactions
        if insiders is not None and not insiders.empty:
            print(f"    - Found {len(insiders)} records.")
            print(insiders.head(3))
        else:
            print("    - No Insider Data found.")

        # 2. Institutional Holders (Quant/Dark Pool Proxy)
        print("  > Fetching Major Holders...")
        holders = tick.major_holders
        if holders is not None and not holders.empty:
            # YFinance changed structures recently, checking format
            print(f"    - Found Data:")
            print(holders)
        else:
            print("    - No Holders Data found.")
            
    except Exception as e:
        print(f"  Error: {e}")
