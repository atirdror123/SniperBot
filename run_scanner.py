import os
import time
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

def save_signal(supabase: Client, ticker: str, entry_price: float, score: int, reasons: str):
    """Saves a signal to Supabase"""
    try:
        data = {
            'ticker': ticker,
            'entry_price': entry_price,
            'confidence_score': score,
            'reasons': reasons,
            'status': 'OPEN' # Using 'OPEN' to match database constraint (user asked for 'new' but schema enforces OPEN/CLOSED)
        }
        supabase.table('sniper_signals').insert(data).execute()
        return True
    except Exception as e:
        print(f"  Error saving {ticker} to DB: {e}")
        return False

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
    total_saved = 0
    
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
        
        # 4. Deep Sniper Analysis
        batch_saved = 0
        for ticker, fast_close in survivors:
            try:
                result = scorer.analyze_stock(ticker)
                score = result.get('final_score', 0)
                
                if score > SCORE_THRESHOLD:
                    # Use the entry price from deep analysis (more recent/accurate) or fallback to fast filter close
                    # The scorer doesn't return entry_price explicitly in the dict, but we can get it from yfinance history inside scorer
                    # Actually, scorer returns 'details' and 'final_score'.
                    # We need to fetch price again or use the one we have.
                    # To be precise, let's use the one from the fast filter as 'entry_price' for now, 
                    # or better, fetch it quickly if needed. 
                    # But wait, the user instructions say: "Read entry_price from the returned data."
                    # The `SniperScorer.analyze_stock` returns `{'ticker': ..., 'final_score': ..., 'details': ...}`.
                    # It does NOT return `entry_price`.
                    # I should probably update `SniperScorer`? No, "DO NOT modify scanner_logic.py".
                    # So I must get entry_price separately.
                    # I will use the `fast_close` from the batch download.
                    
                    if save_signal(supabase, ticker, fast_close, score, result['details']):
                        batch_saved += 1
                        print(f"    >>> SAVED: {ticker} (Score: {score})")
                        
            except Exception as e:
                print(f"    Error analyzing {ticker}: {e}")
                continue
        
        total_saved += batch_saved
        print(f"  Batch Summary: {len(batch)} scanned -> {len(survivors)} survivors -> {batch_saved} saved")
        
        # Sleep to be nice to API
        time.sleep(1)

    print("\n" + "="*60)
    print("SCAN COMPLETE")
    print(f"Total Scanned: {total_tickers}")
    print(f"Total Survivors: {total_survivors}")
    print(f"Total Saved: {total_saved}")
    print("="*60)

if __name__ == "__main__":
    run_scanner()
