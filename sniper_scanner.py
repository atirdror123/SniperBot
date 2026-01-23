"""
Sniper Scanner V2.0 - "The Sniper Alpha"

New scanner that:
1. Runs the Pressure Cooker filter to find ~10-15 explosive candidates
2. Applies existing lens scoring (HUNTER weighted heavily per Phase 0 findings)
3. Picks top 3 for paper trading
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import yfinance as yf
import pandas as pd

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client
from pressure_cooker import pressure_cooker_filter
from filter_config import POSITION_CONFIG, LENS_WEIGHTS, MIN_LENS_SCORES
from scan_logger import get_logger
from tournament_ai import run_tournament

logger = get_logger("SNIPER_SCANNER")


def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def get_stock_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch stock data from Yahoo Finance."""
    try:
        df = yf.download(ticker, period=period, progress=False)
        return df
    except:
        return pd.DataFrame()


def run_sniper_scan(universe: list) -> list:
    """
    Main Sniper scan process.
    
    Args:
        universe: List of tickers to scan
    
    Returns:
        List of top 3 candidates for paper trading
    """
    logger.info("=" * 60)
    logger.info("SNIPER SCANNER V2.0 - Explosive Breakout Hunt")
    logger.info(f"Scanning {len(universe)} stocks...")
    logger.info("=" * 60)
    
    # Stage 1: Pressure Cooker Filter
    logger.info("\n🔥 STAGE 1: PRESSURE COOKER FILTER")
    logger.info("-" * 40)
    
    pressure_candidates = []
    
    for i, ticker in enumerate(universe):
        if i % 50 == 0:
            logger.info(f"  Progress: {i}/{len(universe)}")
        
        try:
            df = get_stock_data(ticker, period="6mo")
            if df.empty or len(df) < 50:
                continue
            
            result = pressure_cooker_filter(df, ticker)
            
            if result['passes']:
                pressure_candidates.append({
                    'ticker': ticker,
                    **result['metrics']
                })
                logger.info(f"  ✓ {ticker} PASSED | RSI={result['metrics']['rsi']:.0f} "
                           f"RVOL={result['metrics']['rvol']:.1f}x Δ={result['metrics']['daily_change']:.1f}%")
        
        except Exception as e:
            pass
    
    logger.info(f"\n  Pressure Cooker: {len(pressure_candidates)} candidates passed")
    
    if not pressure_candidates:
        logger.info("No candidates passed Pressure Cooker filter. Exiting.")
        return []
    
    # Stage 2: Score candidates (HUNTER weighted heavily)
    logger.info("\n📊 STAGE 2: SCORING (HUNTER-WEIGHTED)")
    logger.info("-" * 40)
    
    scored_candidates = []
    
    for candidate in pressure_candidates:
        ticker = candidate['ticker']
        
        # Calculate a composite score based on metrics
        # Higher RVOL = better explosion signal
        # Higher pct_from_high = closer to breakout
        # RSI in sweet spot (55-70) preferred
        
        score = 0
        
        # RVOL score (max 30 points)
        rvol_score = min(candidate['rvol'] * 10, 30)
        score += rvol_score
        
        # Blue sky score (max 30 points)
        blue_sky_score = max(0, (candidate['pct_from_high'] - 90) * 3)
        score += min(blue_sky_score, 30)
        
        # RSI sweet spot (max 20 points - peak at 60)
        rsi = candidate['rsi']
        rsi_score = 20 - abs(rsi - 60) * 0.5
        score += max(0, rsi_score)
        
        # Momentum score (max 20 points)
        momentum_score = min(candidate['daily_change'] * 3, 20)
        score += momentum_score
        
        scored_candidates.append({
            **candidate,
            'composite_score': score
        })
        
        logger.info(f"  {ticker}: Score={score:.1f} (RVOL={rvol_score:.0f} "
                   f"BlueSky={blue_sky_score:.0f} RSI={rsi_score:.0f} Mom={momentum_score:.0f})")
    
    # Stage 3: Tournament AI Selection
    logger.info("\n🎯 STAGE 3: TOURNAMENT AI (Risk Manager)")
    logger.info("-" * 40)
    
    # Run AI tournament to ruthlessly analyze and pick Top 3
    ai_result = run_tournament(scored_candidates)
    
    # Extract top 3 tickers from AI result
    top_3_tickers = [pick['ticker'] for pick in ai_result.get('top_3', [])]
    
    # Match back to our candidate data
    top_candidates = []
    for pick in ai_result.get('top_3', []):
        ticker = pick['ticker']
        # Find the candidate with full data
        for c in scored_candidates:
            if c['ticker'] == ticker:
                c['ai_confidence'] = pick.get('confidence', 70)
                c['ai_reason'] = pick.get('entry_reason', 'Selected by AI')
                top_candidates.append(c)
                break
    
    for i, candidate in enumerate(top_candidates, 1):
        logger.info(f"  #{i} {candidate['ticker']} | Score: {candidate['composite_score']:.1f} | "
                   f"AI Confidence: {candidate.get('ai_confidence', 70)}%")
        logger.info(f"      Reason: {candidate.get('ai_reason', 'N/A')}")
    
    logger.info("\n✅ SNIPER SCAN COMPLETE")
    
    return top_candidates


def save_sniper_picks(candidates: list):
    """Save top picks to paper_positions table."""
    supabase = get_supabase()
    
    position_size = POSITION_CONFIG['fixed_position_size']
    
    for candidate in candidates:
        ticker = candidate['ticker']
        price = candidate['price']
        quantity = int(position_size / price)
        cost_basis = quantity * price
        
        position = {
            'portfolio': 'SNIPER',
            'ticker': ticker,
            'entry_price': price,
            'quantity': quantity,
            'cost_basis': cost_basis,
            'status': 'OPEN'
        }
        
        try:
            supabase.table('paper_positions').insert(position).execute()
            logger.info(f"💰 Opened position: {ticker} x{quantity} @ ${price:.2f}")
        except Exception as e:
            logger.error(f"Failed to save position: {e}")


if __name__ == "__main__":
    # Test with a small universe
    test_universe = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'AMD', 'TSLA', 'META', 'AMZN']
    
    candidates = run_sniper_scan(test_universe)
    
    if candidates:
        print("\nWould save these to paper trading:")
        for c in candidates:
            print(f"  {c['ticker']} @ ${c['price']:.2f}")
