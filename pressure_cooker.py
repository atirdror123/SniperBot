"""
Pressure Cooker Filter - Explosive Breakout Detection

Filters the entire US market down to ~10-15 "explosive" candidates.
Uses scientifically-tuned thresholds from Phase 0 data mining.
"""
import pandas as pd
import numpy as np
from filter_config import WINNER_PROFILE, MIN_LENS_SCORES


def calculate_rsi(prices: pd.Series, period: int = 14) -> float:
    """Calculate RSI from price series."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    
    if loss.iloc[-1] == 0:
        return 100
    
    rs = gain.iloc[-1] / loss.iloc[-1]
    return 100 - (100 / (1 + rs))


def calculate_rvol(volume: pd.Series, lookback: int = 10) -> float:
    """Calculate Relative Volume (current vs average)."""
    avg_vol = volume.tail(lookback + 1).iloc[:-1].mean()
    current_vol = volume.iloc[-1]
    
    return current_vol / avg_vol if avg_vol > 0 else 1.0


def calculate_bb_width(prices: pd.Series, period: int = 20) -> float:
    """Calculate Bollinger Band Width (normalized)."""
    sma = prices.rolling(period).mean().iloc[-1]
    std = prices.rolling(period).std().iloc[-1]
    
    return (std * 4) / sma if sma > 0 else 0


def pressure_cooker_filter(df: pd.DataFrame, ticker: str = None) -> dict:
    """
    The "Pressure Cooker" Filter - finds explosive breakout candidates.
    
    Args:
        df: DataFrame with columns: Open, High, Low, Close, Volume
        ticker: Stock symbol (for logging)
    
    Returns:
        dict with 'passes' (bool) and 'metrics' (details)
    """
    if len(df) < 50:  # Need enough history
        return {'passes': False, 'reason': 'Insufficient data', 'metrics': {}}
    
    close = df['Close']
    high = df['High']
    volume = df['Volume']
    
    # Get configuration
    config = WINNER_PROFILE
    
    # Calculate all metrics
    current_price = close.iloc[-1]
    prev_close = close.iloc[-2]
    
    # 1. RSI (14-day)
    rsi = calculate_rsi(close)
    
    # 2. RVOL (Relative Volume)
    rvol = calculate_rvol(volume)
    
    # 3. Daily Change %
    daily_change = ((current_price - prev_close) / prev_close) * 100
    
    # 4. Bollinger Band Width
    bb_width = calculate_bb_width(close)
    
    # 5. Distance from 52-Week High
    high_52w = high.tail(252).max() if len(high) >= 252 else high.max()
    pct_from_high = (current_price / high_52w) * 100
    
    # 6. EMA Alignment (Price > EMA20 > EMA50)
    ema20 = close.ewm(span=20).mean().iloc[-1]
    ema50 = close.ewm(span=50).mean().iloc[-1]
    ema_aligned = (current_price > ema20) and (ema20 > ema50)
    
    metrics = {
        'rsi': rsi,
        'rvol': rvol,
        'daily_change': daily_change,
        'bb_width': bb_width,
        'pct_from_high': pct_from_high,
        'ema_aligned': ema_aligned,
        'price': current_price
    }
    
    # Apply filters
    filters = []
    
    # RSI in range
    if not (config['rsi_min'] <= rsi <= config['rsi_max']):
        filters.append(f"RSI {rsi:.0f} not in {config['rsi_min']}-{config['rsi_max']}")
    
    # Volume explosion
    if rvol < config['rvol_min']:
        filters.append(f"RVOL {rvol:.1f}x < {config['rvol_min']}x")
    
    # Daily momentum range
    if not (config['daily_change_min'] <= daily_change <= config['daily_change_max']):
        filters.append(f"Daily Δ {daily_change:.1f}% not in {config['daily_change_min']}-{config['daily_change_max']}%")
    
    # Bollinger squeeze
    if bb_width > config['bb_width_max']:
        filters.append(f"BB Width {bb_width:.3f} > {config['bb_width_max']}")
    
    # Blue sky potential
    if pct_from_high < config['pct_from_52w_high_min']:
        filters.append(f"From 52WH {pct_from_high:.0f}% < {config['pct_from_52w_high_min']}%")
    
    # EMA alignment
    if config.get('require_ema_alignment', True) and not ema_aligned:
        filters.append("EMA not aligned (need Price > EMA20 > EMA50)")
    
    passes = len(filters) == 0
    
    return {
        'passes': passes,
        'metrics': metrics,
        'failed_filters': filters,
        'reason': filters[0] if filters else 'PASSED'
    }


def run_pressure_cooker_on_universe(tickers: list, get_data_func) -> list:
    """
    Run the Pressure Cooker filter on a list of tickers.
    
    Args:
        tickers: List of stock symbols
        get_data_func: Function that takes ticker and returns DataFrame
    
    Returns:
        List of candidates that passed all filters
    """
    candidates = []
    
    for i, ticker in enumerate(tickers):
        try:
            df = get_data_func(ticker)
            result = pressure_cooker_filter(df, ticker)
            
            if result['passes']:
                candidates.append({
                    'ticker': ticker,
                    **result['metrics']
                })
                print(f"✓ {ticker}: PASSED | RSI={result['metrics']['rsi']:.0f} "
                      f"RVOL={result['metrics']['rvol']:.1f}x Δ={result['metrics']['daily_change']:.1f}%")
            
        except Exception as e:
            pass  # Skip problematic tickers
    
    return candidates
