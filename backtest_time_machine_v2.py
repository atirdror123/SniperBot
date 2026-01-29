"""
Time Machine Backtest V2 - Robust
---------------------------------
Validates predictive power with better error handling.
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

# Focused list of widely held stocks with likely insider activity
TICKERS = ['NVDA', 'TSLA', 'AMD', 'AAPL', 'MSFT', 'META', 'AMZN', 'GOOGL', 'JPM', 'NFLX']

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
        except Exception as e:
            print(f"    (Insider data error: {e})")
        
        # 2. 30-Day Return
        hist = stock.history(period="3mo") # Get more data to be safe
        if len(hist) < 30:
            print(f"    (Insufficient history: {len(hist)} rows)")
            return None
        
        target_date = datetime.now() - timedelta(days=30)
        # Find closest date
        try:
            idx = hist.index.get_indexer([target_date], method='nearest')[0]
            past_close = hist.iloc[idx]['Close']
            curr_close = hist.iloc[-1]['Close']
            
            ret = ((curr_close - past_close) / past_close) * 100
            
            return {
                'text': insider_text,
                'return_30d': ret,
                'cutoff_date': target_date.strftime('%Y-%m-%d')
            }
        except Exception as e:
            print(f"    (Date lookup error: {e})")
            return None
            
    except Exception as e:
        print(f"  Critical Error: {e}")
        return None

def get_past_sentiment(ticker, data):
    if not data['text']:
        return 0
    
    prompt = f"""You are a financial analyst. Analyze {ticker} insider transactions.

CRITICAL INSTRUCTION:
IGNORE any transactions AFTER {data['cutoff_date']}.
Only consider transactions ON or BEFORE {data['cutoff_date']}.

Data:
{data['text'][:2000]}

Return ONLY JSON:
{{ "sentiment": <-100 to +100 based ONLY on pre-cutoff data>, "details": "reasoning" }}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        start = text.find('{')
        end = text.rfind('}') + 1
        js = json.loads(text[start:end])
        return js.get('sentiment', 0)
    except Exception as e:
        print(f"    (AI Parse Error: {e})")
        return 0

def run():
    print("="*60)
    print("TIME MACHINE BACKTEST V2")
    print("="*60)
    
    results = []
    
    for i, ticker in enumerate(TICKERS):
        print(f"\nProcessing {ticker} [{i+1}/{len(TICKERS)}]")
        
        data = get_past_data(ticker)
        if not data:
            continue
            
        print(f"  30d Return: {data['return_30d']:+.1f}%")
        
        if ticker != TICKERS[0]: # Wait between calls
            print("  Waiting 5s...")
            time.sleep(5)
            
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
        
        # Save to file
        df.to_csv('time_machine_results.csv', index=False)
        print("Saved to time_machine_results.csv")

if __name__ == "__main__":
    run()
