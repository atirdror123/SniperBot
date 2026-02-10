"""Re-migrate: Check sniper_signals and migrate to legacy_portfolio"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def migrate():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    print("=== CHECKING SNIPER_SIGNALS (Original Source) ===")
    try:
        res = supabase.table("sniper_signals").select("*").execute()
        count = len(res.data)
        print(f"sniper_signals row count: {count}")
        
        if count == 0:
            print("sniper_signals is also EMPTY!")
            return
        
        # Show sample
        print(f"Sample (first 3):")
        for row in res.data[:3]:
            print(f"  {row.get('ticker')} - Entry: ${row.get('entry_price')} - Status: {row.get('status')}")
        
        # Migrate to legacy_portfolio
        print(f"\n=== MIGRATING {count} ROWS TO legacy_portfolio ===")
        
        legacy_data = []
        for row in res.data:
            legacy_row = {
                'ticker': row.get('ticker'),
                'entry_price': row.get('entry_price'),
                'quantity': 1,
                'status': row.get('status', 'OPEN'),
                'entry_date': row.get('created_at'),
                'notes': f"Migrated from sniper_signals. Original score: {row.get('confidence_score')}"
            }
            legacy_data.append(legacy_row)
        
        # Batch insert
        supabase.table("legacy_portfolio").insert(legacy_data).execute()
        print(f"✅ Successfully migrated {len(legacy_data)} rows to legacy_portfolio!")
        
        # Verify
        verify = supabase.table("legacy_portfolio").select("*", count="exact").execute()
        print(f"Verification: legacy_portfolio now has {len(verify.data)} rows")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    migrate()
