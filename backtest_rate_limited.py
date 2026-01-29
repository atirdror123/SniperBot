"""
Rate-Limited AI Lens Backtest

Handles Gemini free tier (15 RPM) by:
1. Using 5-second delays between requests
2. Testing only 10 stocks to complete quickly
3. Proper error handling for rate limits
"""
import os
import json
import warnings
import time
from datetime import datetime
from dotenv import load_dotenv

warnings.filterwarnings('ignore')
load_dotenv()

import pandas as pd
import numpy as np
import yfinance as yf
import google.generativeai as genai

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Smaller test set for quick validation
TEST_TICKERS = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'JPM', 'TSLA', 'META', 'CRM', 'ABNB', 'AMD']

def get_yahoo_data(ticker):
    """Get insider data from Yahoo."""
    try:
        stock = yf.Ticker(ticker)
        
        insider_text = ""
        try:
            df = stock.insider_transactions
            if df is not None and not df.empty:
                insider_text = df.to_string()
        except:
            pass
        
        holders_text = ""
        try:
            h = stock.major_holders
            if h is not None and not h.empty:
                holders_text = h.to_string()
        except:
            pass
        
        return {
            'insider': insider_text,
            'holders': holders_text,
            'has_data': bool(insider_text or holders_text)
        }
    except:
        return {'insider': '', 'holders': '', 'has_data': False}

def parse_with_ai(ticker, data, retry_count=0):
    """Parse with AI, handling rate limits."""
    if not data['has_data']:
        return {'sentiment': 0, 'success': False, 'reason': 'no_data'}
    
    prompt = f"""For {ticker}, analyze this and return ONLY JSON:

INSIDER: {data['insider'][:800] if data['insider'] else 'None'}
HOLDERS: {data['holders'][:300] if data['holders'] else 'None'}

Return ONLY: {{"sentiment": -100 to +100, "buys": count, "sells": count}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Extract JSON
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            text = text[start:end]
        
        result = json.loads(text)
        return {
            'sentiment': result.get('sentiment', 0),
            'buys': result.get('buys', 0),
            'sells': result.get('sells', 0),
            'success': True
        }
        
    except Exception as e:
        error_str = str(e)
        if 'quota' in error_str.lower() or 'rate' in error_str.lower():
            if retry_count < 2:
                print(f"    Rate limit hit, waiting 60s...")
                time.sleep(60)
                return parse_with_ai(ticker, data, retry_count + 1)
        
        return {'sentiment': 0, 'success': False, 'reason': str(e)[:50]}

def get_return(ticker):
    """Get 30-day return."""
    try:
        df = yf.download(ticker, period='2mo', progress=False)
        if len(df) < 30:
            return None
        curr = df['Close'].iloc[-1]
        past = df['Close'].iloc[-30]
        return float((curr - past) / past * 100)
    except:
        return None

def run():
    print("=" * 60)
    print("RATE-LIMITED AI LENS BACKTEST")
    print(f"Started: {datetime.now().strftime('%H:%M:%S')}")
    print(f"Testing {len(TEST_TICKERS)} stocks with 5s delay between AI calls")
    print("=" * 60)
    
    results = []
    sentiments = []
    
    for i, ticker in enumerate(TEST_TICKERS):
        print(f"\n[{i+1}/{len(TEST_TICKERS)}] {ticker}")
        
        # 1. Yahoo data
        data = get_yahoo_data(ticker)
        print(f"  Yahoo: {'✓' if data['has_data'] else '✗'}")
        
        # 2. AI parse (with rate limit delay)
        if i > 0:
            print("  Waiting 5s for rate limit...")
            time.sleep(5)
        
        ai = parse_with_ai(ticker, data)
        print(f"  AI: {'✓' if ai['success'] else '✗'} sentiment={ai['sentiment']:+d}")
        
        if ai['success']:
            sentiments.append(ai['sentiment'])
        
        # 3. Get return
        ret = get_return(ticker)
        print(f"  Return: {ret:+.1f}%" if ret else "  Return: N/A")
        
        results.append({
            'ticker': ticker,
            'has_data': data['has_data'],
            'ai_success': ai['success'],
            'sentiment': ai['sentiment'],
            'return_30d': ret
        })
    
    # Analysis
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    
    df = pd.DataFrame(results)
    
    # Key test: Score variation
    print("\n📈 SCORE VARIATION (Key Test):")
    if sentiments:
        unique = len(set(sentiments))
        print(f"  Unique values: {unique}")
        print(f"  Range: {min(sentiments)} to {max(sentiments)}")
        print(f"  Values: {sentiments}")
        
        if unique >= 3:
            print("  ✅ PASSED: Varied scores (not bucketed!)")
        else:
            print("  ⚠️ FAILED: Low variation")
    
    # Correlation
    print("\n🎯 PREDICTIVE POWER:")
    valid = df[df['ai_success'] & df['return_30d'].notna()]
    if len(valid) >= 3:
        corr = valid['sentiment'].corr(valid['return_30d'])
        print(f"  Correlation: {corr:+.3f}")
    
    # Save
    df.to_csv('rate_limited_backtest.csv', index=False)
    print(f"\n📁 Saved to rate_limited_backtest.csv")
    print(f"Finished: {datetime.now().strftime('%H:%M:%S')}")

if __name__ == "__main__":
    run()
