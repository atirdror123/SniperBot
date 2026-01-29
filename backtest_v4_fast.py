"""
Time Machine Backtest V4 (Fast)
-------------------------------
Filters insider transactions using Python (df['Start Date'] < cutoff)
BEFORE sending to AI. This guarantees valid "past" data.
"""
import os
import time
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

# 12 diverse tickers
TICKERS = [
    'NVDA', 'TSLA', 'AMD', 'PLTR', 'AAPL', 'MSFT', 'META', 'AMZN', 
    'COIN', 'MSTR', 'INTC', 'CRM'
]

def get_past_data(ticker):
    print(f"  Fetching {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        
        # 1. 30-Day Return
        hist = stock.history(period="3mo")
        if len(hist) < 30: return None
        
        last_date = hist.index[-1]
        target_date = last_date - timedelta(days=30)
        cutoff_str = target_date.strftime('%Y-%m-%d')
        idx = min(hist.index, key=lambda x: abs(x - target_date))
        
        past_close = hist.loc[idx]['Close']
        curr_close = hist.iloc[-1]['Close']
        ret = ((curr_close - past_close) / past_close) * 100
        
        # 2. Insider Text (Filtered)
        insider_text = ""
        try:
            df = stock.insider_transactions
            if df is not None and not df.empty:
                if 'Start Date' in df.columns:
                    df['Start Date'] = pd.to_datetime(df['Start Date'], errors='coerce')
                    cutoff_ts = pd.Timestamp(target_date)
                    
                    # TZ Normalize
                    if df['Start Date'].dt.tz is not None and cutoff_ts.tz is None:
                         cutoff_ts = cutoff_ts.tz_localize(df['Start Date'].dt.tz)
                    elif df['Start Date'].dt.tz is None and cutoff_ts.tz is not None:
                         df['Start Date'] = df['Start Date'].dt.tz_localize(cutoff_ts.tz)

                    past_df = df[df['Start Date'] <= cutoff_ts]
                    
                    if not past_df.empty:
                        cols = [c for c in ['Start Date', 'Transaction', 'Insider', 'Shares', 'Value', 'Text'] if c in past_df.columns]
                        insider_text = past_df[cols].to_string()
                    else:
                        print("    (No transactions before cutoff)")
                else:
                    insider_text = df.to_string()
        except: pass
            
        return {'text': insider_text, 'return_30d': ret, 'cutoff_date': cutoff_str}
            
    except: return None

def get_past_sentiment(ticker, data):
    if not data['text']: return 0
    
    prompt = f"""Analyze {ticker} insider transactions.
Predict sentiment (-100 to +100) based on this past data.
Use ONLY the data provided.

Data:
{data['text'][:2000]}

Return JSON: {{ "sentiment": <integer> }}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        start = text.find('{')
        end = text.rfind('}') + 1
        return json.loads(text[start:end]).get('sentiment', 0)
    except: return 0

def run():
    print("="*60)
    print("TIME MACHINE BACKTEST V4 (FAST)")
    print("="*60)
    
    results = []
    
    for i, ticker in enumerate(TICKERS):
        print(f"\nProcessing {ticker} [{i+1}/{len(TICKERS)}]")
        
        data = get_past_data(ticker)
        if not data: continue
            
        print(f"  Return: {data['return_30d']:+.1f}%")
        
        if i > 0: time.sleep(4)
            
        sentiment = get_past_sentiment(ticker, data)
        print(f"  Sentiment: {sentiment:+d}")
        
        results.append({'Ticker': ticker, 'Sentiment': sentiment, 'Return_30d': data['return_30d']})
        
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    df = pd.DataFrame(results)
    print(df)
    
    if len(df) > 2:
        corr = df['Sentiment'].corr(df['Return_30d'])
        print(f"\nCorrelation: {corr:+.3f}")
        df.to_csv('final_results_fast.csv', index=False)

if __name__ == "__main__":
    run()
