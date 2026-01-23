"""
Daily Sniper Scan - Production Entry Point

This is the main entry point for daily automated scans.
Uses the full stock universe and runs:
1. Pressure Cooker filter (~10-15 candidates)
2. Tournament AI (Risk Manager picks Top 3)
3. Saves to paper_positions table
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_ingestion import fetch_universe
from sniper_scanner import run_sniper_scan, save_sniper_picks
from scan_logger import get_logger

logger = get_logger("DAILY_SNIPER")


def run_daily_sniper():
    """Main daily scan entry point."""
    logger.info("=" * 60)
    logger.info("🎯 SNIPER BOT V2.0 - DAILY SCAN")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    # Fetch full stock universe
    logger.info("\n📡 Fetching stock universe...")
    universe = fetch_universe()
    
    if not universe:
        logger.error("Failed to fetch universe. Exiting.")
        return
    
    logger.info(f"Universe size: {len(universe)} stocks")
    
    # Run Sniper scan
    top_picks = run_sniper_scan(universe)
    
    if top_picks:
        logger.info(f"\n💰 Saving {len(top_picks)} picks to paper_positions...")
        save_sniper_picks(top_picks)
        
        logger.info("\n🎯 TODAY'S SNIPER PICKS:")
        for i, pick in enumerate(top_picks, 1):
            logger.info(f"  #{i} {pick['ticker']} @ ${pick['price']:.2f}")
    else:
        logger.info("\n⚠️ No stocks passed all filters today.")
    
    logger.info("\n✅ DAILY SNIPER SCAN COMPLETE")


if __name__ == "__main__":
    run_daily_sniper()
