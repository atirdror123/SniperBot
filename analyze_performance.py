"""
Phase 0: Data Mining - Winner Profile Analysis
Uses small-batch Yahoo Finance calls (10 at a time) for reliability.
Entry data comes from our existing Supabase database.
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import yfinance as yf
import pandas as pd
import numpy as np
import time

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client


def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def batch_quotes(tickers, batch_size=10):
    """Get current prices in small batches to avoid timeouts."""
    prices = {}
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        print(f"  Batch {i//batch_size + 1}/{(len(tickers)-1)//batch_size + 1}: {len(batch)} tickers...")
        
        try:
            data = yf.download(batch, period="1d", progress=False, threads=True)
            
            if len(batch) == 1:
                if not data.empty:
                    prices[batch[0]] = float(data['Close'].iloc[-1])
            else:
                for ticker in batch:
                    try:
                        price = float(data['Close'][ticker].iloc[-1])
                        if not pd.isna(price):
                            prices[ticker] = price
                    except:
                        pass
            
            time.sleep(0.5)  # Rate limit
        except Exception as e:
            print(f"    Error: {e}")
    
    return prices


def run_analysis():
    """Main analysis pipeline."""
    print("=" * 60)
    print("PHASE 0: DATA MINING - Winner Profile Analysis")
    print("=" * 60)
    
    # Step 1: Fetch signals from DB (WE HAVE THIS DATA!)
    supabase = get_supabase()
    response = supabase.table("sniper_signals").select("*").execute()
    signals = response.data
    
    if not signals:
        print("No signals found.")
        return
    
    df = pd.DataFrame(signals)
    tickers = df['ticker'].unique().tolist()
    print(f"\n📊 Found {len(signals)} signals ({len(tickers)} unique tickers)")
    
    # Step 2: Get current prices (small batches)
    print("\n🔄 Fetching current prices (small batches)...")
    prices = batch_quotes(tickers, batch_size=10)
    print(f"\n  ✓ Got prices for {len(prices)} tickers")
    
    # Step 3: Calculate performance using DB entry data
    print("\n📈 Calculating performance...")
    results = []
    
    for _, row in df.iterrows():
        ticker = row['ticker']
        entry_price = row.get('entry_price', 0)
        entry_date = str(row.get('created_at', ''))[:10]
        
        if not entry_price or ticker not in prices:
            continue
        
        current_price = prices[ticker]
        pct_change = (current_price - entry_price) / entry_price * 100
        
        results.append({
            'ticker': ticker,
            'entry_date': entry_date,
            'entry_price': entry_price,
            'current_price': current_price,
            'pct_change': pct_change,
            'raw_features': row.get('raw_features', {})
        })
    
    perf_df = pd.DataFrame(results)
    
    if perf_df.empty:
        print("No performance data.")
        return
    
    # Step 4: Top 10 Winners
    print(f"\n🏆 TOP 10 WINNERS:")
    print("-" * 50)
    
    winners = perf_df.nlargest(10, 'pct_change')
    
    for _, row in winners.iterrows():
        emoji = "🟢" if row['pct_change'] > 0 else "🔴"
        print(f"  {emoji} {row['ticker']:6} | Entry: ${row['entry_price']:.2f} | "
              f"Now: ${row['current_price']:.2f} | {row['pct_change']:+.1f}%")
    
    # Step 5: Analyze winners' lens scores from our EXISTING DATA
    print("\n" + "=" * 60)
    print("REVERSE ENGINEERING: Winner Profile (from DB data)")
    print("=" * 60)
    
    winner_profiles = []
    
    for _, row in winners.iterrows():
        raw = row.get('raw_features', {})
        if raw and 'lens_scores' in raw:
            lens = raw['lens_scores']
            winner_profiles.append({
                'ticker': row['ticker'],
                'pct_gain': row['pct_change'],
                'quant': lens.get('QUANT', 0),
                'oracle': lens.get('ORACLE', 0),
                'hunter': lens.get('HUNTER', 0),
                'chartist': lens.get('CHARTIST', 0)
            })
            print(f"  {row['ticker']:6} | +{row['pct_change']:.1f}% | "
                  f"Q:{lens.get('QUANT', 0)} O:{lens.get('ORACLE', 0)} "
                  f"H:{lens.get('HUNTER', 0)} C:{lens.get('CHARTIST', 0)}")
    
    if winner_profiles:
        wp_df = pd.DataFrame(winner_profiles)
        
        print("\n📋 WINNER LENS SCORE AVERAGES:")
        print("-" * 40)
        print(f"  QUANT:    {wp_df['quant'].mean():.1f}")
        print(f"  ORACLE:   {wp_df['oracle'].mean():.1f}")
        print(f"  HUNTER:   {wp_df['hunter'].mean():.1f}")
        print(f"  CHARTIST: {wp_df['chartist'].mean():.1f}")
    
    # Step 6: Overall Performance Stats
    print("\n" + "=" * 60)
    print("📊 OVERALL PERFORMANCE STATS")
    print("=" * 60)
    
    total = len(perf_df)
    winners_count = len(perf_df[perf_df['pct_change'] > 0])
    losers_count = len(perf_df[perf_df['pct_change'] < 0])
    win_rate = winners_count / total * 100 if total > 0 else 0
    
    print(f"  Total Picks:  {total}")
    print(f"  Winners:      {winners_count} ({win_rate:.1f}%)")
    print(f"  Losers:       {losers_count}")
    print(f"  Avg Return:   {perf_df['pct_change'].mean():.1f}%")
    print(f"  Best:         {perf_df['pct_change'].max():.1f}%")
    print(f"  Worst:        {perf_df['pct_change'].min():.1f}%")
    
    print("\n✅ PHASE 0 COMPLETE")
    
    return perf_df, winners


if __name__ == "__main__":
    run_analysis()
