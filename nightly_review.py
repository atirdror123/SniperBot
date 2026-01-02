"""
Nightly Review: Self-Learning Feedback Loop

This script runs daily to:
1. Find stock picks that are 20+ days old
2. Check their current price vs entry price
3. Calculate outcome (WIN/LOSS/HOLD)
4. Adjust lens weights via gradient descent
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

# Review period: Check picks that are at least this many days old
REVIEW_DAYS = 20


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
    """Main review process."""
    logger.info("=" * 50)
    logger.info("NIGHTLY REVIEW: Self-Learning Feedback Loop")
    logger.info("=" * 50)
    
    # Initialize
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        logger.error("Missing SUPABASE credentials")
        return
    
    supabase = create_client(url, key)
    brain = SentientBrain()
    
    # Calculate cutoff date (20 days ago)
    cutoff_date = (datetime.now() - timedelta(days=REVIEW_DAYS)).strftime("%Y-%m-%d")
    
    logger.info(f"Looking for picks older than {cutoff_date}")
    
    # Find pending picks that are old enough
    try:
        response = supabase.table("sentient_memory") \
            .select("*") \
            .eq("outcome_label", "PENDING") \
            .lte("entry_date", cutoff_date) \
            .execute()
        
        pending = response.data
        logger.info(f"Found {len(pending)} picks to review")
        
    except Exception as e:
        logger.error(f"Failed to fetch pending picks: {e}")
        return
    
    if not pending:
        logger.info("No picks ready for review. Exiting.")
        return
    
    # Process each pick
    reviewed_count = 0
    for pick in pending:
        ticker = pick.get("ticker")
        entry_price = pick.get("entry_price")
        regime = pick.get("regime")
        memory_id = pick.get("id")
        
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
        
        logger.info(f"{ticker}: Entry ${entry_price:.2f} -> Current ${current_price:.2f} = {outcome_pct*100:.1f}%")
        
        # Update weights via brain
        brain.log_outcome(memory_id, outcome_pct, regime)
        reviewed_count += 1
    
    logger.info("=" * 50)
    logger.info(f"REVIEW COMPLETE: Processed {reviewed_count} picks")
    logger.info("=" * 50)


if __name__ == "__main__":
    run_nightly_review()
