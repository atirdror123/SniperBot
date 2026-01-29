"""
Time Machine Backtest V3 - Timezone Fix
---------------------------------------
Validates predictive power with robust timezone handling.
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

# Focused list
TICKERS = ['NVDA', 'TSLA', 'AMD', 'PLTR', 'AAPL', 'MSFT', 'META', 'AMZN', 'GOOGL', 'COIN']

def get_past_data(ticker):
    print(f"  Fetching {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        
        # 1. Insider Text
        insider_text = ""
        try:
            df = stock.insider_transactions
            if df is not None and not df.empty:
                insider_text = df.to_string()
            else:
                print("    (No insider data found)")
        except: pass
        
        # 2. 30-Day Return
        hist = stock.history(period="3mo")
        if len(hist) < 30:
            print(f"    (Insufficient history)")
            return None
        
        # Robust Timezone-Aware Lookup
        # Convert target to same timezone as history index (usually US/Eastern)
        last_date = hist.index[-1]
        target_date = last_date - timedelta(days=30)
        
        # Find index closest to target_date
        # Use abs difference
        closest_date = min(hist.index, key=lambda x: abs(x - target_date))
        
        past_close = hist.loc[closest_date]['Close']
        curr_close = hist.iloc[-1]['Close']
        
        ret = ((curr_close - past_close) / past_close) * 100
        
        return {
            'text': insider_text,
            'return_30d': ret,
            'cutoff_date': target_date.strftime('%Y-%m-%d')
        }
            
    except Exception as e:
        print(f"  Error: {e}")
        return None

def get_past_sentiment(ticker, data):
    if not data['text']:
        return 0
    
    prompt = f"""Analyze {ticker} insider transactions.
IGNORE any transactions AFTER {data['cutoff_date']}.
Only score sentiment (-100 to +100) based on transactions ON or BEFORE {data['cutoff_date']}.

Data:
{data['text'][:2000]}

Return JSON: {{ "sentiment": <integer> }}"""

    try:
        response = model.generate_content(prompt)
        text = response.text
        start = text.find('{')
        end = text.rfind('}') + 1
        return json.loads(text[start:end]).get('sentiment', 0)
    except:
        return 0

def run():
    print("="*60)
    print("TIME MACHINE BACKTEST V3")
    print("="*60)
    
    results = []
    
    for i, ticker in enumerate(TICKERS):
        print(f"\nProcessing {ticker} [{i+1}/{len(TICKERS)}]")
        
        data = get_past_data(ticker)
        if not data: continue
            
        print(f"  30d Return: {data['return_30d']:+.1f}% (since {data['cutoff_date']})")
        
        if i > 0: time.sleep(5)
            
        sentiment = get_past_sentiment(ticker, data)
        print(f"  AI Past Sentiment: {sentiment:+d}")
        
        results.append({
            'Ticker': ticker,
            'Sentiment': sentiment,
            'Return_30d': data['return_30d']
        })
        
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    df = pd.DataFrame(results)
    print(df)
    
    if len(df) > 2:
        corr = df['Sentiment'].corr(df['Return_30d'])
        print(f"\nCorrelation: {corr:+.3f}")
        df.to_csv('final_backtest_results.csv', index=False)

if __name__ == "__main__":
    run()
