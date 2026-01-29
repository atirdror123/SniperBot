"""
Diagnostic: Trace Technical Scorer
==================================
Runs the technical scorer on a single high-quality stock (NVDA) 
and prints every internal step to find why it returns 0.
"""
import os
import pandas as pd
import yfinance as yf
from scanner_logic import SniperScorer
from dotenv import load_dotenv

load_dotenv()

def diagnose_scorer():
    ticker = "NVDA"
    print(f"\n🔍 DIAGNOSING {ticker} SCORING...")
    
    # 1. Check Data Fetching
    print("Step 1: Fetching Data...")
    scorer = SniperScorer()
    try:
        data = scorer._fetch_history_with_retry(ticker)
        if data.empty:
            print("❌ FETCH FAILED: Returned empty DataFrame")
            return
        print(f"✅ Data Fetched: {len(data)} rows")
        print("   Latest Row:")
        print(data.iloc[-1])
    except Exception as e:
        print(f"❌ FETCH EXCEPTION: {e}")
        return

    # 2. Run Analyze Stock
    print("\nStep 2: Exceluting analyze_stock()...")
    result = scorer.analyze_stock(ticker, data)
    
    print("\n📊 RESULT DUMP:")
    print(f"Final Score: {result.get('final_score')}")
    print(f"Details: {result.get('details')}")
    print(f"Raw Features: {result.get('raw_features')}")
    
    if result.get('final_score') == 0:
        print("\n❌ CRITICAL FAILURE: Score is 0.")
        print("Checking internal logic...")
        # Check specific conditions that force 0
        if scorer.market_regime == 'BEAR' and not scorer.allow_shorts:
            print("   -> Market Regime is BEAR and shorts skipped")

if __name__ == "__main__":
    diagnose_scorer()
