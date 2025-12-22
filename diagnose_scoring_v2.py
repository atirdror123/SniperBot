from main_sentient import SentientSniperBot
from primitives import MarketRegime

bot = SentientSniperBot()
print("--- DIAGNOSING ENHANCED SCORING ---")

tickers = ["AAPL", "NVDA"]

for t in tickers:
    print(f"\nAnalyzing {t}...")
    setup = bot.signal_engine.analyze_ticker(t, MarketRegime.BULL, df=None)
    
    print(f"Score: {setup.final_score}")
    print(f"Lenses: {setup.lens_scores.keys()}")
    for lens, score_obj in setup.lens_scores.items():
        print(f"  - {lens.name}: {score_obj.score} (Active: {score_obj.score > 0})")
        # Check details for fallback usage
        if "details" in score_obj.__dict__:
             print(f"    Details: {score_obj.details}")

    if setup.final_score >= 75:
        print("-> PASS Candidate")
    else:
        print("-> REJECT (Score < 75)")
