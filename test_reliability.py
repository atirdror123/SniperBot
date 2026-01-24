"""
Comprehensive Test Suite for SniperBot Reliability Refactor
Tests: Chrono-Guard, Data Ingestion, Scanner Logic, Logging
"""
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all modules import without errors."""
    print("\n=== TEST 1: Module Imports ===")
    try:
        from scan_logger import get_logger, ScanMetrics
        print("  ✓ scan_logger")
        
        from chrono_guard import ChronoGuard
        print("  ✓ chrono_guard")
        
        from data_ingestion import DataIngestor
        print("  ✓ data_ingestion")
        
        from scanner_logic import SniperScorer
        print("  ✓ scanner_logic")
        
        from main_sentient import SentientSniperBot
        print("  ✓ main_sentient")
        
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False

def test_chrono_guard():
    """Test Chrono-Guard logic."""
    print("\n=== TEST 2: Chrono-Guard ===")
    try:
        from chrono_guard import ChronoGuard
        
        # Test weekend detection
        guard = ChronoGuard(research_mode=False)
        is_weekend = guard.is_weekend()
        print(f"  Weekend check: {is_weekend}")
        
        # Test holiday detection
        is_holiday = guard.is_holiday()
        print(f"  Holiday check: {is_holiday}")
        
        # Test market hours
        is_market_hours = guard.is_market_hours()
        print(f"  Market hours check: {is_market_hours}")
        
        # Test research mode bypass
        guard_research = ChronoGuard(research_mode=True)
        result = guard_research.check_and_gate()
        print(f"  Research mode bypass: {result}")
        
        print("  ✓ Chrono-Guard tests passed")
        return True
    except Exception as e:
        print(f"  ✗ Chrono-Guard test failed: {e}")
        return False

def test_scan_logger():
    """Test structured logging and metrics."""
    print("\n=== TEST 3: Scan Logger & Metrics ===")
    try:
        from scan_logger import get_logger, ScanMetrics
        
        logger = get_logger("TEST")
        logger.info("Test log message")
        print("  ✓ Logger initialized")
        
        metrics = ScanMetrics()
        metrics.universe_size = 100
        metrics.batches_attempted = 10
        metrics.batches_succeeded = 9
        metrics.batches_failed = 1
        metrics.log_error("TEST", "Test error")
        
        summary = metrics.get_summary()
        print(f"  ✓ Metrics summary: {summary['batch_success_rate']}% success rate")
        
        return True
    except Exception as e:
        print(f"  ✗ Scan Logger test failed: {e}")
        return False

def test_data_ingestion():
    """Test data ingestion with retry logic."""
    print("\n=== TEST 4: Data Ingestion (Universe Fetch) ===")
    try:
        from data_ingestion import DataIngestor
        
        ingestor = DataIngestor()
        
        # Test with small limit to verify functionality
        universe = ingestor.fetch_universe(limit=100)
        
        if len(universe) > 0:
            print(f"  ✓ Fetched {len(universe)} tickers")
            print(f"  Sample: {universe[:5]}")
            return True
        else:
            print("  ✗ Returned 0 tickers")
            return False
            
    except Exception as e:
        print(f"  ✗ Data ingestion test failed: {e}")
        return False

def test_scanner_logic():
    """Test scanner logic with retry."""
    print("\n=== TEST 5: Scanner Logic (YF Retry) ===")
    try:
        from scanner_logic import SniperScorer
        
        scorer = SniperScorer()
        
        # Test with a known good ticker
        result = scorer._fetch_history_with_retry("AAPL", period="1mo")
        
        if not result.empty:
            print(f"  ✓ Fetched {len(result)} days of data for AAPL")
            return True
        else:
            print("  ✗ Empty history returned")
            return False
            
    except Exception as e:
        print(f"  ✗ Scanner logic test failed: {e}")
        return False

def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*50)
    print("SNIPERBOT RELIABILITY TEST SUITE")
    print(f"Run at: {datetime.now()}")
    print("="*50)
    
    results = {
        "imports": test_imports(),
        "chrono_guard": test_chrono_guard(),
        "scan_logger": test_scan_logger(),
        "data_ingestion": test_data_ingestion(),
        "scanner_logic": test_scanner_logic(),
    }
    
    print("\n" + "="*50)
    print("TEST RESULTS")
    print("="*50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"  {test}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print("\n⚠️ SOME TESTS FAILED")
        return 1

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    exit_code = run_all_tests()
    sys.exit(exit_code)
