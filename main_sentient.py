import os
import argparse
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

from primitives import MarketRegime, SafetyStatus, StockSetup, Lens
from iron_dome import IronDome
from data_ingestion import DataIngestor
from signal_engine import SignalEngine
from reinforcement_learner import SentientBrain
from portfolio_manager import PortfolioManager

# Load Environment
load_dotenv()

class SentientSniperBot:
    def __init__(self):
        self.supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
        
        # Initialize Layers
        self.iron_dome = IronDome()
        self.ingestor = DataIngestor()
        self.brain = SentientBrain()
        self.signal_engine = SignalEngine(self.ingestor)
        self.portfolio_manager = PortfolioManager()
        
        self.tickers_to_scan = [
            # Sample list for valid testing
            "AAPL", "NVDA", "AMD", "TSLA", "MSFT", 
            "AMZN", "GOOGL", "META", "JPM", "BAC", 
            "XOM", "CVX", "PFE", "LLY", "UNH"
        ]

    def reset_system(self):
        """
        Wipes the sentient_memory and resets weights.
        """
        print("[SYSTEM] --- RESETTING SYSTEM ---")
        
        # 1. Reset Memory
        try:
            self.supabase.table("sentient_memory").delete().neq("ticker", "XXXX").execute()
            print("[SYSTEM] Sentient Memory Wiped.")
        except Exception as e:
            if "nd" in str(e) or "not found" in str(e) or "404" in str(e): 
                print("[SYSTEM] Warning: 'sentient_memory' table not found. Skipping.")
            else:
                print(f"[SYSTEM] Error wiping memory: {e}")

        # 2. Reset Signals
        try:
            self.supabase.table("sniper_signals").delete().neq("ticker", "XXXX").execute()
            print("[SYSTEM] Sniper Signals Wiped.")
        except Exception as e:
            print(f"[SYSTEM] Error wiping signals: {e}")

    def run_daily_cycle(self):
        print("\n" + "="*50)
        print(f"SENTIENT SNIPER - DAILY CYCLE - {datetime.now()}")
        print("="*50)

        # 1. IRON DOME (Layer 1)
        safety, regime = self.iron_dome.check_market_environment()
        if safety == SafetyStatus.ANGER:
            print("[IRON DOME] KILL SWITCH ENGAGED. ABORTING SCAN.")
            return

        # 2. GET WEIGHTS (Layer 3 - Brain)
        weights = self.brain.get_weights(regime)
        print(f"[BRAIN] Active Weights for {regime.name}: {weights}")

        # 3. SCAN & SCORE (Layer 2)
        candidates = []
        # 3. SCAN & SCORE (Layer 2)
        candidates = []
        
        # A. FMP Screener (FMP 1 call)
        print("[SCANNER] Fetching Universe from FMP Screener...")
        universe = self.ingestor.fetch_universe()
        print(f"[SCANNER] Universe Size: {len(universe)} stocks.")
        
        # B. Batch Processing
        BATCH_SIZE = 100
        # Simple Rate Limiting: 300 calls/min = 5 calls/sec. 
        # Deep Scan uses ~3 calls per stock. So ~1.5 stocks/sec.
        # We will process carefully.
        
        import yfinance as yf
        import time
        import pandas as pd
        
        total_processed = 0
        deep_scan_count = 0
        
        for i in range(0, len(universe), BATCH_SIZE):
            batch = universe[i:i+BATCH_SIZE]
            print(f"\n[BATCH] Processing {i} to {i+len(batch)}...")
            
            # C. Fast Technical Filter (YF Batch - Free/Cheap)
            survivors = []
            try:
                # Download batch data efficiently
                data = yf.download(batch, period="1y", interval="1d", group_by='ticker', progress=False, threads=True)
                
                for ticker in batch:
                    try:
                        # Handle MultiIndex vs Single
                        if len(batch) > 1:
                            if ticker not in data.columns.levels[0]: continue
                            df = data[ticker]
                        else:
                            df = data
                            
                        if df.empty or len(df) < 150: continue
                        
                        # Trend Check: Price > SMA150
                        # Calculate minimal technicals here to save FMP calls
                        close = df['Close'].iloc[-1]
                        sma150 = df['Close'].rolling(window=150).mean().iloc[-1]
                        
                        if pd.isna(close) or pd.isna(sma150): continue
                        
                        # Apply Iron Dome Technical Filter LOCALLY
                        # If price < sma150, we reject immediately without asking FMP
                        # (Unless Regime is BEAR, but let's stick to Trend Following for filtering)
                        if float(close) > float(sma150):
                            survivors.append(ticker)
                            
                    except Exception:
                        continue
            except Exception as e:
                print(f"  [BATCH ERROR] YF Download failed: {e}")
                continue
            
            print(f"  -> Survivors (Trend Positive): {len(survivors)}/{len(batch)}")
            
            # D. Deep Sentient Scan (FMP Heavy)
            for ticker in survivors:
                try:
                    # Rate Limit Enforcer
                    # We do ~3 calls per ticker.
                    # We pause 0.5s per ticker to stay safe ~120 stocks/min (360 calls/min) - slightly aggressive?
                    # Let's do 1.0s to be strictly safe (<180 calls/min).
                    time.sleep(1.0) 
                    
                    setup = self.signal_engine.analyze_ticker(ticker, regime)
                    deep_scan_count += 1
                    
                    if not setup.is_valid:
                        # print(f"  [REJECT] {ticker}: {setup.rejection_reason}")
                        continue
                        
                    # Apply AI Weights
                    weighted_sum = 0
                    total_weight = 0
                    
                    for lens, lens_score in setup.lens_scores.items():
                        w = weights.get(lens, 1.0)
                        lens_score.weight = w
                        weighted_sum += lens_score.score * w
                        total_weight += w
                    
                    # Normalize to 0-100
                    if total_weight > 0:
                        setup.final_score = weighted_sum / total_weight
                    else:
                        setup.final_score = 0
                    
                    if setup.final_score > 75:
                        print(f"  [CANDIDATE] {ticker} | Score: {setup.final_score:.1f}")
                        candidates.append(setup)
                except Exception as e:
                    print(f"  [ERROR] {ticker}: {e}")
            
            # Checkpoint
            if deep_scan_count > 0 and deep_scan_count % 50 == 0:
                print("  [LIMIT] Pausing 10s to cool down API...")
                time.sleep(10)

        # 4. PORTFOLIO OPTIMIZATION (Layer 4)
        top_picks = sorted(candidates, key=lambda x: x.final_score, reverse=True)
        top_picks = self.portfolio_manager.filter_for_diversification(top_picks)
        
        # Limit to Top 10
        top_10 = top_picks[:10]
        
        # 5. EXECUTION & MEMORY (Layer 5)
        print(f"\n[EXECUTION] Storing {len(top_10)} setups to Database...")
        for setup in top_10:
            self.save_setup(setup, safety)

        print("[SYSTEM] Cycle Complete.")

    def save_setup(self, setup: StockSetup, safety: SafetyStatus):
        """
        Saves to 'sniper_signals' and 'sentient_memory'.
        """
        # 1. Save to Signal Table (for Dashboard)
        signal_data = {
            "ticker": setup.ticker,
            "entry_price": setup.price,
            "confidence_score": setup.final_score,
            "reasons": f"Regime: {setup.regime.name}",
            "status": "OPEN",
            "raw_features": {
                "lens_scores": {k.name: v.score for k, v in setup.lens_scores.items()},
                "weights_used": {k.name: v.weight for k, v in setup.lens_scores.items()}
            }
        }
        self.supabase.table("sniper_signals").insert(signal_data).execute()
        
        # 2. Save to Sentient Memory (for Training)
        memory_data = {
            "ticker": setup.ticker,
            "score_quant": setup.lens_scores[Lens.QUANT].score,
            "score_oracle": setup.lens_scores[Lens.ORACLE].score,
            "score_hunter": setup.lens_scores[Lens.HUNTER].score,
            "score_chartist": setup.lens_scores[Lens.CHARTIST].score,
            "final_score": setup.final_score,
            "regime_at_entry": setup.regime.name,
            "outcome_label": "PENDING"
        }
        self.supabase.table("sentient_memory").insert(memory_data).execute()
        
        print(f"  -> Saved {setup.ticker}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="Wipe all memory before running")
    args = parser.parse_args()
    
    bot = SentientSniperBot()
    if args.reset:
        bot.reset_system()
    
    bot.run_daily_cycle()
