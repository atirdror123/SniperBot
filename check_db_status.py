import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def check_db():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ Missing Supabase credentials in .env")
        return

    print(f"🔌 Connecting to Supabase...")
    supabase = create_client(url, key)
    
    try:
        # Check sniper_signals
        print("\n🔎 Checking 'sniper_signals' table (New System):")
        response = supabase.table("sniper_signals").select("ticker, confidence_score, status, created_at").eq("status", "OPEN").order("created_at", desc=True).limit(5).execute()
        
        rows = response.data
        if rows:
            print(f"✅ Found {len(rows)} OPEN signals:")
            for row in rows:
                print(f"   - {row['ticker']}: Score {row['confidence_score']} ({row['created_at']})")
        else:
            print("⚠️ No OPEN signals found in 'sniper_signals'.")
            print("   (This means the new scanner hasn't run successfully yet)")

        # Check paper_positions (Old System - just to see)
        print("\n🔎 Checking 'paper_positions' table (Old System):")
        response_old = supabase.table("paper_positions").select("ticker, status").eq("status", "OPEN").limit(5).execute()
        if response_old.data:
            print(f"ℹ️  Found {len(response_old.data)} rows in old table (these were creating the confusion).")
        else:
            print("   Table is empty.")

    except Exception as e:
        print(f"❌ Error querying database: {e}")

if __name__ == "__main__":
    check_db()
