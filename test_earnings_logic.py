from scanner_logic import SniperScorer
from datetime import date, timedelta
import unittest
from unittest.mock import MagicMock
import pandas as pd

class TestEarningsLogic(unittest.TestCase):
    def setUp(self):
        self.scorer = SniperScorer()
        self.scorer.sector_etf_map = {} # Disable sector logic for this test to focus on earnings
        self.scorer._prefetch_sector_trends = MagicMock() # Mock this to avoid network calls

    def test_earnings_penalty_calendar(self):
        """Test penalty when earnings are tomorrow (via calendar)"""
        print("\nTesting: Earnings Tomorrow (via Calendar)")
        
        mock_stock = MagicMock()
        mock_stock.info = {'sector': 'Technology'}
        mock_stock.history.return_value = pd.DataFrame({
            'Close': [100]*200, 
            'Volume': [1000000]*200,
            'High': [110]*200,
            'Low': [90]*200
        }) # Dummy data
        
        # Earnings tomorrow
        today = date.today()
        tomorrow = today + timedelta(days=1)
        
        mock_stock.calendar = {'Earnings Date': [tomorrow]}
        mock_stock.earnings_dates = None
        
        # Patch yfinance Ticker to return our mock
        with unittest.mock.patch('yfinance.Ticker', return_value=mock_stock):
            result = self.scorer.analyze_stock('TEST')
            details = result['details']
            print(f"Details: {details}")
            self.assertIn("EARNINGS RISK", details)
            self.assertIn("-50", details)

    def test_earnings_safe_calendar(self):
        """Test NO penalty when earnings are 20 days away (via calendar)"""
        print("\nTesting: Earnings Safe (20 days away)")
        
        mock_stock = MagicMock()
        mock_stock.info = {'sector': 'Technology'} 
        mock_stock.history.return_value = pd.DataFrame({
            'Close': [100]*200, 
            'Volume': [1000000]*200,
            'High': [110]*200,
            'Low': [90]*200
        })
        
        today = date.today()
        future = today + timedelta(days=20)
        
        mock_stock.calendar = {'Earnings Date': [future]}
        
        with unittest.mock.patch('yfinance.Ticker', return_value=mock_stock):
            result = self.scorer.analyze_stock('TEST')
            details = result['details']
            print(f"Details: {details}")
            self.assertIn("Earnings Safe", details)
            self.assertNotIn("EARNINGS RISK", details)

if __name__ == '__main__':
    unittest.main()
