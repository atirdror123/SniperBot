import pandas as pd
# Read and display results
try:
    res = pd.read_csv('ai_backtest_results.csv')
    print("=== BACKTEST RESULTS ===")
    print(f"Stocks: {len(res)}")
    print(f"Winners: {len(res[res['is_winner']])}")
    print(f"Avg Return: {res['forward_return'].mean():.1f}%")
    print(f"\nAI Sentiment range: {res['ai_sentiment'].min()} to {res['ai_sentiment'].max()}")
    print(f"AI Sentiment mean: {res['ai_sentiment'].mean():.1f}")
    
    print("\n=== SIGNAL ANALYSIS ===")
    ana = pd.read_csv('ai_signal_analysis.csv')
    for _, r in ana.iterrows():
        print(f"{r['signal']:<15}: corr={r['correlation']:.3f if pd.notna(r['correlation']) else 'N/A'}, diff={r['diff']:.1f}")
    
    print("\n=== SAMPLE DATA ===")
    print(res[['ticker', 'forward_return', 'ai_sentiment', 'ai_exec_buys']].head(10).to_string())
except Exception as e:
    print(f"Error: {e}")
