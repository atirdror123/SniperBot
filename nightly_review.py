"""
Nightly Review: Multi-Period Self-Learning (6 checkpoints)

Reviews stocks at 10, 20, 30, 40, 50, and 60 days.
Each period outcome is stored separately - no overwriting.
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import yfinance as yf

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client
from reinforcement_learner import SentientBrain, REVIEW_PERIODS
from scan_logger import get_logger

logger = get_logger("NIGHTLY_REVIEW")


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
    """Multi-period review process (10, 20, 30, 40, 50, 60 days)."""
    logger.info("=" * 60)
    logger.info("NIGHTLY REVIEW: Multi-Period Self-Learning (6 checkpoints)")
    logger.info(f"Review periods: {REVIEW_PERIODS}")
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
    for period in REVIEW_PERIODS:
        logger.info(f"\n--- Checking {period}-Day Reviews ---")
        
        # Column names for this period
        outcome_col = f"outcome_{period}d"
        
        # Calculate date range (stocks entered around period days ago)
        target_date = (datetime.now() - timedelta(days=period)).strftime("%Y-%m-%d")
        range_start = (datetime.now() - timedelta(days=period + 2)).strftime("%Y-%m-%d")
        range_end = (datetime.now() - timedelta(days=period - 2)).strftime("%Y-%m-%d")
        
        logger.info(f"Looking for entries from {range_start} to {range_end} with {outcome_col}='PENDING'")
        
        # Find stocks that need this specific period reviewed
        try:
            response = supabase.table("sentient_memory") \
                .select("*") \
                .eq(outcome_col, "PENDING") \
                .gte("entry_date", range_start) \
                .lte("entry_date", range_end) \
                .execute()
            
            pending = response.data
            logger.info(f"Found {len(pending)} stocks needing {period}D review")
            
        except Exception as e:
            logger.error(f"Failed to fetch pending for {period}D: {e}")
            continue
        
        if not pending:
            continue
        
        # Process each stock
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
                logger.warning(f"Skipping incomplete record ID {memory_id}")
                continue
            
            # Get current price
            current_price = get_current_price(ticker)
            if current_price is None:
                logger.warning(f"Could not get price for {ticker}")
                continue
            
            # Calculate outcome
            outcome_pct = (current_price - entry_price) / entry_price
            
            logger.info(f"{ticker} @{period}D: ${entry_price:.2f} -> ${current_price:.2f} = {outcome_pct*100:+.1f}%")
            
            # Log period-specific outcome (no overwriting!)
            brain.log_period_outcome(
                memory_id=memory_id,
                outcome_pct=outcome_pct,
                regime=regime,
                lens_scores=lens_scores,
                period=period
            )
            total_reviewed += 1
    
    logger.info("\n" + "=" * 60)
    logger.info(f"REVIEW COMPLETE: Processed {total_reviewed} period-checks")
    logger.info("=" * 60)


if __name__ == "__main__":
    run_nightly_review()
