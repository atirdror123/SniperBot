"""Debug AI Prompt - PLTR"""
import os
import json
import warnings
from datetime import datetime, timedelta
from dotenv import load_dotenv
import pandas as pd
import yfinance as yf
import google.generativeai as genai

warnings.filterwarnings('ignore')
load_dotenv()

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

ticker = 'PLTR'
print(f"Testing {ticker} (Last 3 Mo)...")
stock = yf.Ticker(ticker)

# Get History for cutoff
hist = stock.history(period="3mo")
last_date = hist.index[-1]
target_date = last_date - timedelta(days=30)
cutoff_ts = pd.Timestamp(target_date)
print(f"Cutoff: {cutoff_ts.date()}")

# Get Insider
df = stock.insider_transactions
text_to_send = ""

if df is not None:
    if 'Start Date' in df.columns:
        df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
        # TZ Sync
        if df['Start Date'].dt.tz is None and cutoff_ts.tz is not None:
             df['Start Date'] = df['Start Date'].dt.tz_localize(cutoff_ts.tz)
        elif df['Start Date'].dt.tz is not None and cutoff_ts.tz is None:
             cutoff_ts = cutoff_ts.tz_localize(df['Start Date'].dt.tz)

        past_df = df[df['Start Date'] <= cutoff_ts]
        print(f"Filtered Rows: {len(past_df)}")
        
        if not past_df.empty:
            cols = [c for c in ['Start Date', 'Transaction', 'Insider', 'Shares', 'Value', 'Text'] if c in past_df.columns]
            text_to_send = past_df[cols].to_string()
            print("\n--- TEXT SENT TO AI ---")
            print(text_to_send[:1000]) # First 1000 chars
        else:
            print("No past rows found")
            exit()
    else:
        print("No Start Date column")
        exit()
else:
    print("No insider data")
    exit()

# CALL AI
print("\n--- CALLING GEMINI ---")
prompt = f"""Analyze {ticker} insider transactions.
Predict sentiment (-100 to +100) based on this past data.
-100 = Heavy Selling
+100 = Heavy Buying
0 = Neutral / Mixed / Gifts

Data:
{text_to_send[:3000]}

Return JSON: {{ "sentiment": <integer>, "reason": "brief reasoning" }}"""

try:
    response = model.generate_content(prompt)
    print("\n--- RAW RESPONSE ---")
    print(response.text)
except Exception as e:
    print(f"Error: {e}")
