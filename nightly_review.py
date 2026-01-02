"""
Nightly Review: Self-Learning Feedback Loop (ADVANCED)

This script runs daily to:
1. Find stock picks at MULTIPLE review periods (10, 20, 30 days)
2. Check their current price vs entry price
3. Calculate outcome (WIN/LOSS/HOLD)
4. Adjust lens weights using PROPORTIONAL gradient descent
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import yfinance as yf

load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client
from reinforcement_learner import SentientBrain
from scan_logger import get_logger

logger = get_logger("NIGHTLY_REVIEW")

# Multi-period review: Check picks at these day intervals
REVIEW_PERIODS = [10, 20, 30]


def get_current_price(ticker: str) -> float:
    """Fetches current price for a ticker."""
    try:
        data = yf.download(ticker, period="1d", progress=False)
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        logger.warning(f"Failed to get price for {ticker}: {e}")
    return None


def run_nightly_review():
    """Main review process with multi-period checking."""
    logger.info("=" * 60)
    logger.info("NIGHTLY REVIEW: Advanced Self-Learning Feedback Loop")
    logger.info("=" * 60)
    
    # Initialize
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        logger.error("Missing SUPABASE credentials")
        return
    
    supabase = create_client(url, key)
    brain = SentientBrain()
    
    total_reviewed = 0
    
    # Process each review period
    for period_days in REVIEW_PERIODS:
        logger.info(f"\n--- Checking {period_days}-Day Reviews ---")
        
        # Calculate target date range (picks from exactly period_days ago, +/- 1 day tolerance)
        target_date = (datetime.now() - timedelta(days=period_days)).strftime("%Y-%m-%d")
        range_start = (datetime.now() - timedelta(days=period_days + 1)).strftime("%Y-%m-%d")
        range_end = (datetime.now() - timedelta(days=period_days - 1)).strftime("%Y-%m-%d")
        
        logger.info(f"Looking for picks from {range_start} to {range_end}")
        
        # Find pending picks in this date range
        try:
            response = supabase.table("sentient_memory") \
                .select("*") \
                .eq("outcome_label", "PENDING") \
                .gte("entry_date", range_start) \
                .lte("entry_date", range_end) \
                .execute()
            
            pending = response.data
            logger.info(f"Found {len(pending)} picks to review at {period_days}D")
            
        except Exception as e:
            logger.error(f"Failed to fetch pending picks: {e}")
            continue
        
        if not pending:
            continue
        
        # Process each pick
        for pick in pending:
            ticker = pick.get("ticker")
            entry_price = pick.get("entry_price")
            regime = pick.get("regime")
            memory_id = pick.get("id")
            
            # Get lens scores for proportional adjustment
            lens_scores = {
                "QUANT": pick.get("score_quant", 0) or 0,
                "ORACLE": pick.get("score_oracle", 0) or 0,
                "HUNTER": pick.get("score_hunter", 0) or 0,
                "CHARTIST": pick.get("score_chartist", 0) or 0
            }
            
            if not all([ticker, entry_price, regime, memory_id]):
                logger.warning(f"Skipping incomplete record: {pick}")
                continue
            
            # Get current price
            current_price = get_current_price(ticker)
            if current_price is None:
                logger.warning(f"Could not get price for {ticker}. Skipping.")
                continue
            
            # Calculate outcome
            outcome_pct = (current_price - entry_price) / entry_price
            
            logger.info(f"{ticker}: ${entry_price:.2f} -> ${current_price:.2f} = {outcome_pct*100:+.1f}%")
            
            # Update weights via brain (with proportional gradient descent)
            brain.log_outcome(
                memory_id=memory_id,
                outcome_pct=outcome_pct,
                regime=regime,
                lens_scores=lens_scores,
                review_period=period_days
            )
            total_reviewed += 1
    
    logger.info("\n" + "=" * 60)
    logger.info(f"REVIEW COMPLETE: Processed {total_reviewed} picks across all periods")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_nightly_review()
