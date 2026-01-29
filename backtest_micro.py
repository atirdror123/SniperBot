"""
Micro Backtest - 5 Stocks, Strict Verification
Validates AI parsing on 5 major stocks with sufficient delays to guarantee success.
"""
import os
import json
import time
import warnings
from dotenv import load_dotenv
import pandas as pd
import yfinance as yf
import google.generativeai as genai

warnings.filterwarnings('ignore')
load_dotenv()

# Setup AI
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

STOCKS = ['AAPL', 'NVDA', 'TSLA', 'JPM', 'GOOGL']

def get_yahoo_data(ticker):
    print(f"  Fetching Yahoo data for {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        
        # Insider
        insider = ""
        try:
            df = stock.insider_transactions
            if df is not None and not df.empty:
                insider = df.head(20).to_string()
        except Exception: pass
        
        # Holders
        holders = ""
        try:
            h = stock.major_holders
            if h is not None and not h.empty:
                holders = h.to_string()
        except Exception: pass
        
        return {'insider': insider, 'holders': holders, 'has_data': bool(insider or holders)}
    except Exception as e:
        print(f"  Error fetching Yahoo data: {e}")
        return {'insider': '', 'holders': '', 'has_data': False}

def parse_data(ticker, data):
    if not data['has_data']:
        return {'score': 0, 'success': False, 'reason': 'No Data'}
    
    print("  Sending to Gemini...")
    prompt = f"""Analyze {ticker} insider data. Return ONLY JSON.
INSIDER: {data['insider'][:1000]}
HOLDERS: {data['holders'][:300]}

JSON FORMAT: {{"sentiment": -100 to +100, "buys": count, "sells": count}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        return {**json.loads(text), 'success': True}
    except Exception as e:
        return {'score': 0, 'success': False, 'reason': str(e)}

def run():
    print("="*50)
    print("MICRO BACKTEST START")
    print("="*50)
    
    results = []
    
    for i, ticker in enumerate(STOCKS):
        print(f"\nProcessing {ticker} [{i+1}/{len(STOCKS)}]")
        
        # 1. Get Data
        data = get_yahoo_data(ticker)
        print(f"  Data Found: {'YES' if data['has_data'] else 'NO'}")
        
        # 2. Parse (Verification)
        result = parse_data(ticker, data)
        print(f"  AI Result: {result}")
        if result['success']:
            print(f"  Sentiment Score: {result.get('sentiment', 0)}")
            
        results.append({'ticker': ticker, 'sentiment': result.get('sentiment', 0)})
        
        # 3. Wait (Rate Limit)
        if i < len(STOCKS) - 1:
            print("  Waiting 15s...")
            time.sleep(15)
            
    print("\n" + "="*50)
    print("RESULTS SUMMARY")
    print("="*50)
    df = pd.DataFrame(results)
    print(df)
    
    scores = df['sentiment'].unique()
    print("\nUnique Scores:", scores)
    if len(scores) >= 3:
        print("✅ SUCCESS: Scores are varied!")
    else:
        print("⚠️ WARNING: Scores are bucketed/zero.")

if __name__ == "__main__":
    run()
