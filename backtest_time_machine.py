"""
Time Machine Backtest
---------------------
Validates predictive power by:
1. Fetching current insider transaction text from Yahoo.
2. Using Gemini to parse ONLY transactions from BEFORE 30 days ago.
3. Generating a "Past Sentiment" score.
4. Comparing with ACTUAL 30-day return.

This simulates having the AI analyze data 30 days ago to predict today's price.
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

# Mix of winners/losers/active stocks
TICKERS = [
    'NVDA', 'TSLA', 'AMD', 'PLTR', 'COIN', 
    'MARA', 'MSTR', 'AAPL', 'MSFT', 'META'
]

def get_past_data(ticker):
    """Get insider text and 30d return."""
    print(f"  Fetching {ticker}...")
    try:
        stock = yf.Ticker(ticker)
        
        # 1. Insider Text
        insider_text = ""
        try:
            df = stock.insider_transactions
            if df is not None and not df.empty:
                insider_text = df.to_string()
        except: pass
        
        # 2. 30-Day Return
        hist = stock.history(period="2mo")
        if len(hist) < 30:
            return None
        
        # Price 30 days ago vs Now
        # We need the price from roughly 30 calendar days ago
        target_date = datetime.now() - timedelta(days=30)
        # Find closest date
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
        print(f"  Error: {e}")
        return None

def get_past_sentiment(ticker, data):
    """Ask AI to score based on old data only."""
    if not data['text']:
        return 0
    
    prompt = f"""You are a financial analyst backtesting a strategy.
Analyze the insider transactions for {ticker} below.

CRITICAL RULE:
IGNORE any transactions that occurred AFTER {data['cutoff_date']}.
Only score sentiment based on transactions ON or BEFORE {data['cutoff_date']}.

Input Data:
{data['text'][:2000]}

Return ONLY JSON:
{{
    "sentiment": <-100 to +100 based ONLY on data before {data['cutoff_date']}>,
    "transaction_count": <how many valid pre-cutoff transactions found>
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.replace('```json', '').replace('```', '').strip()
        js = json.loads(text)
        return js.get('sentiment', 0)
    except:
        return 0

def run():
    print("="*60)
    print("TIME MACHINE BACKTEST")
    print("Can AI predict the last 30 days?")
    print("="*60)
    
    results = []
    
    for i, ticker in enumerate(TICKERS):
        print(f"\nProcessing {ticker} [{i+1}/{len(TICKERS)}]")
        
        data = get_past_data(ticker)
        if not data:
            print("  No data, skipping.")
            continue
            
        print(f"  30d Return: {data['return_30d']:+.1f}%")
        
        # Rate limit wait
        if i > 0:
            print("  Waiting 10s...")
            time.sleep(10)
            
        sentiment = get_past_sentiment(ticker, data)
        print(f"  AI Past Sentiment: {sentiment:+d}")
        
        results.append({
            'Ticker': ticker,
            'Sentiment': sentiment,
            'Return_30d': data['return_30d']
        })
        
    # Analysis
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    df = pd.DataFrame(results)
    print(df)
    
    if len(df) > 2:
        corr = df['Sentiment'].corr(df['Return_30d'])
        print(f"\nCorrelation: {corr:+.3f}")
        
        if corr > 0.2:
            print("✅ POSITIVE PREDICTIVE SIGNAL DETECTED")
        else:
            print("⚠️ NO STRONG SIGNAL (May need more data/tuning)")

if __name__ == "__main__":
    run()
