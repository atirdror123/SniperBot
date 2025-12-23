from main_sentient import SentientSniperBot
from primitives import MarketRegime

# Must reload to pick up signal_engine changes if import cached, but standard python script start is fresh.
bot = SentientSniperBot()
print("--- VERIFYING BOOSTED SCORING ---")

tickers = ["AAPL", "NVDA"]

for t in tickers:
    print(f"\nScanning {t}...")
    try:
        setup = bot.signal_engine.analyze_ticker(t, MarketRegime.BULL, df=None)
        print(f"  Final Score: {setup.final_score:.2f}")
        for lens, obj in setup.lens_scores.items():
            print(f"    - {lens.name}: {obj.score}")
            
        if setup.final_score >= 75:
            print("  ✅ PASS (>= 75)")
        else:
            print("  ❌ FAIL (< 75)")
    except Exception as e:
        print(f"Error: {e}")
