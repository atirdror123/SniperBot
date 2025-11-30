from scanner_logic import SniperScorer

def test_scorer():
    scorer = SniperScorer()
    ticker = "NVDA" # Using a strong stock as requested
    
    print(f"Running SniperScorer analysis on {ticker}...")
    result = scorer.analyze_stock(ticker)
    
    print("\n" + "="*30)
    print(f"RESULTS FOR {result['ticker']}")
    print("="*30)
    print(f"Final Score: {result['final_score']}")
    print("-" * 30)
    print("Details:")
    for detail in result['details'].split('; '):
        print(f"- {detail}")
    print("="*30)

if __name__ == "__main__":
    test_scorer()
