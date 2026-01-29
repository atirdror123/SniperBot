from scanner_logic import SniperScorer
import pandas as pd

def check_specific_stocks():
    tickers = ['A', 'AA', 'AAL', 'AAMI', 'AAOI', 'AAPL', 'NVDA', 'TSLA']
    scorer = SniperScorer()
    
    print("\n🔍 CHECKING REJECTION REASONS:")
    print("-" * 60)
    
    for ticker in tickers:
        print(f"Checking {ticker}...", end=" ")
        try:
            result = scorer.analyze_stock(ticker)
            score = result.get('final_score', 0)
            details = result.get('details', 'N/A')
            
            print(f"Score: {score}")
            print(f"   Reason: {details}")
            print("-" * 60)
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    check_specific_stocks()
