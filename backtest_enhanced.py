"""
Enhanced Backtest Framework with FMP Insider & Institutional Data

Tests ALL signal types:
- Technical (from yfinance)
- Insider Trading (from FMP)
- Institutional Ownership (from FMP)
- Fundamentals (from FMP)
"""
import pandas as pd
import numpy as np
import yfinance as yf
import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
import warnings
import time
warnings.filterwarnings('ignore')

load_dotenv()

FMP_API_KEY = os.getenv('FMP_API_KEY')
FMP_BASE = "https://financialmodelingprep.com/api"

# ============================================================================
# FMP API FUNCTIONS
# ============================================================================

def fmp_get(endpoint: str, params: dict = None) -> dict:
    """Make FMP API request with rate limiting"""
    if params is None:
        params = {}
    params['apikey'] = FMP_API_KEY
    
    try:
        url = f"{FMP_BASE}{endpoint}"
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        pass
    return None


def get_insider_trading(ticker: str) -> dict:
    """Get insider trading activity for a ticker"""
    data = fmp_get(f"/v4/insider-trading", {"symbol": ticker, "limit": 50})
    
    if not data:
        return {'score': 0, 'net_buys_90d': 0, 'total_value': 0}
    
    # Analyze last 90 days of insider activity
    net_buys = 0
    net_value = 0
    ceo_bought = False
    
    cutoff = datetime.now() - timedelta(days=90)
    
    for trade in data:
        try:
            trade_date = datetime.strptime(trade.get('transactionDate', ''), '%Y-%m-%d')
            if trade_date < cutoff:
                continue
                
            trans_type = trade.get('transactionType', '').upper()
            shares = trade.get('securitiesTransacted', 0) or 0
            value = trade.get('price', 0) or 0
            value = shares * value
            
            # Check if executive bought
            title = (trade.get('typeOfOwner', '') or '').upper()
            
            if 'P-PURCHASE' in trans_type or 'BUY' in trans_type:
                net_buys += 1
                net_value += value
                if 'CEO' in title or 'CHIEF EXECUTIVE' in title:
                    ceo_bought = True
            elif 'S-SALE' in trans_type or 'SELL' in trans_type:
                net_buys -= 1
                net_value -= value
        except:
            continue
    
    # Calculate insider score (0-100)
    score = 50  # Neutral base
    if net_buys > 0:
        score += min(net_buys * 10, 30)  # +10 per net buy, max +30
    elif net_buys < 0:
        score += max(net_buys * 5, -30)  # -5 per net sell, max -30
    
    if ceo_bought:
        score += 20  # Big bonus for CEO buying
    
    score = max(0, min(100, score))
    
    return {
        'insider_score': score,
        'net_buys_90d': net_buys,
        'net_value': net_value,
        'ceo_bought': ceo_bought
    }


def get_institutional_ownership(ticker: str) -> dict:
    """Get institutional ownership data"""
    # Try institutional holders endpoint
    data = fmp_get(f"/v3/institutional-holder/{ticker}")
    
    if not data:
        return {'inst_score': 50, 'inst_count': 0, 'inst_change': 0}
    
    # Count recent institutional activity
    inst_count = len(data)
    
    # Calculate score based on number of institutional holders
    score = 50
    if inst_count > 100:
        score = 80
    elif inst_count > 50:
        score = 70
    elif inst_count > 20:
        score = 60
    elif inst_count < 5:
        score = 30
    
    return {
        'inst_score': score,
        'inst_count': inst_count,
        'inst_change': 0  # Would need historical data to calculate
    }


def get_fundamentals(ticker: str) -> dict:
    """Get fundamental ratios"""
    data = fmp_get(f"/v3/ratios-ttm/{ticker}")
    
    if not data or len(data) == 0:
        return {'fundamental_score': 50}
    
    ratios = data[0] if isinstance(data, list) else data
    
    # Extract key metrics
    roe = ratios.get('returnOnEquityTTM', 0) or 0
    pe = ratios.get('peRatioTTM', 0) or 0
    peg = ratios.get('pegRatioTTM', 0) or 0
    current_ratio = ratios.get('currentRatioTTM', 0) or 0
    debt_equity = ratios.get('debtEquityRatioTTM', 0) or 0
    
    # Calculate fundamental score
    score = 50
    
    # ROE scoring (higher = better)
    if roe > 0.20:
        score += 15
    elif roe > 0.10:
        score += 8
    elif roe < 0:
        score -= 15
    
    # PEG scoring (lower = better, but not negative)
    if 0 < peg < 1:
        score += 15
    elif 1 <= peg < 2:
        score += 8
    elif peg > 3:
        score -= 10
    
    # Debt/Equity (lower = better)
    if debt_equity < 0.5:
        score += 10
    elif debt_equity > 2:
        score -= 10
    
    score = max(0, min(100, score))
    
    return {
        'fundamental_score': score,
        'roe': roe,
        'peg': peg,
        'debt_equity': debt_equity
    }


# ============================================================================
# TECHNICAL SIGNAL FUNCTIONS (from original backtest)
# ============================================================================

def calc_rsi(prices: pd.Series, period: int = 14) -> float:
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    if loss.iloc[-1] == 0:
        return 100.0
    rs = gain.iloc[-1] / loss.iloc[-1]
    return float(100 - (100 / (1 + rs)))


def calc_momentum_1m(prices: pd.Series) -> float:
    if len(prices) < 21:
        return 0.0
    return float((prices.iloc[-1] / prices.iloc[-21] - 1) * 100)


def calc_volatility(prices: pd.Series, period: int = 20) -> float:
    returns = prices.pct_change().dropna()
    if len(returns) < period:
        return 0.0
    return float(returns.tail(period).std() * np.sqrt(252) * 100)


def calc_ema_trend_score(prices: pd.Series) -> float:
    if len(prices) < 50:
        return 50.0
    ema10 = prices.ewm(span=10).mean().iloc[-1]
    ema20 = prices.ewm(span=20).mean().iloc[-1]
    ema50 = prices.ewm(span=50).mean().iloc[-1]
    current = prices.iloc[-1]
    
    score = 50.0
    if current > ema10: score += 15
    if ema10 > ema20: score += 20
    if ema20 > ema50: score += 15
    if current < ema50: score -= 30
    
    return min(max(score, 0), 100)


def calc_distance_from_52w_high(high: pd.Series, current_price: float) -> float:
    high_52w = high.tail(252).max() if len(high) >= 252 else high.max()
    return float((current_price / high_52w) * 100) if high_52w > 0 else 0.0


# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def fetch_stock_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    try:
        df = yf.download(ticker, period=period, progress=False, threads=False)
        if df.empty or len(df) < 100:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None


def calculate_all_signals(df: pd.DataFrame, ticker: str, use_fmp: bool = True) -> dict:
    """Calculate all signals including FMP data"""
    signals = {}
    
    # Technical signals
    signals['rsi'] = calc_rsi(df['Close'])
    signals['momentum_1m'] = calc_momentum_1m(df['Close']) * 2 + 50  # Normalize to 0-100
    signals['momentum_1m'] = max(0, min(100, signals['momentum_1m']))
    signals['volatility'] = 100 - calc_volatility(df['Close'])  # Lower vol = higher score
    signals['ema_trend'] = calc_ema_trend_score(df['Close'])
    signals['distance_52w_high'] = calc_distance_from_52w_high(df['High'], df['Close'].iloc[-1])
    
    # FMP signals (with rate limiting)
    if use_fmp:
        time.sleep(0.25)  # Rate limit: 4 requests/sec
        
        # Insider trading
        insider = get_insider_trading(ticker)
        signals['insider_score'] = insider.get('insider_score', 50)
        signals['net_insider_buys'] = insider.get('net_buys_90d', 0)
        
        # Institutional ownership
        inst = get_institutional_ownership(ticker)
        signals['institutional_score'] = inst.get('inst_score', 50)
        
        # Fundamentals
        fund = get_fundamentals(ticker)
        signals['fundamental_score'] = fund.get('fundamental_score', 50)
    
    return signals


def run_enhanced_backtest(tickers: list, forward_days: int = 30, use_fmp: bool = True) -> pd.DataFrame:
    """Run backtest with FMP data"""
    results = []
    
    print(f"📊 Running ENHANCED backtest on {len(tickers)} tickers...")
    print(f"   Using FMP data: {use_fmp}")
    print(f"   Forward return window: {forward_days} days\n")
    
    for i, ticker in enumerate(tickers):
        print(f"   [{i+1}/{len(tickers)}] {ticker}...", end="")
        
        df = fetch_stock_data(ticker, period="1y")
        if df is None or len(df) < 100 + forward_days:
            print(" SKIP (insufficient data)")
            continue
        
        # Split data for backtest simulation
        signal_data = df.iloc[:-forward_days].copy()
        
        if len(signal_data) < 100:
            print(" SKIP")
            continue
        
        # Calculate signals
        signals = calculate_all_signals(signal_data, ticker, use_fmp=use_fmp)
        
        # Calculate forward return
        price_at_signal = signal_data['Close'].iloc[-1]
        price_after = df['Close'].iloc[-1]
        forward_return = ((price_after / price_at_signal) - 1) * 100
        
        result = {
            'ticker': ticker,
            'forward_return': forward_return,
            'is_winner': forward_return > 10,
            **signals
        }
        results.append(result)
        print(f" OK | Return: {forward_return:+.1f}%")
    
    return pd.DataFrame(results)


def analyze_signals(backtest_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze which signals correlate with returns"""
    signal_cols = [c for c in backtest_df.columns if c not in ['ticker', 'forward_return', 'is_winner']]
    
    # Define categories for each signal
    categories = {
        'rsi': 'CHARTIST',
        'momentum_1m': 'CHARTIST',
        'volatility': 'CHARTIST',
        'ema_trend': 'CHARTIST',
        'distance_52w_high': 'CHARTIST',
        'insider_score': 'HUNTER',
        'net_insider_buys': 'HUNTER',
        'institutional_score': 'QUANT',
        'fundamental_score': 'ORACLE'
    }
    
    analysis = []
    for signal in signal_cols:
        corr = backtest_df[signal].corr(backtest_df['forward_return'])
        
        winners = backtest_df[backtest_df['is_winner'] == True]
        losers = backtest_df[backtest_df['is_winner'] == False]
        
        winner_avg = winners[signal].mean() if len(winners) > 0 else 0
        loser_avg = losers[signal].mean() if len(losers) > 0 else 0
        diff = winner_avg - loser_avg
        
        category = categories.get(signal, 'OTHER')
        
        analysis.append({
            'signal': signal,
            'category': category,
            'correlation': corr,
            'winner_avg': winner_avg,
            'loser_avg': loser_avg,
            'diff': diff,
            'predictive': abs(corr) > 0.1 and diff > 3
        })
    
    return pd.DataFrame(analysis).sort_values('correlation', ascending=False)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Smaller test set due to API rate limits
    TEST_TICKERS = [
        # Large caps (diverse sectors)
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA",
        "NFLX", "CRM", "INTC", "CSCO", "PFE", "ABT",
        # Growth stocks
        "PLTR", "SOFI", "COIN", "SQ", "SHOP", "ROKU",
        "CRWD", "SNOW", "NET", "DDOG",
        # Recent movers
        "SMCI", "ARM", "CELH", "CAVA", "ABNB"
    ]
    
    print("="*70)
    print("🎯 ENHANCED SIGNAL BACKTEST (with FMP Insider & Institutional Data)")
    print("="*70)
    print(f"Testing {len(TEST_TICKERS)} stocks")
    print(f"FMP API Key: {'✅ Found' if FMP_API_KEY else '❌ Missing!'}")
    print("="*70 + "\n")
    
    if not FMP_API_KEY:
        print("ERROR: FMP_API_KEY not found in environment!")
        exit(1)
    
    # Run enhanced backtest
    results_df = run_enhanced_backtest(TEST_TICKERS, forward_days=30, use_fmp=True)
    
    print(f"\n✅ Backtest complete: {len(results_df)} stocks analyzed")
    winners = results_df[results_df['is_winner']]
    print(f"   Winners (>10%): {len(winners)} ({len(winners)/len(results_df)*100:.1f}%)")
    print(f"   Avg Forward Return: {results_df['forward_return'].mean():.1f}%")
    
    # Analyze signals
    print("\n" + "="*70)
    print("📊 SIGNAL CORRELATION ANALYSIS (Including FMP Data)")
    print("="*70)
    
    analysis_df = analyze_signals(results_df)
    
    print("\nSignals ranked by correlation with forward returns:\n")
    print(f"{'Signal':<22} | {'Category':<10} | {'Corr':>7} | {'Winner':>8} | {'Loser':>8} | {'Diff':>6}")
    print("-" * 75)
    
    for _, row in analysis_df.iterrows():
        print(f"{row['signal']:<22} | {row['category']:<10} | {row['correlation']:>+7.3f} | {row['winner_avg']:>8.1f} | {row['loser_avg']:>8.1f} | {row['diff']:>+6.1f}")
    
    # Key findings
    print("\n" + "="*70)
    print("🏆 KEY FINDINGS")
    print("="*70)
    
    # Best signals by category
    for category in ['HUNTER', 'QUANT', 'ORACLE', 'CHARTIST']:
        cat_signals = analysis_df[analysis_df['category'] == category]
        if len(cat_signals) > 0:
            best = cat_signals.iloc[0]
            print(f"\n{category}:")
            print(f"  Best signal: {best['signal']} (corr: {best['correlation']:+.3f})")
    
    # Save results
    results_df.to_csv('enhanced_backtest_results.csv', index=False)
    analysis_df.to_csv('enhanced_signal_analysis.csv', index=False)
    print("\n💾 Results saved to enhanced_backtest_results.csv and enhanced_signal_analysis.csv")
