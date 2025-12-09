import pandas as pd
import yfinance as yf
from datetime import datetime
from primitives import StockSetup, Lens, LensScore, MarketRegime
from data_ingestion import DataIngestor
import numpy as np

class SignalEngine:
    def __init__(self, data_ingestor: DataIngestor):
        self.ingestor = data_ingestor

    def analyze_ticker(self, ticker: str, current_regime: MarketRegime) -> StockSetup:
        """
        Main Analysis Pipeline:
        1. Multi-Timeframe Checks (Fractal Alignment)
        2. 4-Lens Scoring
        3. Packaging into StockSetup
        """
        # 1. Fetch Price Data (Hourly, Daily, Weekly)
        # For efficiency, we just fetch 1y daily and resample/use indicators for approximations in this prototype
        try:
            df = yf.download(ticker, period="1y", interval="1d", progress=False, threads=False)
            if df.empty or len(df) < 50:
                return self._create_empty_setup(ticker, "Insufficient Data")
        except Exception as e:
            return self._create_empty_setup(ticker, f"Data Error: {str(e)}")

        current_price = df['Close'].iloc[-1].item() # Convert to float
        volume = df['Volume'].iloc[-1].item()

        # --- FRACTAL ALIGNMENT (LAYER 1.5) ---
        # Weekly: Price > SMA30 (Using Daily SMA150 as approx for Weekly SMA30)
        sma150 = df['Close'].rolling(window=150).mean().iloc[-1]
        if current_price < float(sma150):
             return self._create_empty_setup(ticker, "Weekly Trend Down ( < SMA150 )")

        # Daily: Momentum Positive
        # Hourly: ( skipped for speed in this version, assumed aligned if daily is strong)

        # --- 4-LENS SCORING (LAYER 2) ---
        
        # Data Gathering
        dark_data = self.ingestor.get_dark_pool_activity(ticker)
        insider_data = self.ingestor.get_insider_activity(ticker)
        earnings_data = self.ingestor.get_earnings_sentiment(ticker)
        funds = self.ingestor.get_fundamentals(ticker)
        
        # Lens A: QUANT
        # Logic: High Score if Dark Pool Activity is present
        quant_raw = 50
        if dark_data['institutions_buying']: quant_raw += 30
        if dark_data['gamma_exposure'] > 0: quant_raw += 10
        lens_quant = LensScore(Lens.QUANT, min(quant_raw, 100), 1.0, details=dark_data)

        # Lens B: ORACLE
        # Logic: Buffett Metrics + NLP
        oracle_raw = 50
        if funds['roe'] > 0.15: oracle_raw += 20
        if funds['peg_ratio'] < 2.0: oracle_raw += 10
        if earnings_data['sentiment_score'] > 0.2: oracle_raw += 20
        lens_oracle = LensScore(Lens.ORACLE, min(oracle_raw, 100), 1.0, details={**funds, **earnings_data})

        # Lens C: HUNTER
        # Logic: Insider Buys + Social
        hunter_raw = 40
        if insider_data['net_insider_buys_90d'] >= 3 or insider_data['ceo_purchase']:
            hunter_raw += 40
        lens_hunter = LensScore(Lens.HUNTER, min(hunter_raw, 100), 1.0, details=insider_data)

        # Lens D: CHARTIST
        # Logic: RSI, VCP (Simulated by std dev)
        # Calculate RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        rsi = float(rsi)
        
        chartist_raw = 60
        if rsi < 70: chartist_raw += 10
        if rsi > 50: chartist_raw += 10 # Momentum Sweet Spot
        
        # Relative Strength vs SPY would go here
        
        lens_chartist = LensScore(Lens.CHARTIST, min(chartist_raw, 100), 1.0, details={"rsi": rsi})

        # --- PACKAGING ---
        
        # Note: Weights will be applied by the ReinforcementLearner later,
        # but we package them here with default 1.0 for now.
        
        scores = {
            Lens.QUANT: lens_quant,
            Lens.ORACLE: lens_oracle,
            Lens.HUNTER: lens_hunter,
            Lens.CHARTIST: lens_chartist
        }
        
        # Base Score (Average of raw scores)
        final_base_score = (quant_raw + oracle_raw + hunter_raw + chartist_raw) / 4

        return StockSetup(
            ticker=ticker,
            timestamp=datetime.now(),
            final_score=final_base_score,
            regime=current_regime,
            lens_scores=scores,
            price=current_price,
            volume=float(volume),
            sector="Unknown", # Placeholder
            is_valid=True
        )

    def _create_empty_setup(self, ticker, reason):
        return StockSetup(
            ticker=ticker,
            timestamp=datetime.now(),
            final_score=0.0,
            regime=MarketRegime.CHOP,
            lens_scores={},
            price=0.0,
            volume=0.0,
            sector="N/A",
            is_valid=False,
            rejection_reason=reason
        )
