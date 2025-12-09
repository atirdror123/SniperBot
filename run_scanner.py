import os
import time
from datetime import datetime, timezone, timedelta
import pandas as pd
import requests
import yfinance as yf
from dotenv import load_dotenv
from supabase import create_client, Client
from scanner_logic import SniperScorer
from io import StringIO

# Load environment variables
load_dotenv()

# Configuration
BATCH_SIZE = 300
SCORE_THRESHOLD = 75
MIN_PRICE = 2.0
MIN_DOLLAR_VOLUME = 5_000_000

def get_all_tickers():
    """
    Fetches a list of US tickers.
    Attempts to use NASDAQ API as a fallback since stocksymbol requires an API key.
    """
    print("Fetching universe of US stocks...")
    tickers = []
    
    # Method 1: NASDAQ API (Free, ~7000+ stocks)
    try:
        url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25&offset=0&download=true"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers)
        data = response.json()
        
        if data['data'] and data['data']['rows']:
            df = pd.DataFrame(data['data']['rows'])
            # The API returns 'symbol' column
            raw_tickers = df['symbol'].tolist()
            
            # Filter out warrants, preferreds, etc. (containing '.' or '-')
            tickers = [t for t in raw_tickers if '.' not in t and '-' not in t]
            
            # Remove any non-alpha characters just in case
            tickers = [t for t in tickers if t.isalpha()]
            
            print(f"Successfully fetched {len(tickers)} tickers from NASDAQ API.")
            return tickers
            
    except Exception as e:
        print(f"Warning: NASDAQ API fetch failed ({e}).")

    # Method 2: Fallback to S&P 500 if NASDAQ fails
    print("Falling back to S&P 500 list...")
    try:
        url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        tables = pd.read_html(StringIO(response.text))
        sp500_table = tables[1] # Usually index 1
        tickers = sp500_table['Symbol'].tolist()
        tickers = [str(t).replace('.', '-') for t in tickers] # S&P 500 uses '-' in yfinance
        # But we want to filter out '-' as per requirements? 
        # Requirement: "Filter out any symbol that contains "." or "-"".
        # So we should actually skip BRK.B etc.
        tickers = [t for t in tickers if '.' not in t and '-' not in t]
        print(f"Fetched {len(tickers)} tickers from S&P 500.")
        return tickers
    except Exception as e:
        print(f"Error fetching S&P 500: {e}")
        return []



def cleanup_todays_signals(supabase: Client):
    """
    Removes ALL 'OPEN' signals to ensure the dashboard only shows the latest batch.
    This guarantees strictly 10 active stocks at any time.
    """
    try:
        # Delete all signals with status='OPEN'
        # This is safer than date filtering because it clears the "Active Targets" view completely
        supabase.table('sniper_signals').delete().eq('status', 'OPEN').execute()
        print(f"  Cleaned up ALL existing OPEN signals to enforce strict limit.")
    except Exception as e:
        print(f"  Warning: Failed to cleanup signals: {e}")

def run_scanner():
    # Initialize Supabase
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
        return
    
    supabase: Client = create_client(url, key)
    scorer = SniperScorer()
    
    # 1. Universe
    tickers = get_all_tickers()
    if not tickers:
        print("No tickers found. Exiting.")
        return
    
    total_tickers = len(tickers)
    print(f"Universe size: {total_tickers} stocks")
    
    # 2. Batching
    total_survivors = 0
    all_qualified_stocks = []  # Store all stocks that pass threshold
    
    for i in range(0, total_tickers, BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (total_tickers + BATCH_SIZE - 1) // BATCH_SIZE
        
        print(f"\nProcessing Batch {batch_num}/{total_batches} ({len(batch)} tickers)...")
        
        # 3. Fast Filter
        survivors = []
        try:
            # Download data for batch
            # group_by='ticker' ensures we get a MultiIndex with Ticker as top level or second level depending on auto_adjust
            # auto_adjust=True simplifies columns to Open, High, Low, Close, Volume
            data = yf.download(batch, period="5d", interval="1d", group_by='ticker', progress=False, threads=True)
            
            if data.empty:
                print("  Warning: No data returned for batch.")
                continue
                
            # Iterate through tickers in the batch
            for ticker in batch:
                try:
                    # Handle MultiIndex: data[ticker] returns DataFrame with OHLCV
                    if ticker not in data.columns.levels[0]:
                        continue
                        
                    df = data[ticker]
                    if df.empty:
                        continue
                        
                    last_row = df.iloc[-1]
                    close = last_row['Close']
                    volume = last_row['Volume']
                    
                    # Check for NaN
                    if pd.isna(close) or pd.isna(volume):
                        continue
                        
                    # Filter Logic
                    if close >= MIN_PRICE and (close * volume) >= MIN_DOLLAR_VOLUME:
                        survivors.append((ticker, close))
                        
                except Exception:
                    continue
                    
        except Exception as e:
            print(f"  Error downloading batch: {e}")
            continue
            
        print(f"  Survivors: {len(survivors)}")
        total_survivors += len(survivors)
        
        # 4. Deep Sniper Analysis - collect all qualified stocks
        for ticker, fast_close in survivors:
            try:
                result = scorer.analyze_stock(ticker)
                score = result.get('final_score', 0)
                
                if score > SCORE_THRESHOLD:
                    # Store qualified stock with all details
                    all_qualified_stocks.append({
                        'ticker': ticker,
                        'entry_price': fast_close,
                        'score': score,
                        'details': result['details'],
                        'raw_features': result.get('raw_features', {}) # Capture raw features
                    })
                    print(f"    >>> QUALIFIED: {ticker} (Score: {score})")
                        
            except Exception as e:
                print(f"    Error analyzing {ticker}: {e}")
                continue
        
        print(f"  Batch Summary: {len(batch)} scanned -> {len(survivors)} survivors -> {len(all_qualified_stocks)} total qualified so far")
        
        # Sleep to be nice to API
        time.sleep(1)

    # 5. Select Top 10 Stocks by Score
    print("\n" + "="*60)
    print("FILTERING TOP 10 STOCKS")
    print("="*60)
    
    if not all_qualified_stocks:
        print("No stocks qualified (score > 75). Nothing to save.")
    else:
        # Sort by score descending and take top 10
        all_qualified_stocks.sort(key=lambda x: x['score'], reverse=True)
        top_10 = all_qualified_stocks[:10]
        
        print(f"Total Qualified: {len(all_qualified_stocks)}")
        
        # CLEANUP: Remove today's existing signals before saving new ones
        print("Cleaning up previous signals for today...")
        cleanup_todays_signals(supabase)
        
        # VERIFY CLEANUP (SAFEGUARD)
        try:
            # Check if any OPEN signals remain
            existing = supabase.table('sniper_signals').select('ticker', count='exact').eq('status', 'OPEN').execute()
            count = existing.count if existing.count is not None else len(existing.data)
            
            if count > 0:
                print(f"CRITICAL ERROR: Cleanup failed. Found {count} 'OPEN' signals still in DB.")
                print("Aborting save to prevent exceeding the 10-stock limit.")
                return
            else:
                print("  Cleanup verified. 0 OPEN signals remaining.")
        except Exception as e:
            print(f"Error verifying cleanup: {e}. Aborting for safety.")
            return
        
        print(f"Saving Top 10 Highest Scoring Stocks:")
        print("-" * 60)
        
        # Prepare batch data
        signals_data = []
        for stock in top_10:
            signals_data.append({
                'ticker': stock['ticker'],
                'entry_price': stock['entry_price'],
                'confidence_score': stock['score'],
                'reasons': stock['details'],
                'status': 'OPEN',
                'raw_features': stock['raw_features']
            })
            print(f"  Preparing: {stock['ticker']} - Score: {stock['score']}")

        # Batch Insert
        if signals_data:
            try:
                supabase.table('sniper_signals').insert(signals_data).execute()
                total_saved = len(signals_data)
                print(f"\nSuccessfully batch inserted {total_saved} stocks.")
            except Exception as e:
                print(f"\nCRITICAL ERROR: Batch insert failed: {e}")
                total_saved = 0
        else:
            total_saved = 0
        
        if len(all_qualified_stocks) > 10:
            print(f"\nNote: {len(all_qualified_stocks) - 10} additional qualified stocks were not saved (only top 10 saved)")

    print("\n" + "="*60)
    print("SCAN COMPLETE")
    print(f"Total Scanned: {total_tickers}")
    print(f"Total Survivors: {total_survivors}")
    print(f"Total Qualified: {len(all_qualified_stocks)}")
    print(f"Total Saved: {total_saved if all_qualified_stocks else 0}")
    print("="*60)

if __name__ == "__main__":
    run_scanner()
