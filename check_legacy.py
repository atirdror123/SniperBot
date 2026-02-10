"""Quick check: What's in legacy_portfolio table?"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def check():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    print("=== LEGACY_PORTFOLIO TABLE ===")
    try:
        res = supabase.table("legacy_portfolio").select("*").execute()
        count = len(res.data)
        print(f"Row count: {count}")
        if count > 0:
            print(f"Sample (first 3):")
            for row in res.data[:3]:
                print(f"  {row.get('ticker')} - Entry: ${row.get('entry_price')} - Status: {row.get('status')}")
        else:
            print("TABLE IS EMPTY!")
    except Exception as e:
        print(f"Error: {e}")
    
    print("\n=== SNIPER_TRADES TABLE ===")
    try:
        res = supabase.table("sniper_trades").select("*").execute()
        count = len(res.data)
        print(f"Row count: {count}")
    except Exception as e:
        print(f"Error: {e}")

    print("\n=== PAPER_POSITIONS TABLE (Original) ===")
    try:
        res = supabase.table("paper_positions").select("*").execute()
        count = len(res.data)
        print(f"Row count: {count}")
        if count > 0:
            print(f"Sample (first 3):")
            for row in res.data[:3]:
                print(f"  {row.get('ticker')} - Entry: ${row.get('entry_price')} - Portfolio: {row.get('portfolio')}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check()
