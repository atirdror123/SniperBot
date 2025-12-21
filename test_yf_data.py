import yfinance as yf
import pandas as pd

def test_yf_features(ticker_symbol):
    print(f"--- Examining {ticker_symbol} via YFinance ---")
    ticker = yf.Ticker(ticker_symbol)
    
    # 1. Fundamentals (Oracle Lens)
    try:
        info = ticker.info
        roe = info.get('returnOnEquity', 'N/A')
        peg = info.get('pegRatio', 'N/A')
        fcf = info.get('freeCashFlow', 'N/A')
        print(f"[FUNDAMENTALS] ROE: {roe}, PEG: {peg}, FCF: {fcf}")
    except Exception as e:
        print(f"[FUNDAMENTALS] Failed: {e}")

    # 2. Insider Trading (Hunter Lens)
    try:
        # insider_purchases or insider_transactions
        insiders = ticker.insider_purchases
        if insiders is not None and not insiders.empty:
            print(f"[INSIDERS] Found Data ({len(insiders)} rows)")
            print(insiders.head(3))
        else:
            # Try transactions
            trans = ticker.insider_transactions
            if trans is not None and not trans.empty:
                print(f"[INSIDERS] Transactions found ({len(trans)} rows)")
                print(trans.head(3))
            else:
                print("[INSIDERS] No data found.")
    except Exception as e:
        print(f"[INSIDERS] Failed: {e}")

    # 3. Institutional/Major Holders (Quant Lens Proxy)
    try:
        major = ticker.major_holders
        inst = ticker.institutional_holders
        if inst is not None and not inst.empty:
            print(f"[INSTITUTIONS] Found {len(inst)} holders.")
            print(inst.head(2))
        else:
            print("[INSTITUTIONS] No data.")
    except Exception as e:
        print(f"[INSTITUTIONS] Failed: {e}")

test_yf_features("AAPL")
test_yf_features("NVDA")
