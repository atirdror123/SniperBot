import os
import sys
# Mock Streamlit for local run if needed, or just standard run
import pandas as pd
from scanner_logic import SniperScorer
from dotenv import load_dotenv

load_dotenv()

def dry_run():
    print("--- DRY RUN: TESTING STRICT SCORING (Threshold: 80) ---")
    scorer = SniperScorer()
    
    # Mix of likely winners and losers
    tickers = [
        "NVDA", "AAPL", "AMD", # Strong Tech
        "TSLA", "AMZN", 
        "XOM", "CVX", # Energy
        "PFE", # Pharma (often weak trend)
        "PLTR", "SOFI", # Retail favs
        "GME", # Meme/Volatile
        "F" # Slow mover
    ]
    
    print(f"Testing {len(tickers)} stocks...")
    print(f"{'TICKER':<6} | {'SCORE':<5} | {'SMA200 Check':<15} | {'DETAILS'}")
    print("-" * 80)
    
    passed_count = 0
    
    for t in tickers:
        try:
            result = scorer.analyze_stock(t)
            score = result['final_score']
            details = result['details']
            
            # Check if it hit the Hard Filter
            sma200_status = "PASS"
            if "Price Below SMA200" in details:
                sma200_status = "FAIL (Hard)"
            
            # Check if it hit the Score Filter
            score_status = "PASS" if score >= 80 else f"FAIL ({score})"
            
            print(f"{t:<6} | {score:<5} | {sma200_status:<15} | {details[:50]}...")
            
            if score >= 80 and sma200_status == "PASS":
                passed_count += 1
                
        except Exception as e:
            print(f"{t:<6} | ERR   | {str(e)}")

    print("-" * 80)
    print(f"Pass Rate: {passed_count}/{len(tickers)}")
    
    if passed_count == 0:
        print("WARNING: Criteria might be too strict (0 passed).")
    else:
        print("Scoring looks viable.")

if __name__ == "__main__":
    dry_run()
