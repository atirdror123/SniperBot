"""Debug Raw Yahoo Data Format"""
import yfinance as yf
import pandas as pd

# pd.set_option('display.max_columns', None)
# pd.set_option('display.max_rows', None)

ticker = 'NVDA'
print(f"Fetching {ticker}...")
stock = yf.Ticker(ticker)

try:
    df = stock.insider_transactions
    if df is not None and not df.empty:
        print("\n--- RAW DATAFRAME HEAD ---")
        print(df.head())
        
        print("\n--- TO_STRING() FORMAT ---")
        print(df.to_string())
        
        print("\n--- COLUMNS ---")
        print(df.columns)
        
        print("\n--- DTYPES ---")
        print(df.dtypes)
    else:
        print("No insider data found")
except Exception as e:
    print(f"Error: {e}")
