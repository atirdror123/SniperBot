from unittest.mock import MagicMock, patch
import pandas as pd
from scanner_logic import SniperScorer
import sys
import os
from dotenv import load_dotenv

load_dotenv()


# Redirect output to file to ensure capture
with open("test_result_log.txt", "w", encoding="utf-8") as log:
    sys.stdout = log
    
    print("--- STARTING AI TEST ---")
    
    try:
        # Init Scorer (Real init)
        scorer = SniperScorer()
        scorer.ai_enabled = True
        scorer.sector_status = {'XLK': 'Strong'}
        scorer.sector_etf_map = {'Technology': 'XLK'}
        
        print("Scorer initialized.")

        # Mock the Ticker
        with patch('yfinance.Ticker') as mock_ticker:
            mock_stock = MagicMock()
            mock_ticker.return_value = mock_stock
            
            # 1. History (Strong Uptrend)
            dates = pd.date_range(end=pd.Timestamp.now(), periods=300)
            closes = [100 + i*0.3 for i in range(300)] # Even Stronger slope
            
            # Create full OHLCV
            volumes = [10000000]*299
            volumes.append(50000000) # RVOL Spike (5x average) on last day
            
            df = pd.DataFrame({
                'Open': closes,
                'High': [c + 1 for c in closes],
                'Low': [c - 1 for c in closes],
                'Close': closes, 
                'Volume': volumes
            }, index=dates)
            mock_stock.history.return_value = df
            
            # 2. Fundamentals
            mock_stock.info = {
                'sector': 'Technology', 'symbol': 'TEST_AI',
                'recommendationKey': 'strong_buy', 
                'targetMeanPrice': 300, 
                'fiftyTwoWeekHigh': 160 # Current is ~190 (100+300*0.3) = 190. Proximity to high.
            }
            # Adjust closes to match 52w high better
            # If start 100, +0.3*300 = +90 => 190.
            # 52w High should be ~190.
            mock_stock.info['fiftyTwoWeekHigh'] = 190

            # 3. News
            mock_stock.news = [
                {'title': 'TEST_AI revenue grows 500%', 'publisher': 'FutureNews'},
                {'title': 'Analyst predicts massive breakout', 'publisher': 'WSJ'}
            ]
            
            # 4. Earnings
            mock_stock.calendar = None

            # Run Analysis
            print("Running analyze_stock('TEST_AI')...")
            result = scorer.analyze_stock('TEST_AI')
            
            print(f"Ticker: {result['ticker']}")
            print(f"Final Score: {result['final_score']}")
            
            print(f"DETAILS: {result['details']}")
            
            if "🤖 AI INSIGHT" in result['details']:
                 print("\n✅ TEST PASSED: AI Conviction Layer Triggered.")
            else:
                 print("\n❌ TEST FAILED: AI did not trigger.")

    except Exception as e:
        print(f"CRITICAL EXCEPTION: {e}")
        import traceback
        traceback.print_exc()

sys.stdout = sys.__stdout__
print("Test complete. Check test_result_log.txt")
