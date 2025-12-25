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
from email_service import send_daily_recap
from discord_service import send_scan_report

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
        print("\n[SYSTEM] STARTING DAILY CYCLE...", flush=True)
        print("="*50, flush=True)
        print(f"SENTIENT SNIPER - DAILY CYCLE - {datetime.now()}", flush=True)
        print("="*50, flush=True)

        # [STATUS BEACON] - Notify DB we are alive immediately
        try:
            self.supabase.table("system_status").upsert({"key": "scan_status", "value": "STARTING..."}).execute()
        except: pass

        deep_scan_count = 0
        candidates = []
        saved_count = 0 
        
        try:
            # 1. IRON DOME (Layer 1)
            safety, regime = self.iron_dome.check_market_environment()
            if safety == SafetyStatus.ANGER:
                print("[IRON DOME] KILL SWITCH ENGAGED. ABORTING SCAN.")
                self.supabase.table("system_status").upsert({"key": "scan_status", "value": "ABORTED_KILL_SWITCH"}).execute()
                return

            # 2. GET WEIGHTS (Layer 3 - Brain)
            weights = self.brain.get_weights(regime)
            print(f"[BRAIN] Active Weights for {regime.name}: {weights}")
            
            # 3. SCAN & SCORE (Layer 2)
            # A. FMP/NASDAQ Screener
            print("[SCANNER] Fetching Universe...")
            self.supabase.table("system_status").upsert({"key": "scan_status", "value": "FETCHING_UNIVERSE"}).execute()
            
            # Check if Testing
            is_test = getattr(self, "test_mode", False)
            limit = 50 if is_test else 10000
            
            universe = self.ingestor.fetch_universe(limit=limit)
            print(f"[SCANNER] Universe Size: {len(universe)} stocks (Test Mode: {is_test}).")
            
            if not universe:
                print("[CRITICAL] UNIVERSE EMPTY. ABORTING.")
                self.supabase.table("system_status").upsert({"key": "scan_status", "value": "FAILED_EMPTY_UNIVERSE"}).execute()
                # We save a failed summary so we know what happened
                self.supabase.table("scan_summaries").upsert({
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "scanned_count": 0,
                    "candidates_count": 0,
                    "saved_count": 0,
                    "note": "FAILED: Universe fetch returned 0 stocks."
                }).execute()
                return

            self.supabase.table("system_status").upsert({"key": "scan_status", "value": "SCANNING"}).execute()

            # B. Batch Processing
            BATCH_SIZE = 100
            import yfinance as yf
            import time
            import pandas as pd
            
            total_processed = 0
            
            for i in range(0, len(universe), BATCH_SIZE):
                batch = universe[i:i+BATCH_SIZE]
                print(f"\n[BATCH] Processing {i} to {i+len(batch)}...")
                
                # C. Fast Technical Filter (YF Batch - Free/Cheap)
                survivors = []
                try:
                    # Download batch data efficiently
                    data = yf.download(batch, period="1y", interval="1d", group_by='ticker', progress=False, threads=True, auto_adjust=True)
                    
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
                            trend_ok = float(close) > float(sma150)
                            
                            # Liquidity Check (Price > $2, Vol*Price > $5M)
                            # We calculate simple avg volume (20 day)
                            avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
                            liquidity_ok = self.iron_dome.check_liquidity(ticker, float(close), float(avg_vol))
                            
                            if trend_ok and liquidity_ok:
                                survivors.append(ticker)
                                
                        except Exception:
                            continue
                except Exception as e:
                    print(f"  [BATCH ERROR] YF Download failed: {e}")
                    continue
                
                print(f"  -> Survivors (Trend Positive): {len(survivors)}/{len(batch)}")
                
                # D. Deep Sentient Scan (FMP Heavy)
                for ticker in survivors:
                    # Get correct DF slice for this ticker
                    ticker_df = data[ticker] if len(batch) > 1 else data
                    
                    try:
                        # Heartbeat for User Reassurance
                        print(f"  [SCAN] {ticker} ({deep_scan_count+1}/{len(survivors)} in batch)...")
                        
                        # Rate Limit Optimization
                        time.sleep(1.0) 
                        
                        setup = self.signal_engine.analyze_ticker(ticker, regime, df=ticker_df) 
                        deep_scan_count += 1
                        
                        # Heartbeat for User Reassurance
                        if deep_scan_count % 5 == 0:
                            print(f"  [ALIVE] Scanned {deep_scan_count} / {len(survivors)} potential targets... (Candidates found so far: {len(candidates)})")
                        
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
                        
                        # Threshold Reverted to 75 (Strict Quality)
                        if setup.final_score >= 75:
                            print(f"  [CANDIDATE] {ticker} | Score: {setup.final_score:.1f}")
                            candidates.append(setup)
                            
                            # [WAIT-AND-SAVE] logic applies

                    except Exception as e:
                        print(f"  [ERROR] {ticker}: {e}")
                
                # Checkpoint
                if deep_scan_count > 0 and deep_scan_count % 100 == 0:
                    print("  [LIMIT] Pausing 2s to cool down API...")
                    time.sleep(2)

            # [STATUS] Cycle Complete (Normally)
            try:
                self.supabase.table("system_status").upsert({"key": "scan_status", "value": "COMPLETED"}).execute()
            except: pass


        except KeyboardInterrupt:
            print("\n[SYSTEM] Interrupted by User. Saving progress...")
            self.supabase.table("system_status").upsert({"key": "scan_status", "value": "INTERRUPTED"}).execute()

        except Exception as e:
            print(f"\n[CRITICAL ERROR] Main Loop Crashed: {e}")
            self.supabase.table("system_status").upsert({"key": "scan_status", "value": f"CRASH: {str(e)[:50]}"}).execute()
            # Try to log detailed error to summary note?
            
        finally:
            print("\n[Shutting Down] Saving results found so far...")
            
            # [FILTER] STRICT TOP 10 LOGIC
            # Sort all candidates by score (Highest first)
            candidates.sort(key=lambda x: x.final_score, reverse=True)
            
            # Keep strictly top 10
            print(f"[SYSTEM] Found {len(candidates)} candidates. Filtering for Top 10...")
            final_list = candidates[:10]
            
            # Save them now
            saved_count = 0
            for setup in final_list:
                try:
                    self.save_setup(setup, setup.safety_check)
                    saved_count += 1
                except: pass

            # Update candidates list for notification to only include what we actually saved
            candidates = final_list
            
            # [SUMMARY] Log Daily Stats
            try:
                today_str = datetime.now().strftime("%Y-%m-%d")
                
                # Re-fetch official count
                # saved_res = self.supabase.table("sniper_signals").select("id", count="exact").gte("created_at", today_str).execute()
                # saved_count = saved_res.count if saved_res.count is not None else len(saved_res.data)
                
                summary_data = {
                    "date": today_str,
                    "scanned_count": deep_scan_count,
                    "candidates_count": len(candidates),
                    "saved_count": saved_count
                }
                self.supabase.table("scan_summaries").upsert(summary_data).execute()
                print(f"[SUMMARY] Logged: Scanned {deep_scan_count}, Saved {saved_count}")
            except Exception as e:
                print(f"[ERROR] Failed to update summary: {e}")

            # [EMAIL] Notification
            if candidates:
                print(f"[NOTIFY] Sending alerts for {len(candidates)} signals...")
                try:
                    send_scan_report(candidates)
                except Exception as e:
                    print(f"Notify failed: {e}")

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
        
        # [DEDUPLICATION] Check if already exists for today
        try:
            today_start = datetime.now().strftime("%Y-%m-%d") + " 00:00:00"
            existing = self.supabase.table("sniper_signals") \
                .select("id") \
                .eq("ticker", setup.ticker) \
                .gte("created_at", today_start) \
                .execute()
            
            if existing.data and len(existing.data) > 0:
                print(f"  -> Skipping {setup.ticker} (Already saved today)")
                return
        except Exception as e:
            print(f"  [WARN] Dup check failed: {e}")

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
    parser.add_argument("--test", action="store_true", help="Run a small test batch (50 stocks)")
    args = parser.parse_args()
    
    bot = SentientSniperBot()
    bot.test_mode = args.test
    
    if args.reset:
        bot.reset_system()
    
    bot.run_daily_cycle()
