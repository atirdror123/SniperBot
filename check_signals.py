import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Force unbuffered stdout
sys.stdout.reconfigure(line_buffering=True)

load_dotenv()

def check_saved_signals():
    print("Starting signal check...")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: Missing keys")
        return
    
    try:
        supabase = create_client(url, key)
        print("Connected to Supabase.")
        
        # Fetch all signals
        response = supabase.table('sniper_signals').select('*').order('created_at', desc=True).execute()
        signals = response.data
        
        print(f"Total signals found: {len(signals)}")
        
        if not signals:
            print("No signals in database.")
            return

        print("\nRecent Signals (Top 20):")
        print("="*60)
        for i, s in enumerate(signals[:20]):
            print(f"{i+1}. {s['ticker']} | Score: {s['confidence_score']} | Created: {s['created_at']}")
        print("="*60)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_saved_signals()
