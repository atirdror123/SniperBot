import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
from scanner_logic import SniperScorer

class TestAILayer(unittest.TestCase):
    def setUp(self):
        # Force AI enabled
        self.scorer = SniperScorer()
        self.scorer.ai_enabled = True
        
        # Mock sector trends to avoid network call
        self.scorer.sector_status = {'XLK': 'Strong'}
        self.scorer.sector_etf_map = {'Technology': 'XLK'}

    @patch('yfinance.Ticker')
    def test_ai_trigger(self, mock_ticker):
        print("\n--- Testing AI Conviction Layer ---")
        
        # 1. Setup Mock Stock Data (Perfect Setup)
        mock_stock = MagicMock()
        mock_ticker.return_value = mock_stock
        
        # History (Uptrend)
        dates = pd.date_range(end=pd.Timestamp.now(), periods=300)
        # Create a price series that is clearly uptrending
        closes = [100 + i*0.1 for i in range(300)]
        df = pd.DataFrame({'Close': closes, 'Volume': [1000000]*300}, index=dates)
        mock_stock.history.return_value = df
        
        # Fundamentals
        mock_stock.info = {
            'sector': 'Technology',
            'symbol': 'TEST_AI',
            'recommendationKey': 'buy',
            'targetMeanPrice': 200, # Current ~130, so upside exists
            'fiftyTwoWeekHigh': 130
        }
        
        # News (Crucial for AI)
        mock_stock.news = [
            {'title': 'TEST_AI releases revolutionary product', 'publisher': 'TechCrunch'},
            {'title': 'Analysts upgrade TEST_AI target', 'publisher': 'Bloomberg'}
        ]
        
        # Earnings (Safe)
        mock_stock.calendar = None 
        
        # 2. Run Analysis
        # We expect a high technical score -> Trigger AI
        print("Analyzing 'TEST_AI'...")
        result = self.scorer.analyze_stock('TEST_AI')
        
        # 3. Verify Results
        score = result.get('final_score')
        details = result.get('details')
        
        print(f"Final Score: {score}")
        
        ai_triggered = False
        for d in details:
            print(f"- {d}")
            if "🤖 AI INSIGHT" in d:
                ai_triggered = True
                
        if ai_triggered:
            print("\nSUCCESS: AI Layer triggered and provided insight!")
        else:
            print("\nFAILURE: AI Layer did NOT trigger.")
            if score < 75:
                print(f"Reason: Score {score} was too low (needs >= 75).")

if __name__ == '__main__':
    unittest.main()
