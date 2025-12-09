from scanner_logic import SniperScorer
import sys
import os

# Mock env if needed (or rely on existing .env loading in scanner_logic)
# scanner_logic loads .env at module level so it should be fine if .env exists.

def test_sector_logic():
    print("--- Testing Sector Logic Initialization ---")
    scorer = SniperScorer()
    
    print("\n[Sector Status Map]")
    for etf, status in scorer.sector_status.items():
        print(f"  {etf}: {status}") 
        
    if not scorer.sector_status:
        print("ERROR: Sector status is empty!")
        return

    print("\n--- Testing Stock Analysis (Sector Check) ---")
    
    # Test cases: known sectors
    # We need real tickers that yfinance can fetch
    test_tickers = ['AAPL', 'JPM', 'XOM', 'PFE'] # Tech, Financial, Energy, Healthcare
    
    for ticker in test_tickers:
        print(f"\nAnalyzing {ticker}...")
        result = scorer.analyze_stock(ticker)
        details = result['details']
        score = result['final_score']
        
        print(f"  Score: {score}")
        # Look for sector specific strings
        sector_msgs = [d for d in details.split('; ') if "Sector" in d]
        if sector_msgs:
            for msg in sector_msgs:
                print(f"  Found Sector Msg: {msg}")
        else:
            print(f"  WARNING: No sector message found in details!")
            print(f"  Full Details: {details}")

if __name__ == "__main__":
    test_sector_logic()
