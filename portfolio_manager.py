import pandas as pd
import yfinance as yf
from typing import List
from primitives import StockSetup, SafetyStatus

class PortfolioManager:
    """
    Layer 4: Portfolio & Risk Management.
    Enforces Diversification and Position Sizing.
    """
    def __init__(self):
        self.max_correlation = 0.7

    def filter_for_diversification(self, setups: List[StockSetup]) -> List[StockSetup]:
        """
        Ensures no two stocks in the Top 10 have correlation > 0.7.
        """
        print("[RISK] Checking Portfolio Correlation Matrix...")
        if len(setups) < 2:
            return setups
            
        # Get tickers
        tickers = [s.ticker for s in setups]
        
        # Download recent history to check correlation
        # We use strict 'Close' prices for last 90 days
        try:
            data = yf.download(tickers, period="3mo", progress=False)['Close']
        except:
            print("[RISK] Failed to download correlation data. Allowing all.")
            return setups

        # If only one ticker, data is Series, not DataFrame
        if isinstance(data, pd.Series):
             return setups

        # Calculate Correlation Matrix
        corr_matrix = data.corr()
        
        # Greedy Filter: Keep highest scoring setup, discard highly correlated peers
        kep_indices = set(range(len(setups)))
        
        # Sort by score descending so we keep the best
        # setups is assumed to be sorted, but let's be safe
        sorted_indices = sorted(range(len(setups)), key=lambda i: setups[i].final_score, reverse=True)
        
        final_list = []
        accepted_tickers = set()
        
        for i in sorted_indices:
            candidate = setups[i]
            ticker_i = candidate.ticker
            
            is_correlated = False
            for accepted_ticker in accepted_tickers:
                # Check correlation
                if ticker_i in data.columns and accepted_ticker in data.columns:
                    c = corr_matrix.loc[ticker_i, accepted_ticker]
                    if c > self.max_correlation:
                        print(f"[RISK] REJECTED {ticker_i}: Too correlated with {accepted_ticker} ({c:.2f})")
                        is_correlated = True
                        break
            
            if not is_correlated:
                final_list.append(candidate)
                accepted_tickers.add(ticker_i)
                
        return final_list

    def calculate_position_size(self, capital: float, safety_status: SafetyStatus) -> float:
        """
        Dynamic Position Sizing based on Iron Dome status.
        """
        base_risk = 0.02 # Risk 2% of account per trade
        
        if safety_status == SafetyStatus.ANGER:
            return 0.0 # No trades
        elif safety_status == SafetyStatus.CAUTION:
            return capital * (base_risk / 2) # Half size
        else:
            return capital * base_risk # Full size
