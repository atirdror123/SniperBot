import os
import pandas as pd
import yfinance as yf
from scanner_logic import SniperScorer
from datetime import datetime, timedelta
import time

# --- Configuration ---
SCAN_DATE = "2024-06-01"  # 6 months ago (approx)
HOLD_PERIOD_DAYS = 90     # 3 months
TARGET_PROFIT = 0.05      # 5%
STOP_LOSS = -0.10         # 10% (Optional, but good for realism)
SCORE_THRESHOLD = 75      # Only buy if score > 75

def run_backtest():
    print(f"--- Starting Backtest Engine ---")
    print(f"Scan Date: {SCAN_DATE}")
    print(f"Target Profit: {TARGET_PROFIT*100}% within {HOLD_PERIOD_DAYS} days")
    
    # 1. Initialize Scorer
    scorer = SniperScorer()
    # Disable AI to speed up backtest and save costs (logic already skips it if data is passed, but good to be sure)
    scorer.ai_enabled = False 
    
    # 2. Define Universe (S&P 500 Tickers - Limited set for speed if needed, or full)
    # Let's try to get a decent sample. Mocks or a hardcoded list for reliability.
    # We'll use a hardcoded list of diverse stocks to verify logic without fetching 500 tickers.
    tickers = [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", # Tech
        "JPM", "BAC", "V", # Financial
        "JNJ", "PFE", "LLY", # Healthcare
        "XOM", "CVX", # Energy
        "PG", "KO", # Consumer Defensive
        "BA", "CAT", # Industrial
        "AMD", "INTC", "QCOM", "CSCO"
    ]
    
    print(f"Universe Size: {len(tickers)}")
    
    # 3. Fetch Data Batch
    # We need data from (Scan Date - 1 Year) to (Scan Date + 90 Days)
    scan_dt = datetime.strptime(SCAN_DATE, "%Y-%m-%d")
    start_dt = scan_dt - timedelta(days=400) # Buffer for 200 SMA
    end_dt = scan_dt + timedelta(days=HOLD_PERIOD_DAYS + 10)
    
    print(f"Fetching Data: {start_dt.date()} to {end_dt.date()}...")
    
    data = yf.download(tickers, start=start_dt, end=end_dt, group_by='ticker', progress=True, auto_adjust=True, threads=True)
    
    trades = []
    
    # 4. Run Simulation
    for ticker in tickers:
        try:
            # Handle MultiIndex
            if ticker not in data.columns.levels[0]:
                print(f"No data for {ticker}")
                continue
                
            df = data[ticker].copy()
            
            if df.empty:
                continue
            
            # Slice Data for Scanner Input (Up to Scan Date)
            # We want the 'Close' of Scan Date to be the LAST row the scanner sees.
            input_df = df[df.index <= SCAN_DATE]
            
            if input_df.empty or len(input_df) < 200:
                # print(f"Not enough history for {ticker}")
                continue
            
            # Run Logic
            result = scorer.analyze_stock(ticker, data=input_df)
            score = result['final_score']
            
            if score >= SCORE_THRESHOLD:
                # BUY SIGNAL
                entry_price = input_df['Close'].iloc[-1]
                entry_date = input_df.index[-1]
                
                print(f"  [BUY] {ticker} | Score: {score} | Price: {entry_price:.2f} | Date: {entry_date.date()}")
                
                # Check Outcome (Look forward 90 days)
                future_df = df[df.index > SCAN_DATE]
                future_df = future_df[future_df.index <= (scan_dt + timedelta(days=HOLD_PERIOD_DAYS)).strftime("%Y-%m-%d")]
                
                if future_df.empty:
                    print(f"    Warning: No future data for {ticker}")
                    outcome = "Unknown"
                    pnl = 0
                else:
                    # Check if High hit Target
                    target_price = entry_price * (1 + TARGET_PROFIT)
                    max_price = future_df['High'].max()
                    
                    if max_price >= target_price:
                        outcome = "WIN"
                        pnl = TARGET_PROFIT
                        # Find date it hit
                        hit_date = future_df[future_df['High'] >= target_price].index[0]
                        days_held = (hit_date - entry_date).days
                        print(f"    >>> WIN! Hit {max_price:.2f} on {hit_date.date()} ({days_held} days)")
                    else:
                        # Check stop loss? Or just final price?
                        # Let's just check final price of period for simple PnL if no win
                        final_price = future_df['Close'].iloc[-1]
                        pnl = (final_price - entry_price) / entry_price
                        outcome = "LOSS" if pnl < 0 else "STAGNANT"
                        print(f"    FAIL. Max: {max_price:.2f}. Final: {final_price:.2f} ({pnl*100:.2f}%)")
                
                trades.append({
                    'ticker': ticker,
                    'score': score,
                    'outcome': outcome,
                    'pnl': pnl
                })
                
        except Exception as e:
            print(f"Error checking {ticker}: {e}")
            
    # 5. Summary
    if not trades:
        print("\nNo trades generated.")
        return
        
    print("\n" + "="*40)
    print("BACKTEST RESULTS")
    print("="*40)
    
    total_trades = len(trades)
    wins = len([t for t in trades if t['outcome'] == 'WIN'])
    win_rate = (wins / total_trades) * 100
    avg_pnl = pd.DataFrame(trades)['pnl'].mean() * 100
    
    print(f"Total Trades: {total_trades}")
    print(f"Wins: {wins}")
    print(f"Win Rate: {win_rate:.1f}%")
    print(f"Avg PnL: {avg_pnl:.2f}%")
    print("="*40)

if __name__ == "__main__":
    run_backtest()
