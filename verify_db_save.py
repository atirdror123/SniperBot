"""
Verify Data Pipeline
Manually saves a TEST position to paper_positions to verify:
1. DB Connection
2. Write Permissions
3. Dashboard Display
"""
import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sniper_scanner import save_sniper_picks
from scan_logger import get_logger

logger = get_logger("TEST_VERIFY")

def run_verify():
    logger.info("🧪 STARTING VERIFICATION TEST")
    
    # Mock candidate
    test_picks = [{
        'ticker': 'TEST',
        'price': 100.0,
        'composite_score': 99.9,
        'confidence': 99,
        'entry_reason': 'Manual Verification Test'
    }]
    
    logger.info("💾 Saving 'TEST' ticker to DB...")
    save_sniper_picks(test_picks)
    
    logger.info("✅ Verification Complete. Check Dashboard for 'TEST' ticker.")

if __name__ == "__main__":
    run_verify()
