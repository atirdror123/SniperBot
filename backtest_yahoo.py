"""
Enhanced Backtest with Yahoo Finance FREE Insider & Institutional Data

Tests:
- Technical signals (momentum, RSI, etc.)
- Insider activity (from yfinance - FREE)
- Institutional ownership (from yfinance - FREE)
"""
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# YAHOO FINANCE DATA FUNCTIONS (FREE!)
# ============================================================================

def get_insider_score_yahoo(ticker: str) -> dict:
    """Calculate insider score from Yahoo Finance data (FREE)"""
    try:
        stock = yf.Ticker(ticker)
        transactions = stock.insider_transactions
        
        if transactions is None or len(transactions) == 0:
            return {'insider_score': 50, 'net_buys': 0, 'total_trans': 0}
        
        # Count buys vs sells from transaction text
        buys = 0
        sells = 0
        
        for _, row in transactions.iterrows():
            text = str(row.get('Text', '')).lower()
            shares = row.get('Shares', 0) or 0
            
            if 'buy' in text or 'purchase' in text or 'acquisition' in text:
                buys += 1
            elif 'sell' in text or 'sale' in text or 'disposition' in text:
                sells += 1
        
        net_buys = buys - sells
        total = buys + sells
        
        # Calculate score (0-100)
        score = 50
        if total > 0:
            buy_ratio = buys / total
            score = int(buy_ratio * 100)
        
        # Bonus for net positive insider buying
        if net_buys > 3:
            score = min(score + 20, 100)
        elif net_buys < -3:
            score = max(score - 20, 0)
        
        return {
            'insider_score': score,
            'net_buys': net_buys,
            'total_trans': total,
            'buy_ratio': buys/total if total > 0 else 0.5
        }
    except Exception as e:
        return {'insider_score': 50, 'net_buys': 0, 'total_trans': 0}


def get_institutional_score_yahoo(ticker: str) -> dict:
    """Calculate institutional score from Yahoo Finance (FREE)"""
    try:
        stock = yf.Ticker(ticker)
        major = stock.major_holders
        
        if major is None or len(major) == 0:
            return {'inst_score': 50, 'inst_pct': 0}
        
        # Extract institutional ownership %
        inst_pct = 0
        insider_pct = 0
        
        for idx, row in major.iterrows():
            val_str = str(row.iloc[0]).replace('%', '')
            try:
                val = float(val_str)
            except:
                continue
                
            desc = str(row.iloc[1]).lower() if len(row) > 1 else str(idx).lower()
            
            if 'institution' in desc:
                inst_pct = val
            elif 'insider' in desc:
                insider_pct = val
        
        # Score: Higher institutional = higher score (smart money)
        score = 50
        if inst_pct > 80:
            score = 85
        elif inst_pct > 60:
            score = 75
        elif inst_pct > 40:
            score = 65
        elif inst_pct < 20:
            score = 35
        
        # Bonus if insiders own significant stake
        if insider_pct > 10:
            score = min(score + 10, 100)
        
        return {
            'inst_score': score,
            'inst_pct': inst_pct,
            'insider_pct': insider_pct
        }
    except Exception as e:
        return {'inst_score': 50, 'inst_pct': 0}


# ============================================================================
# TECHNICAL SIGNALS
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
        return 50.0
    mom = float((prices.iloc[-1] / prices.iloc[-21] - 1) * 100)
    # Normalize to 0-100
    return min(max(mom * 2 + 50, 0), 100)


def calc_volatility_score(prices: pd.Series, period: int = 20) -> float:
    returns = prices.pct_change().dropna()
    if len(returns) < period:
        return 50.0
    vol = float(returns.tail(period).std() * np.sqrt(252) * 100)
    # Lower vol = higher score (stability)
    return min(max(100 - vol, 0), 100)


# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def run_yahoo_backtest(tickers: list, forward_days: int = 30) -> pd.DataFrame:
    """Run backtest with Yahoo Finance data"""
    results = []
    
    print(f"Running backtest on {len(tickers)} tickers...")
    print(f"Forward window: {forward_days} days")
    print("-" * 50)
    
    for i, ticker in enumerate(tickers):
        print(f"[{i+1}/{len(tickers)}] {ticker}...", end=" ")
        
        try:
            # Get price data
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y")
            
            if df is None or len(df) < 100 + forward_days:
                print("SKIP (insufficient data)")
                continue
            
            # Split for backtest
            signal_data = df.iloc[:-forward_days].copy()
            
            # Technical signals
            rsi = calc_rsi(signal_data['Close'])
            momentum = calc_momentum_1m(signal_data['Close'])
            volatility = calc_volatility_score(signal_data['Close'])
            
            # Yahoo Finance signals (FREE!)
            insider = get_insider_score_yahoo(ticker)
            institutional = get_institutional_score_yahoo(ticker)
            
            # Forward return
            price_at_signal = signal_data['Close'].iloc[-1]
            price_after = df['Close'].iloc[-1]
            forward_return = ((price_after / price_at_signal) - 1) * 100
            
            result = {
                'ticker': ticker,
                'forward_return': forward_return,
                'is_winner': forward_return > 10,
                # Technical
                'rsi': rsi,
                'momentum_1m': momentum,
                'volatility': volatility,
                # Insider (HUNTER)
                'insider_score': insider['insider_score'],
                'net_insider_buys': insider['net_buys'],
                # Institutional (QUANT)
                'inst_score': institutional['inst_score'],
                'inst_pct': institutional.get('inst_pct', 0),
            }
            results.append(result)
            print(f"OK | Return: {forward_return:+.1f}%")
            
        except Exception as e:
            print(f"ERROR: {e}")
            continue
    
    return pd.DataFrame(results)


def analyze_results(df: pd.DataFrame) -> pd.DataFrame:
    """Analyze signal correlations"""
    signal_cols = [c for c in df.columns if c not in ['ticker', 'forward_return', 'is_winner']]
    
    categories = {
        'rsi': 'CHARTIST',
        'momentum_1m': 'CHARTIST',
        'volatility': 'CHARTIST',
        'insider_score': 'HUNTER',
        'net_insider_buys': 'HUNTER',
        'inst_score': 'QUANT',
        'inst_pct': 'QUANT'
    }
    
    analysis = []
    for signal in signal_cols:
        corr = df[signal].corr(df['forward_return'])
        
        winners = df[df['is_winner']]
        losers = df[~df['is_winner']]
        
        w_avg = winners[signal].mean() if len(winners) > 0 else 0
        l_avg = losers[signal].mean() if len(losers) > 0 else 0
        
        analysis.append({
            'signal': signal,
            'category': categories.get(signal, 'OTHER'),
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
    # Test universe
    TEST_TICKERS = [
        # Large caps
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA",
        "JPM", "JNJ", "V", "PG", "UNH", "HD", "MA",
        "NFLX", "CRM", "INTC", "PFE", "ABT",
        # Growth/volatile
        "PLTR", "SOFI", "COIN", "SQ", "SHOP", "ROKU",
        "CRWD", "SNOW", "NET", "DDOG",
        # Recent movers
        "SMCI", "ARM", "CELH", "CAVA", "ABNB"
    ]
    
    print("="*60)
    print("BACKTEST WITH YAHOO FINANCE FREE DATA")
    print("="*60)
    
    # Run backtest
    results = run_yahoo_backtest(TEST_TICKERS, forward_days=30)
    
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    
    winners = results[results['is_winner']]
    print(f"Total stocks: {len(results)}")
    print(f"Winners (>10%): {len(winners)} ({len(winners)/len(results)*100:.1f}%)")
    print(f"Avg Return: {results['forward_return'].mean():.1f}%")
    
    # Analysis
    print("\n" + "="*60)
    print("SIGNAL ANALYSIS (Ranked by Correlation)")
    print("="*60)
    
    analysis = analyze_results(results)
    
    print(f"\n{'Signal':<18} | {'Cat':<8} | {'Corr':>7} | {'Winner':>7} | {'Loser':>7} | {'Diff':>6}")
    print("-" * 65)
    
    for _, row in analysis.iterrows():
        print(f"{row['signal']:<18} | {row['category']:<8} | {row['correlation']:>+7.3f} | {row['winner_avg']:>7.1f} | {row['loser_avg']:>7.1f} | {row['diff']:>+6.1f}")
    
    # Save
    results.to_csv('yahoo_backtest_results.csv', index=False)
    analysis.to_csv('yahoo_signal_analysis.csv', index=False)
    print("\nSaved to yahoo_backtest_results.csv and yahoo_signal_analysis.csv")
