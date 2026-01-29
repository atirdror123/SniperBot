"""
Quick sample test to estimate pressure cooker pass rate.
Uses S&P 500 as a sample instead of full universe for speed.
"""
import os
import sys
import warnings
from dotenv import load_dotenv

# Suppress yfinance warnings
warnings.filterwarnings('ignore')

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yfinance as yf
import pandas as pd
from pressure_cooker import pressure_cooker_filter

# S&P 500 sample (top 100 most liquid)
SP500_SAMPLE = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK-B', 'UNH', 'JNJ',
    'XOM', 'JPM', 'V', 'PG', 'MA', 'HD', 'CVX', 'MRK', 'ABBV', 'LLY',
    'PEP', 'KO', 'COST', 'AVGO', 'TMO', 'MCD', 'WMT', 'CSCO', 'ACN', 'DHR',
    'ABT', 'VZ', 'ADBE', 'NKE', 'CRM', 'CMCSA', 'INTC', 'TXN', 'PM', 'NEE',
    'BMY', 'QCOM', 'UPS', 'RTX', 'T', 'HON', 'AMGN', 'IBM', 'LOW', 'GS',
    'AMD', 'SPGI', 'CAT', 'ELV', 'SBUX', 'DE', 'BLK', 'INTU', 'MDLZ', 'GILD',
    'ISRG', 'ADP', 'ADI', 'PLD', 'BKNG', 'REGN', 'CB', 'NOW', 'CI', 'MMC',
    'MO', 'ZTS', 'VRTX', 'DUK', 'TJX', 'SO', 'CME', 'SCHW', 'SYK', 'PGR',
    'AON', 'EOG', 'LRCX', 'CSX', 'NOC', 'BSX', 'CL', 'BDX', 'ITW', 'WM',
    'FI', 'MU', 'APD', 'ICE', 'FCX', 'NSC', 'SHW', 'ETN', 'MCK', 'KLAC'
]

def get_stock_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch stock data from Yahoo Finance."""
    try:
        df = yf.download(ticker, period=period, progress=False, auto_adjust=True)
        if df.empty:
            return pd.DataFrame()
        
        # Flatten multi-index if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        return df
    except:
        return pd.DataFrame()

def run_sample_test():
    """Run pressure cooker on S&P 500 sample to estimate pass rate."""
    print("=" * 60)
    print("PRESSURE COOKER SAMPLE TEST")
    print(f"Testing {len(SP500_SAMPLE)} S&P 500 stocks")
    print("=" * 60)
    
    passed = []
    failed_data = 0
    failed_filter = 0
    
    for i, ticker in enumerate(SP500_SAMPLE):
        if i % 20 == 0:
            print(f"Progress: {i}/{len(SP500_SAMPLE)}")
        
        try:
            df = get_stock_data(ticker)
            if df.empty or len(df) < 50:
                failed_data += 1
                continue
            
            result = pressure_cooker_filter(df, ticker)
            
            if result['passes']:
                passed.append(ticker)
                print(f"  ✓ {ticker} PASSED | RSI={result['metrics']['rsi']:.0f} RVOL={result['metrics']['rvol']:.1f}x")
            else:
                failed_filter += 1
        
        except Exception as e:
            failed_data += 1
    
    # Results
    print("\n" + "=" * 60)
    print("RESULTS")
    print("=" * 60)
    print(f"Tested:        {len(SP500_SAMPLE)}")
    print(f"Failed Data:   {failed_data}")
    print(f"Failed Filter: {failed_filter}")
    print(f"PASSED:        {len(passed)}")
    
    pass_rate = len(passed) / (len(SP500_SAMPLE) - failed_data) * 100 if (len(SP500_SAMPLE) - failed_data) > 0 else 0
    print(f"\nPass Rate: {pass_rate:.1f}%")
    
    if passed:
        print(f"\nPassed stocks: {', '.join(passed)}")
    
    # Extrapolate to full universe
    print("\n" + "=" * 60)
    print("EXTRAPOLATION TO FULL UNIVERSE")
    print("=" * 60)
    for universe_size in [3000, 5000, 8000]:
        estimated = int(universe_size * pass_rate / 100)
        print(f"Universe {universe_size:,}: ~{estimated} stocks would pass")
    
    # Save results
    with open('sample_test_results.txt', 'w') as f:
        f.write(f"Sample Size: {len(SP500_SAMPLE)}\n")
        f.write(f"Passed: {len(passed)}\n")
        f.write(f"Pass Rate: {pass_rate:.1f}%\n")
        f.write(f"Passed Stocks: {', '.join(passed)}\n")
    
    print("\n✅ Results saved to sample_test_results.txt")

if __name__ == "__main__":
    run_sample_test()
