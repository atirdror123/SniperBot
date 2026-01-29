import pandas as pd
with open('final_results.txt', 'w') as f:
    df = pd.read_csv('yahoo_signal_analysis.csv')
    f.write("YAHOO FINANCE BACKTEST - SIGNAL ANALYSIS\n")
    f.write("="*60 + "\n")
    f.write(df.to_string() + "\n\n")
    
    br = pd.read_csv('yahoo_backtest_results.csv')
    f.write(f"\nTotal stocks: {len(br)}\n")
    f.write(f"Winners: {len(br[br['is_winner']])}\n")
    f.write(f"Win Rate: {len(br[br['is_winner']])/len(br)*100:.1f}%\n")
    f.write(f"Avg Return: {br['forward_return'].mean():.1f}%\n")
print("Saved to final_results.txt")
