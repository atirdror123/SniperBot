"""
AI Lens Scoring Backtest

Validates that the AI-powered lens scoring system:
1. Produces VARIED scores (not bucketed like the old system)
2. Actually correlates with stock performance
3. Has no data holes (missing data causes score = 0)

Uses historical winners and losers from the database.
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
from supabase import create_client

# Gemini AI
import google.generativeai as genai

# Setup
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

def fetch_historical_stocks(limit=50):
    """Fetch stocks from database with known outcomes."""
    print("Fetching historical stocks from database...")
    
    try:
        # Get stocks with exit data (known outcomes)
        response = supabase.table('paper_positions').select('*').not_.is_('exit_date', 'null').limit(limit).execute()
        
        if response.data:
            print(f"Found {len(response.data)} stocks with exit data")
            return response.data
        else:
            print("No stocks with exit data found. Trying all stocks...")
            response = supabase.table('paper_positions').select('*').limit(limit).execute()
            return response.data or []
    except Exception as e:
        print(f"Database error: {e}")
        return []

def get_yahoo_insider_data(ticker: str) -> dict:
    """Fetch insider and institutional data from Yahoo Finance."""
    try:
        stock = yf.Ticker(ticker)
        
        # Insider transactions (text-based)
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
            'institutional_ownership': 0,
            'parse_success': False,
            'error': 'No Yahoo data available'
        }
    
    prompt = f"""Analyze this stock data for {ticker} and extract structured metrics.

INSIDER TRANSACTIONS:
{yahoo_data['insider_transactions'][:2000] if yahoo_data['insider_transactions'] else 'No data'}

MAJOR HOLDERS:
{yahoo_data['major_holders'][:500] if yahoo_data['major_holders'] else 'No data'}

INSTITUTIONAL HOLDERS:
{yahoo_data['institutional_holders'][:500] if yahoo_data['institutional_holders'] else 'No data'}

Return ONLY a JSON object with these fields:
{{
    "insider_sentiment": <-100 to +100, negative=selling, positive=buying>,
    "insider_buys": <count of buy transactions, 0 if unknown>,
    "insider_sells": <count of sell transactions, 0 if unknown>,
    "exec_buys": <count of C-level executive purchases, 0 if unknown>,
    "institutional_ownership": <percentage 0-100, 0 if unknown>,
    "confidence": <0-100, how confident you are in this analysis>
}}

If data is ambiguous or unclear, use 0. Return ONLY valid JSON, no explanation."""

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()
        
        # Clean up response
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
        if text.endswith('```'):
            text = text.rsplit('```', 1)[0]
        text = text.replace('```json', '').replace('```', '').strip()
        
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
            'institutional_ownership': 0,
            'parse_success': False,
            'error': str(e)
        }

def calculate_forward_return(ticker: str, entry_date: str) -> float:
    """Calculate 30-day forward return from entry date."""
    try:
        entry = datetime.strptime(entry_date[:10], '%Y-%m-%d')
        end = entry + timedelta(days=45)
        
        df = yf.download(ticker, start=entry.strftime('%Y-%m-%d'), 
                         end=end.strftime('%Y-%m-%d'), progress=False)
        
        if len(df) < 20:
            return None
        
        entry_price = df['Close'].iloc[0]
        exit_price = df['Close'].iloc[min(30, len(df)-1)]
        
        return ((exit_price - entry_price) / entry_price) * 100
    except:
        return None

def run_backtest():
    """Main backtest function."""
    print("=" * 70)
    print("AI LENS SCORING BACKTEST")
    print("Validating data quality and predictive power")
    print("=" * 70)
    
    # Fetch historical stocks
    stocks = fetch_historical_stocks(limit=30)
    
    if not stocks:
        print("ERROR: No stocks to backtest. Exiting.")
        return
    
    results = []
    ai_scores = []
    
    print(f"\nProcessing {len(stocks)} stocks...")
    print("-" * 70)
    
    for i, stock in enumerate(stocks):
        ticker = stock.get('ticker', stock.get('symbol', 'UNKNOWN'))
        entry_date = stock.get('entry_date', stock.get('created_at', ''))
        
        print(f"\n[{i+1}/{len(stocks)}] {ticker}")
        
        # 1. Get Yahoo data
        yahoo_data = get_yahoo_insider_data(ticker)
        print(f"  Yahoo Data: {'✓ Found' if yahoo_data['has_data'] else '✗ Missing'}")
        
        # 2. Parse with AI
        ai_result = parse_with_ai(ticker, yahoo_data)
        print(f"  AI Parse: {'✓ Success' if ai_result['parse_success'] else '✗ Failed'}")
        
        if ai_result['parse_success']:
            print(f"  Sentiment: {ai_result['insider_sentiment']:+d} | "
                  f"Buys: {ai_result['insider_buys']} | Sells: {ai_result['insider_sells']}")
            ai_scores.append(ai_result['insider_sentiment'])
        
        # 3. Get actual outcome
        exit_pnl = stock.get('pnl_percent') or stock.get('exit_pnl')
        if exit_pnl is None:
            forward_return = calculate_forward_return(ticker, entry_date)
        else:
            forward_return = float(exit_pnl)
        
        print(f"  Return: {forward_return:+.1f}%" if forward_return else "  Return: N/A")
        
        # Store result
        results.append({
            'ticker': ticker,
            'entry_date': entry_date,
            'has_yahoo_data': yahoo_data['has_data'],
            'ai_parse_success': ai_result['parse_success'],
            'insider_sentiment': ai_result['insider_sentiment'],
            'insider_buys': ai_result['insider_buys'],
            'insider_sells': ai_result['insider_sells'],
            'exec_buys': ai_result['exec_buys'],
            'institutional_ownership': ai_result.get('institutional_ownership', 0),
            'forward_return': forward_return,
            'is_winner': forward_return > 10 if forward_return else None
        })
        
        # Rate limit for Gemini
        time.sleep(2)
    
    # Analysis
    print("\n" + "=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)
    
    df = pd.DataFrame(results)
    
    # 1. Data Quality Check
    print("\n📊 DATA QUALITY:")
    print("-" * 40)
    print(f"Total stocks tested: {len(df)}")
    print(f"Yahoo data available: {df['has_yahoo_data'].sum()} ({df['has_yahoo_data'].mean()*100:.0f}%)")
    print(f"AI parse successful: {df['ai_parse_success'].sum()} ({df['ai_parse_success'].mean()*100:.0f}%)")
    
    # 2. Score Variation Check (key validation!)
    print("\n📈 SCORE VARIATION CHECK:")
    print("-" * 40)
    
    if ai_scores:
        unique_scores = len(set(ai_scores))
        print(f"Unique sentiment scores: {unique_scores}")
        print(f"Score range: {min(ai_scores)} to {max(ai_scores)}")
        print(f"Score std dev: {np.std(ai_scores):.1f}")
        
        # Check for bucketing problem
        if unique_scores <= 3:
            print("⚠️ WARNING: Low score variation - possible bucketing issue!")
        elif unique_scores >= 5:
            print("✅ GOOD: High score variation - continuous scoring working!")
    else:
        print("⚠️ No AI scores generated")
    
    # 3. Predictive Power Check
    print("\n🎯 PREDICTIVE POWER:")
    print("-" * 40)
    
    valid_df = df[df['forward_return'].notna() & df['ai_parse_success']]
    
    if len(valid_df) >= 5:
        correlation = valid_df['insider_sentiment'].corr(valid_df['forward_return'])
        print(f"Insider Sentiment vs Return correlation: {correlation:+.3f}")
        
        if abs(correlation) > 0.2:
            print("✅ Meaningful predictive signal detected!")
        elif abs(correlation) > 0.1:
            print("⚡ Weak but present signal")
        else:
            print("⚠️ No clear predictive power")
        
        # Compare winners vs losers
        winners = valid_df[valid_df['forward_return'] > 10]
        losers = valid_df[valid_df['forward_return'] < -5]
        
        if len(winners) > 0 and len(losers) > 0:
            print(f"\nWinner avg sentiment: {winners['insider_sentiment'].mean():+.1f}")
            print(f"Loser avg sentiment: {losers['insider_sentiment'].mean():+.1f}")
    else:
        print("Not enough valid data points for correlation analysis")
    
    # Save results
    df.to_csv('ai_lens_backtest_results.csv', index=False)
    
    # Summary report
    summary = f"""
AI LENS SCORING BACKTEST SUMMARY
================================
Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}

DATA QUALITY:
- Stocks tested: {len(df)}
- Yahoo data rate: {df['has_yahoo_data'].mean()*100:.0f}%
- AI parse rate: {df['ai_parse_success'].mean()*100:.0f}%

SCORE VARIATION:
- Unique scores: {len(set(ai_scores)) if ai_scores else 0}
- Score range: {min(ai_scores) if ai_scores else 'N/A'} to {max(ai_scores) if ai_scores else 'N/A'}
- Score std dev: {np.std(ai_scores):.1f if ai_scores else 'N/A'}

PREDICTIVE POWER:
- Correlation: {correlation:+.3f if len(valid_df) >= 5 else 'N/A'}

CONCLUSION:
"""
    
    # Determine conclusion
    if ai_scores and len(set(ai_scores)) >= 5:
        summary += "✅ AI lens scoring produces varied, non-bucketed scores.\n"
    else:
        summary += "⚠️ Score variation needs improvement.\n"
    
    if len(valid_df) >= 5 and abs(correlation) > 0.1:
        summary += "✅ Insider sentiment shows predictive signal.\n"
    else:
        summary += "⚠️ Limited predictive power detected.\n"
    
    with open('ai_lens_backtest_summary.txt', 'w') as f:
        f.write(summary)
    
    print(summary)
    print("\n📁 Results saved to:")
    print("  - ai_lens_backtest_results.csv")
    print("  - ai_lens_backtest_summary.txt")

if __name__ == "__main__":
    run_backtest()
