import time
import os
from dotenv import load_dotenv
from main_sentient import SentientSniperBot

load_dotenv()

def diagnose():
    print(f"[0.0s] Starting Diagnosis on AAPL...")
    start = time.time()
    
    # 1. Init
    try:
        bot = SentientSniperBot()
        print(f"[{time.time()-start:.2f}s] Bot Initialized.")
    except Exception as e:
        print(f"[FAIL] Init Error: {e}")
        return

    # 2. Analyze
    ticker = "AAPL"
    try:
        print(f"[{time.time()-start:.2f}s] Running Signal Engine...")
        # Get Regime correctly
        safety, regime = bot.iron_dome.check_market_environment()
        print(f"[{time.time()-start:.2f}s] Regime detected: {regime.name}")
        setup = bot.signal_engine.analyze_ticker(ticker, regime)
        print(f"[{time.time()-start:.2f}s] Analysis Complete. Score: {setup.final_score}")
        print(f"   -> Details: {setup.lens_scores}")
    except Exception as e:
        print(f"[FAIL] Analysis Error: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. Save (Mocking pipeline insertion)
    try:
        if setup.final_score > 0:
            print(f"[{time.time()-start:.2f}s] Attempting DB Save...")
            # Manual insert matching main_sentient.py logic
            data = {
                "ticker": setup.ticker,
                "entry_price": setup.price,
                "confidence_score": setup.final_score,
                "reasons": f"Use: Diagnosis",
                "status": "TEST",
                "raw_features": {}
            }
            bot.supabase.table("sniper_signals").insert(data).execute()
            print(f"[{time.time()-start:.2f}s] DB Save Success.")
        else:
            print("[SKIP] Score too low to save.")
    except Exception as e:
        print(f"[FAIL] DB Error: {e}")

    print(f"[{time.time()-start:.2f}s] Diagnosis DONE.")

if __name__ == "__main__":
    diagnose()
