"""
AI Lens Scoring Backtest V2

Uses a fixed list of real tickers (mix of known winners and random stocks)
to validate the AI-powered lens scoring without database dependency.
"""
import os
import sys
import warnings
import json
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv

warnings.filterwarnings('ignore')
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
import yfinance as yf

# Gemini AI
import google.generativeai as genai

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Test stocks - mix of large caps that should have insider data
TEST_TICKERS = [
    # Large caps with active insider trading
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA',
    'JPM', 'V', 'JNJ', 'UNH', 'HD', 'PG', 'MA',
    # Some mid-caps
    'CRM', 'ABNB', 'SNOW', 'ZM', 'DDOG', 'NET', 'CRWD',
    # Some small-caps (less likely to have data)
    'BILL', 'HUBS', 'GTLB', 'MDB', 'CFLT'
]

def get_yahoo_insider_data(ticker: str) -> dict:
    """Fetch insider and institutional data from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        
        # Insider transactions
        insider_text = ""
        try:
            insider_df = stock.insider_transactions
            if insider_df is not None and not insider_df.empty:
                insider_text = insider_df.to_string()
        except:
            pass
        
        # Major holders
        holders_text = ""
        try:
            holders = stock.major_holders
            if holders is not None and not holders.empty:
                holders_text = holders.to_string()
        except:
            pass
        
        # Institutional holders
        inst_text = ""
        try:
            inst = stock.institutional_holders
            if inst is not None and not inst.empty:
                inst_text = inst.head(5).to_string()
        except:
            pass
        
        return {
            'insider_transactions': insider_text,
            'major_holders': holders_text,
            'institutional_holders': inst_text,
            'has_data': bool(insider_text or holders_text or inst_text)
        }
    except Exception as e:
        return {
            'insider_transactions': '',
            'major_holders': '',
            'institutional_holders': '',
            'has_data': False
        }

def parse_with_ai(ticker: str, yahoo_data: dict) -> dict:
    """Use Gemini to parse Yahoo data and extract structured scores."""
    
    if not yahoo_data['has_data']:
        return {
            'insider_sentiment': 0,
            'insider_buys': 0,
            'insider_sells': 0,
            'exec_buys': 0,
            'institutional_pct': 0,
            'parse_success': False,
            'error': 'No Yahoo data'
        }
    
    prompt = f"""Analyze this stock data for {ticker} and extract structured metrics.

INSIDER TRANSACTIONS:
{yahoo_data['insider_transactions'][:2000] if yahoo_data['insider_transactions'] else 'No data'}

MAJOR HOLDERS:
{yahoo_data['major_holders'][:500] if yahoo_data['major_holders'] else 'No data'}

INSTITUTIONAL HOLDERS:
{yahoo_data['institutional_holders'][:500] if yahoo_data['institutional_holders'] else 'No data'}

Return ONLY a JSON object (no markdown, no explanation):
{{
    "insider_sentiment": <-100 to +100>,
    "insider_buys": <count>,
    "insider_sells": <count>,
    "exec_buys": <count>,
    "institutional_pct": <0-100>
}}"""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean up
        if '```' in text:
            text = text.split('```')[1] if '```' in text else text
            text = text.replace('json', '').strip()
        
        data = json.loads(text)
        data['parse_success'] = True
        data['error'] = None
        return data
        
    except Exception as e:
        return {
            'insider_sentiment': 0,
            'insider_buys': 0,
            'insider_sells': 0,
            'exec_buys': 0,
            'institutional_pct': 0,
            'parse_success': False,
            'error': str(e)[:50]
        }

def get_stock_performance(ticker: str) -> dict:
    """Get 30-day performance for a stock."""
    try:
        df = yf.download(ticker, period='3mo', progress=False)
        if len(df) < 30:
            return {'return_30d': None}
        
        current = df['Close'].iloc[-1]
        past = df['Close'].iloc[-30]
        return_30d = ((current - past) / past) * 100
        
        return {'return_30d': float(return_30d)}
    except:
        return {'return_30d': None}

def run_backtest():
    """Main backtest function."""
    print("=" * 70)
    print("AI LENS SCORING BACKTEST V2")
    print("=" * 70)
    print(f"Testing {len(TEST_TICKERS)} stocks: {', '.join(TEST_TICKERS[:10])}...")
    print("-" * 70)
    
    results = []
    sentiments = []
    
    for i, ticker in enumerate(TEST_TICKERS):
        print(f"\n[{i+1}/{len(TEST_TICKERS)}] {ticker}", end=" ")
        
        # 1. Get Yahoo data
        yahoo_data = get_yahoo_insider_data(ticker)
        print(f"{'📊' if yahoo_data['has_data'] else '❌'}", end=" ")
        
        # 2. Parse with AI
        ai_result = parse_with_ai(ticker, yahoo_data)
        print(f"{'🤖' if ai_result['parse_success'] else '⚠️'}", end=" ")
        
        # 3. Get performance
        perf = get_stock_performance(ticker)
        
        if ai_result['parse_success']:
            sent = ai_result['insider_sentiment']
            sentiments.append(sent)
            print(f"Sentiment: {sent:+3d} | Return: {perf['return_30d']:+.1f}%" if perf['return_30d'] else f"Sentiment: {sent:+3d}")
        else:
            print(f"Parse failed: {ai_result.get('error', 'unknown')}")
        
        results.append({
            'ticker': ticker,
            'has_data': yahoo_data['has_data'],
            'parse_success': ai_result['parse_success'],
            'insider_sentiment': ai_result['insider_sentiment'],
            'insider_buys': ai_result['insider_buys'],
            'insider_sells': ai_result['insider_sells'],
            'exec_buys': ai_result['exec_buys'],
            'institutional_pct': ai_result.get('institutional_pct', 0),
            'return_30d': perf['return_30d']
        })
        
        # Rate limit
        time.sleep(2)
    
    # Analysis
    print("\n" + "=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)
    
    df = pd.DataFrame(results)
    
    # 1. Data Quality
    print("\n📊 DATA QUALITY:")
    print(f"  Stocks tested: {len(df)}")
    print(f"  Yahoo data available: {df['has_data'].sum()}/{len(df)} ({df['has_data'].mean()*100:.0f}%)")
    print(f"  AI parse successful: {df['parse_success'].sum()}/{len(df)} ({df['parse_success'].mean()*100:.0f}%)")
    
    # 2. Score Variation - THE KEY TEST
    print("\n📈 SCORE VARIATION (Key Validation):")
    if sentiments:
        unique = len(set(sentiments))
        print(f"  Unique sentiment values: {unique}")
        print(f"  Range: {min(sentiments)} to {max(sentiments)}")
        print(f"  Std Dev: {np.std(sentiments):.1f}")
        print(f"  All values: {sorted(sentiments)}")
        
        if unique <= 3:
            print("  ⚠️ WARNING: Low variation - may have bucketing issue")
        elif unique >= 5:
            print("  ✅ GOOD: High variation detected!")
    
    # 3. Predictive Power
    print("\n🎯 PREDICTIVE POWER:")
    valid = df[df['parse_success'] & df['return_30d'].notna()]
    
    if len(valid) >= 5:
        corr = valid['insider_sentiment'].corr(valid['return_30d'])
        print(f"  Sentiment-Return Correlation: {corr:+.3f}")
        
        # Show top/bottom by sentiment
        top = valid.nlargest(3, 'insider_sentiment')[['ticker', 'insider_sentiment', 'return_30d']]
        bot = valid.nsmallest(3, 'insider_sentiment')[['ticker', 'insider_sentiment', 'return_30d']]
        
        print("\n  Top 3 by sentiment:")
        for _, row in top.iterrows():
            print(f"    {row['ticker']}: sentiment={row['insider_sentiment']:+d}, return={row['return_30d']:+.1f}%")
        
        print("\n  Bottom 3 by sentiment:")
        for _, row in bot.iterrows():
            print(f"    {row['ticker']}: sentiment={row['insider_sentiment']:+d}, return={row['return_30d']:+.1f}%")
    
    # Save
    df.to_csv('ai_lens_backtest_v2.csv', index=False)
    print("\n📁 Results saved to ai_lens_backtest_v2.csv")

if __name__ == "__main__":
    run_backtest()
