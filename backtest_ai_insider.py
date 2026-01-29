"""
Backtest: AI-Powered Insider Sentiment Parsing

Uses Gemini AI to parse Yahoo's text-based insider data
and measures if it predicts stock performance.
"""
import pandas as pd
import numpy as np
import yfinance as yf
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
import time
import warnings
warnings.filterwarnings('ignore')

load_dotenv()

# Setup Gemini
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

# ============================================================================
# AI INSIDER PARSING
# ============================================================================

def get_yahoo_insider_data(ticker: str) -> str:
    """Get raw insider transaction data from Yahoo"""
    try:
        stock = yf.Ticker(ticker)
        transactions = stock.insider_transactions
        if transactions is None or len(transactions) == 0:
            return None
        return transactions.head(15).to_string()
    except:
        return None

def ai_parse_insider(raw_data: str, ticker: str) -> dict:
    """Use Gemini to parse insider sentiment"""
    prompt = f"""Analyze this insider trading data for {ticker}.
Return ONLY a JSON object with these exact keys:
- sentiment: integer from -100 to 100 (-100=heavy selling, 0=neutral, 100=heavy buying)
- buys: number of buy transactions
- sells: number of sell transactions  
- executive_buys: true if CEO/CFO/executives bought, false otherwise

Data:
{raw_data}

Return ONLY valid JSON, no markdown or explanation."""

    try:
        time.sleep(1.5)  # Rate limiting
        response = model.generate_content(prompt)
        txt = response.text.strip()
        
        # Clean markdown if present
        if '```' in txt:
            txt = txt.split('```')[1]
            if txt.startswith('json'):
                txt = txt[4:]
            txt = txt.strip()
        
        result = json.loads(txt)
        return {
            'ai_sentiment': result.get('sentiment', 0),
            'ai_buys': result.get('buys', 0),
            'ai_sells': result.get('sells', 0),
            'ai_exec_buys': result.get('executive_buys', False)
        }
    except Exception as e:
        return {'ai_sentiment': 0, 'ai_buys': 0, 'ai_sells': 0, 'ai_exec_buys': False, 'error': str(e)}

# ============================================================================
# TECHNICAL SIGNALS
# ============================================================================

def calc_momentum_1m(prices: pd.Series) -> float:
    if len(prices) < 21:
        return 50.0
    mom = float((prices.iloc[-1] / prices.iloc[-21] - 1) * 100)
    return min(max(mom * 2 + 50, 0), 100)

def calc_rsi(prices: pd.Series, period: int = 14) -> float:
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    if loss.iloc[-1] == 0:
        return 100.0
    rs = gain.iloc[-1] / loss.iloc[-1]
    return float(100 - (100 / (1 + rs)))

# ============================================================================
# BACKTEST
# ============================================================================

def run_ai_backtest(tickers: list, forward_days: int = 30) -> pd.DataFrame:
    """Run backtest with AI-parsed insider data"""
    results = []
    
    print(f"Running AI Insider Backtest on {len(tickers)} stocks...")
    print(f"Forward window: {forward_days} days")
    print("-" * 50)
    
    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] {ticker}...", end=" ", flush=True)
        
        try:
            # Get price data
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y")
            
            if df is None or len(df) < 100 + forward_days:
                print("SKIP (data)")
                continue
            
            # Get insider data and AI parse
            raw_insider = get_yahoo_insider_data(ticker)
            if raw_insider:
                ai_result = ai_parse_insider(raw_insider, ticker)
            else:
                ai_result = {'ai_sentiment': 0, 'ai_buys': 0, 'ai_sells': 0, 'ai_exec_buys': False}
            
            # Split for backtest
            signal_data = df.iloc[:-forward_days].copy()
            
            # Technical signals
            momentum = calc_momentum_1m(signal_data['Close'])
            rsi = calc_rsi(signal_data['Close'])
            
            # Forward return
            price_at_signal = signal_data['Close'].iloc[-1]
            price_after = df['Close'].iloc[-1]
            forward_return = ((price_after / price_at_signal) - 1) * 100
            
            result = {
                'ticker': ticker,
                'forward_return': forward_return,
                'is_winner': forward_return > 10,
                # AI Signals
                'ai_sentiment': ai_result.get('ai_sentiment', 0),
                'ai_buys': ai_result.get('ai_buys', 0),
                'ai_sells': ai_result.get('ai_sells', 0),
                'ai_exec_buys': 100 if ai_result.get('ai_exec_buys') else 0,
                # Technical
                'momentum_1m': momentum,
                'rsi': rsi,
            }
            results.append(result)
            
            sentiment = ai_result.get('ai_sentiment', 0)
            print(f"AI:{sentiment:+d} | Return:{forward_return:+.1f}%")
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    return pd.DataFrame(results)

def analyze_results(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze correlations"""
    signal_cols = ['ai_sentiment', 'ai_buys', 'ai_sells', 'ai_exec_buys', 'momentum_1m', 'rsi']
    
    analysis = []
    for signal in signal_cols:
        if signal not in df.columns:
            continue
        corr = df[signal].corr(df['forward_return'])
        
        winners = df[df['is_winner']]
        losers = df[~df['is_winner']]
        
        w_avg = winners[signal].mean() if len(winners) > 0 else 0
        l_avg = losers[signal].mean() if len(losers) > 0 else 0
        
        category = 'AI_HUNTER' if signal.startswith('ai_') else 'CHARTIST'
        
        analysis.append({
            'signal': signal,
            'category': category,
            'correlation': corr,
            'winner_avg': w_avg,
            'loser_avg': l_avg,
            'diff': w_avg - l_avg
        })
    
    return pd.DataFrame(analysis).sort_values('correlation', ascending=False)

# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    # Smaller set due to API rate limits
    TEST_TICKERS = [
        "AAPL", "MSFT", "GOOGL", "NVDA", "META", "TSLA",
        "JPM", "V", "HD", "MA", "NFLX", "CRM",
        "PLTR", "COIN", "SHOP", "CRWD", "NET",
        "SMCI", "ARM", "CELH", "CAVA", "ABNB"
    ]
    
    print("="*60)
    print("AI-POWERED INSIDER SENTIMENT BACKTEST")
    print("Using Gemini to parse Yahoo insider data")
    print("="*60)
    
    # Run backtest
    results = run_ai_backtest(TEST_TICKERS, forward_days=30)
    
    if len(results) == 0:
        print("No results - check API rate limits")
        exit(1)
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    winners = results[results['is_winner']]
    print(f"Total stocks: {len(results)}")
    print(f"Winners (>10%): {len(winners)} ({len(winners)/len(results)*100:.1f}%)")
    print(f"Avg Return: {results['forward_return'].mean():.1f}%")
    
    # Analysis
    print("\n" + "="*60)
    print("SIGNAL ANALYSIS")
    print("="*60)
    
    analysis = analyze_results(results)
    
    print(f"\n{'Signal':<15} | {'Category':<10} | {'Corr':>7} | {'Winner':>7} | {'Loser':>7} | {'Diff':>6}")
    print("-" * 65)
    
    for _, row in analysis.iterrows():
        corr = row['correlation']
        corr_str = f"{corr:+7.3f}" if pd.notna(corr) else "    N/A"
        print(f"{row['signal']:<15} | {row['category']:<10} | {corr_str} | {row['winner_avg']:>7.1f} | {row['loser_avg']:>7.1f} | {row['diff']:>+6.1f}")
    
    # Save
    results.to_csv('ai_backtest_results.csv', index=False)
    analysis.to_csv('ai_signal_analysis.csv', index=False)
    print("\nSaved to ai_backtest_results.csv and ai_signal_analysis.csv")
    
    # Key finding
    print("\n" + "="*60)
    print("KEY FINDING")
    print("="*60)
    ai_sentiment_corr = analysis[analysis['signal'] == 'ai_sentiment']['correlation'].values
    if len(ai_sentiment_corr) > 0 and pd.notna(ai_sentiment_corr[0]):
        corr = ai_sentiment_corr[0]
        if corr > 0.1:
            print(f"AI Sentiment correlation: {corr:+.3f} - PREDICTIVE!")
        elif corr > 0:
            print(f"AI Sentiment correlation: {corr:+.3f} - Weak positive signal")
        else:
            print(f"AI Sentiment correlation: {corr:+.3f} - Not predictive")
    else:
        print("Could not calculate AI sentiment correlation")
