
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

def clean_duplicates():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: Supabase credentials missing.")
        return

    supabase: Client = create_client(url, key)
    
    print("Fetching recent signals...")
    # Fetch last 24 hours (or just all open signals to be safe)
    response = supabase.table("sniper_signals").select("*").order("created_at", desc=True).limit(500).execute()
    data = response.data
    
    if not data:
        print("No signals found.")
        return

    print(f"Analyzing {len(data)} signals for duplicates...")
    
    seen_tickers = {}
    duplicates_to_delete = []

    # Iterate through data. Since it's ordered by desc, the first one we see is the latest.
    for signal in data:
        ticker = signal['ticker']
        # Check if it was created today (simple check)
        created_at = signal['created_at'][:10] # YYYY-MM-DD
        
        # Only care about today's duplicates for now or just generic recent duplicates
        # Actually, let's just deduplicate by ticker for the recent batch.
        # If we see the ticker again, it's a duplicate (older version)
        
        if ticker in seen_tickers:
            duplicates_to_delete.append(signal['id'])
            print(f"  [DUPLICATE] {ticker} (ID: {signal['id']}) - Keeping {seen_tickers[ticker]}")
        else:
            seen_tickers[ticker] = signal['id']

    if duplicates_to_delete:
        print(f"\nFound {len(duplicates_to_delete)} duplicates. Deleting...")
        for dup_id in duplicates_to_delete:
            try:
                supabase.table("sniper_signals").delete().eq("id", dup_id).execute()
                print(f"  Deleted ID: {dup_id}")
            except Exception as e:
                print(f"  Error deleting {dup_id}: {e}")
        print("Cleanup complete.")
    else:
        print("No duplicates found.")

if __name__ == "__main__":
    clean_duplicates()
