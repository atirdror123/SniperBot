"""
Backtest Framework - Signal Validation Engine

Tests which quantitative signals best predict stock winners.
Uses historical data to calculate forward returns and correlations.
"""
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# SIGNAL CALCULATION FUNCTIONS (Continuous 0-100 scoring)
# ============================================================================

def calc_rsi(prices: pd.Series, period: int = 14) -> float:
    """RSI - returns 0-100"""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    
    if loss.iloc[-1] == 0:
        return 100.0
    
    rs = gain.iloc[-1] / loss.iloc[-1]
    return float(100 - (100 / (1 + rs)))


def calc_rvol(volume: pd.Series, lookback: int = 20) -> float:
    """Relative Volume - current vs 20-day average"""
    avg_vol = volume.tail(lookback + 1).iloc[:-1].mean()
    current_vol = volume.iloc[-1]
    return float(current_vol / avg_vol) if avg_vol > 0 else 1.0


def calc_momentum_1m(prices: pd.Series) -> float:
    """1-Month momentum (%)"""
    if len(prices) < 21:
        return 0.0
    return float((prices.iloc[-1] / prices.iloc[-21] - 1) * 100)


def calc_momentum_3m(prices: pd.Series) -> float:
    """3-Month momentum (%)"""
    if len(prices) < 63:
        return 0.0
    return float((prices.iloc[-1] / prices.iloc[-63] - 1) * 100)


def calc_volatility(prices: pd.Series, period: int = 20) -> float:
    """20-day volatility (annualized %)"""
    returns = prices.pct_change().dropna()
    if len(returns) < period:
        return 0.0
    return float(returns.tail(period).std() * np.sqrt(252) * 100)


def calc_distance_from_52w_high(high: pd.Series, current_price: float) -> float:
    """Distance from 52-week high (0-100, where 100 = at high)"""
    high_52w = high.tail(252).max() if len(high) >= 252 else high.max()
    return float((current_price / high_52w) * 100) if high_52w > 0 else 0.0


def calc_ema_trend_score(prices: pd.Series) -> float:
    """EMA alignment score (0-100)"""
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


def calc_macd_signal(prices: pd.Series) -> float:
    """MACD momentum score (0-100)"""
    if len(prices) < 26:
        return 50.0
    
    ema12 = prices.ewm(span=12).mean()
    ema26 = prices.ewm(span=26).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9).mean()
    
    macd_val = macd.iloc[-1]
    signal_val = signal.iloc[-1]
    hist = macd_val - signal_val
    
    # Convert to 0-100 score
    if hist > 0:
        return min(50 + (hist / prices.iloc[-1] * 1000), 100)
    else:
        return max(50 + (hist / prices.iloc[-1] * 1000), 0)


def calc_volume_trend(volume: pd.Series, period: int = 10) -> float:
    """Volume trend score (0-100) - is volume increasing?"""
    if len(volume) < period * 2:
        return 50.0
    
    recent_avg = volume.tail(period).mean()
    older_avg = volume.tail(period * 2).head(period).mean()
    
    ratio = recent_avg / older_avg if older_avg > 0 else 1.0
    
    # Convert to 0-100 (1.5x = 100, 0.5x = 0)
    return min(max((ratio - 0.5) * 100, 0), 100)


def calc_price_acceleration(prices: pd.Series) -> float:
    """Price acceleration (2nd derivative) score (0-100)"""
    if len(prices) < 30:
        return 50.0
    
    # Calculate daily returns
    returns = prices.pct_change().dropna()
    
    # Recent 10-day avg return vs prior 10-day avg
    recent_ret = returns.tail(10).mean()
    prior_ret = returns.tail(20).head(10).mean()
    
    acceleration = (recent_ret - prior_ret) * 100
    
    # Convert to 0-100
    return min(max(50 + acceleration * 50, 0), 100)


# ============================================================================
# SIGNAL GROUPS (By Category)
# ============================================================================

SIGNAL_DEFINITIONS = {
    # CHARTIST (Technical)
    'rsi': {'func': lambda d: calc_rsi(d['Close']), 'category': 'CHARTIST', 'ideal_range': (50, 70)},
    'rvol': {'func': lambda d: min(calc_rvol(d['Volume']) * 25, 100), 'category': 'CHARTIST', 'ideal_range': (50, 100)},
    'momentum_1m': {'func': lambda d: min(max(calc_momentum_1m(d['Close']) * 2 + 50, 0), 100), 'category': 'CHARTIST', 'ideal_range': (50, 100)},
    'momentum_3m': {'func': lambda d: min(max(calc_momentum_3m(d['Close']) + 50, 0), 100), 'category': 'CHARTIST', 'ideal_range': (50, 100)},
    'ema_trend': {'func': lambda d: calc_ema_trend_score(d['Close']), 'category': 'CHARTIST', 'ideal_range': (70, 100)},
    'macd_signal': {'func': lambda d: calc_macd_signal(d['Close']), 'category': 'CHARTIST', 'ideal_range': (50, 100)},
    'distance_52w_high': {'func': lambda d: calc_distance_from_52w_high(d['High'], d['Close'].iloc[-1]), 'category': 'CHARTIST', 'ideal_range': (85, 100)},
    
    # QUANT (Volume/Flow)
    'volume_trend': {'func': lambda d: calc_volume_trend(d['Volume']), 'category': 'QUANT', 'ideal_range': (50, 100)},
    'price_acceleration': {'func': lambda d: calc_price_acceleration(d['Close']), 'category': 'QUANT', 'ideal_range': (50, 100)},
    
    # ORACLE (Fundamental proxies from price action)
    'volatility': {'func': lambda d: 100 - calc_volatility(d['Close']), 'category': 'ORACLE', 'ideal_range': (50, 100)},  # Lower vol = higher score
}


def calculate_all_signals(df: pd.DataFrame) -> dict:
    """Calculate all signals for a stock's data"""
    signals = {}
    for name, config in SIGNAL_DEFINITIONS.items():
        try:
            signals[name] = config['func'](df)
        except:
            signals[name] = 50.0  # Default neutral
    return signals


def calculate_forward_returns(df: pd.DataFrame, days: int) -> float:
    """Calculate forward return from end of DataFrame"""
    if len(df) <= days:
        return None
    # We need to simulate "what happened next" - in backtest we know future
    try:
        price_now = df['Close'].iloc[-(days + 1)]  # Starting price
        price_future = df['Close'].iloc[-1]  # Future price
        return float((price_future / price_now - 1) * 100)
    except:
        return None


# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def fetch_stock_data(ticker: str, period: str = "1y") -> pd.DataFrame:
    """Fetch historical data for a ticker"""
    try:
        df = yf.download(ticker, period=period, progress=False, threads=False)
        if df.empty or len(df) < 100:
            return None
        # Flatten multi-index if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        return df
    except:
        return None


def run_backtest(tickers: list, lookback_days: int = 60, forward_days: int = 30) -> pd.DataFrame:
    """
    Run backtest on a list of tickers.
    
    For each ticker:
    1. Get historical data
    2. Calculate signals at T-forward_days (simulating "past")
    3. Calculate forward returns (what happened next)
    4. Store for correlation analysis
    """
    results = []
    
    print(f"📊 Running backtest on {len(tickers)} tickers...")
    print(f"   Looking {forward_days} days forward for returns\n")
    
    for i, ticker in enumerate(tickers):
        if i % 10 == 0:
            print(f"   Processing {i}/{len(tickers)}...")
        
        df = fetch_stock_data(ticker, period="1y")
        if df is None or len(df) < lookback_days + forward_days:
            continue
        
        # Split data: use data UP TO forward_days ago to calculate signals
        # Then measure what happened in those forward_days
        signal_data = df.iloc[:-forward_days].copy()  # Data for signal calculation
        
        if len(signal_data) < lookback_days:
            continue
        
        # Calculate signals on historical data
        signals = calculate_all_signals(signal_data)
        
        # Calculate what actually happened (forward return)
        price_at_signal = signal_data['Close'].iloc[-1]
        price_after = df['Close'].iloc[-1]
        forward_return = ((price_after / price_at_signal) - 1) * 100
        
        # Store result
        result = {
            'ticker': ticker,
            'forward_return': forward_return,
            'is_winner': forward_return > 10,  # >10% = winner
            **signals
        }
        results.append(result)
    
    return pd.DataFrame(results)


def analyze_signals(backtest_df: pd.DataFrame) -> pd.DataFrame:
    """Analyze which signals correlate with forward returns"""
    
    signal_cols = [c for c in backtest_df.columns if c not in ['ticker', 'forward_return', 'is_winner']]
    
    analysis = []
    for signal in signal_cols:
        # Correlation with forward return
        corr = backtest_df[signal].corr(backtest_df['forward_return'])
        
        # Mean signal value for winners vs losers
        winners = backtest_df[backtest_df['is_winner'] == True][signal].mean()
        losers = backtest_df[backtest_df['is_winner'] == False][signal].mean()
        
        # T-test significance (simplified)
        diff = winners - losers
        
        category = SIGNAL_DEFINITIONS.get(signal, {}).get('category', 'OTHER')
        
        analysis.append({
            'signal': signal,
            'category': category,
            'correlation': corr,
            'winner_avg': winners,
            'loser_avg': losers,
            'diff': diff,
            'predictive': abs(corr) > 0.1 and diff > 3
        })
    
    return pd.DataFrame(analysis).sort_values('correlation', ascending=False)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    # Test universe: S&P 500 sample + some small caps
    TEST_TICKERS = [
        # Large caps
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
        "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA", "DIS", "PYPL", "ADBE",
        "NFLX", "CRM", "INTC", "CSCO", "PFE", "ABT", "COST", "TMO", "AVGO",
        "NKE", "MRK", "PEP", "KO", "WMT", "CVX", "XOM", "LLY", "ABBV",
        # Mid/Small caps with more volatility
        "PLTR", "SOFI", "UPST", "AFRM", "HOOD", "RIVN", "LCID", "NIO",
        "DKNG", "COIN", "MARA", "RIOT", "SQ", "SHOP", "ROKU", "ZM",
        "CRWD", "SNOW", "NET", "DDOG", "MDB", "TTD", "BILL", "HUBS",
        # Recent movers
        "SMCI", "ARM", "CELH", "DUOL", "CAVA", "TOST", "DASH", "ABNB"
    ]
    
    print("="*60)
    print("🎯 SIGNAL BACKTEST ENGINE")
    print("="*60)
    print(f"Testing {len(TEST_TICKERS)} stocks")
    print(f"Forward return window: 30 days")
    print("="*60 + "\n")
    
    # Run backtest
    results_df = run_backtest(TEST_TICKERS, forward_days=30)
    
    print(f"\n✅ Backtest complete: {len(results_df)} stocks analyzed")
    print(f"   Winners (>10%): {len(results_df[results_df['is_winner']])} ({len(results_df[results_df['is_winner']])/len(results_df)*100:.1f}%)")
    print(f"   Avg Forward Return: {results_df['forward_return'].mean():.1f}%")
    
    # Analyze signals
    print("\n" + "="*60)
    print("📊 SIGNAL CORRELATION ANALYSIS")
    print("="*60)
    
    analysis_df = analyze_signals(results_df)
    
    print("\nSignals ranked by correlation with forward returns:\n")
    print(f"{'Signal':<22} | {'Category':<10} | {'Corr':>7} | {'Winner':>7} | {'Loser':>7} | {'Diff':>6} | {'Predictive':>10}")
    print("-" * 90)
    
    for _, row in analysis_df.iterrows():
        predictive = "✅ YES" if row['predictive'] else "❌ No"
        print(f"{row['signal']:<22} | {row['category']:<10} | {row['correlation']:>+7.3f} | {row['winner_avg']:>7.1f} | {row['loser_avg']:>7.1f} | {row['diff']:>+6.1f} | {predictive:>10}")
    
    # Summary
    print("\n" + "="*60)
    print("🏆 TOP PREDICTIVE SIGNALS")
    print("="*60)
    
    top_signals = analysis_df[analysis_df['predictive'] == True]
    if len(top_signals) > 0:
        print("\nSignals that differentiate winners from losers:")
        for _, row in top_signals.iterrows():
            print(f"  • {row['signal']} ({row['category']}): Corr={row['correlation']:+.3f}, Diff={row['diff']:+.1f}")
    else:
        print("\n⚠️ No signals showed strong predictive power in this test.")
        print("   This suggests we need additional data sources (insider, options flow)")
    
    # Save results
    results_df.to_csv('backtest_results.csv', index=False)
    analysis_df.to_csv('signal_analysis.csv', index=False)
    print("\n💾 Results saved to backtest_results.csv and signal_analysis.csv")
