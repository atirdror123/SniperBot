import yfinance as yf
import pandas as pd
from primitives import SafetyStatus, MarketRegime

class IronDome:
    def __init__(self):
        self.spy_ticker = "SPY"
        self.market_breadth_threshold = 0.60 # Arbitrary simple threshold for now
        
    def check_market_environment(self) -> tuple[SafetyStatus, MarketRegime]:
        """
        Layer 1: The Global Safety Check.
        Returns the SafetyStatus (SAFE/ANGER) and the MarketRegime (BULL/BEAR).
        """
        print(f"[IRON DOME] Scanning Global Markets...")
        
        # 1. Fetch S&P 500 Data (SPY) for Trend
        spy = yf.Ticker(self.spy_ticker)
        hist = spy.history(period="1y")
        
        if hist.empty:
            print("[IRON DOME] CRITICAL: SPY Data Unreachable. Defaulting to ANGER.")
            return SafetyStatus.ANGER, MarketRegime.CHOP

        current_price = hist['Close'].iloc[-1]
        sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
        
        # Define Regime
        if current_price > sma200:
            regime = MarketRegime.BULL
            print(f"[IRON DOME] Market Regime: BULL (Price {current_price:.2f} > SMA200 {sma200:.2f})")
        else:
            regime = MarketRegime.BEAR
            print(f"[IRON DOME] Market Regime: BEAR (Price {current_price:.2f} < SMA200 {sma200:.2f})")
            
        # 2. Market Breadth / VIX Check (Simplified for "Iron Dome")
        # In a real app, we'd check Advance/Decline line here.
        # For now, we will use VIX as a proxy for "ANGER".
        vix = yf.Ticker("^VIX")
        vix_hist = vix.history(period="5d")
        
        if not vix_hist.empty:
            current_vix = vix_hist['Close'].iloc[-1]
            print(f"[IRON DOME] VIX Level: {current_vix:.2f}")
            
            if current_vix > 30:
                print("[IRON DOME] ALERT: Volatility Extreme. KILL SWITCH ENGAGED.")
                return SafetyStatus.ANGER, regime
            elif current_vix > 20:
                print("[IRON DOME] CAUTION: Volatility Elevated. Reduced sizing.")
                return SafetyStatus.CAUTION, regime
        
        print("[IRON DOME] Environment: STABLE.")
        return SafetyStatus.SAFE, regime

    def check_liquidity(self, ticker: str, price: float, avg_volume: float) -> bool:
        """
        Layer 1 Strict Liquidity Filters:
        - Price > $2.00
        - Dollar Volume > $5M/day
        """
        if price < 2.00:
            return False
            
        dollar_vol = price * avg_volume
        if dollar_vol < 5_000_000:
            return False
            
        return True
