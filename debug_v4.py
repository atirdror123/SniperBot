"""Debug V4 Filtering Logic"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

ticker = 'NVDA'
print(f"Testing filter on {ticker}...")
stock = yf.Ticker(ticker)

# Get History for date
hist = stock.history(period="3mo")
last_date = hist.index[-1]
target_date = last_date - timedelta(days=30)
cutoff_ts = pd.Timestamp(target_date)
print(f"Cutoff: {cutoff_ts}")

# Get Insider
df = stock.insider_transactions
if df is not None and not df.empty:
    print(f"Total Rows: {len(df)}")
    
    # Check column
    print(f"Columns: {list(df.columns)}")
    if 'Start Date' in df.columns:
        df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
        
        # Check TZ
        print(f"DF TZ: {df['Start Date'].dt.tz}")
        print(f"Cutoff TZ: {cutoff_ts.tz}")
        
        # Normalize
        if df['Start Date'].dt.tz is not None and cutoff_ts.tz is None:
             cutoff_ts = cutoff_ts.tz_localize(df['Start Date'].dt.tz)
        elif df['Start Date'].dt.tz is None and cutoff_ts.tz is not None:
             df['Start Date'] = df['Start Date'].dt.tz_localize(cutoff_ts.tz)

        print(f"Normalized Cutoff: {cutoff_ts}")
        
        # Filter
        past_df = df[df['Start Date'] <= cutoff_ts]
        print(f"Rows Before Cutoff: {len(past_df)}")
        if not past_df.empty:
            print("Preview:")
            print(past_df[['Start Date', 'Text']].head())
        else:
            print("NO ROWS PASSED FILTER")
            print("Earliest Date in DF:", df['Start Date'].min())
    else:
        print("Column 'Start Date' not found")
else:
    print("No data")
