from main_sentient import SentientSniperBot
from datetime import datetime

print("--- MINI SCAN TEST (10 Stocks) ---")
bot = SentientSniperBot()
# Force test mode to limit universe to 10 stocks for speed
bot.test_mode = True 

# Overwrite tickers to scan with a mix of big names to ensure data flow
bot.tickers_to_scan = ["AAPL", "NVDA", "TSLA", "MSFT", "AMD", "GOOGL", "AMZN", "META", "JPM", "BAC"]

print(f"[TEST] Starting Cycle at {datetime.now()}")
try:
    bot.run_daily_cycle()
    print("[TEST] Cycle Completed Successfully.")
except Exception as e:
    print(f"[TEST] Cycle Failed: {e}")
