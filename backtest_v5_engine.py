"""
Backtest V5 - Engine Verification
=================================
Uses the corrected AISignalEngine (v1 REST API) to score 3 stocks.
"""
import time
import json
from ai_signal_engine import AISignalEngine
import sys

STOCKS = ['NVDA', 'PLTR', 'AMD']

def run():
    print("="*60)
    print("BACKTEST V5: ENGINE VERIFICATION")
    print("="*60)
    
    engine = AISignalEngine()
    print(f"API URL: {engine.api_url[:60]}...", flush=True)
    
    for i, ticker in enumerate(STOCKS):
        print(f"\n[{i+1}/{len(STOCKS)}] Analyzing {ticker}...", flush=True)
        
        # We call score_stock directly (blocking)
        # It handles rate limits internally by sleeping if needed
        start = time.time()
        result = engine.score_stock(ticker)
        duration = time.time() - start
        
        print(f"  Duration: {duration:.1f}s")
        if result['success']:
            print(f"  ✅ SUCCESS!")
            print(f"     HUNTER: {result['hunter']} ({result['hunter_reason']})")
            print(f"     QUANT:  {result['quant']} ({result['quant_reason']})")
            print(f"     ORACLE: {result['oracle']} ({result['oracle_reason']})")
        else:
            print(f"  ❌ FAILED / PARTIAL")
            print(f"     HUNTER: {result['hunter']} ({result['hunter_reason']})")
            print(f"     QUANT:  {result['quant']} ({result['quant_reason']})")
            print(f"     ORACLE: {result['oracle']} ({result['oracle_reason']})")
            
        # Extra safety sleep between stocks
        time.sleep(5)

if __name__ == "__main__":
    run()
