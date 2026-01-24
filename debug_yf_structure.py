import yfinance as yf
import pandas as pd
from network_utils import get_retry_session

tickers = ["AAPL", "MSFT", "GOOG", "TSLA"]
session = get_retry_session()

print("Downloading batch...")
data = yf.download(
    tickers, 
    period="1mo", 
    interval="1d", 
    group_by='ticker', 
    progress=False, 
    threads=True, 
    auto_adjust=True,
    session=session
)

print("\n--- DATA INFO ---")
print(f"Type: {type(data)}")
print(f"Columns: {data.columns}")
if isinstance(data.columns, pd.MultiIndex):
    print(f"Levels: {data.columns.levels}")

print("\n--- ACCESS TEST ---")
for t in tickers:
    try:
        if t in data.columns.levels[0]:
            print(f"{t}: FOUND in Level 0")
            df = data[t]
            print(f"  Shape: {df.shape}")
            print(f"  Close exist? {'Close' in df.columns}")
        else:
            print(f"{t}: NOT FOUND in Level 0")
    except Exception as e:
        print(f"{t}: Error {e}")
