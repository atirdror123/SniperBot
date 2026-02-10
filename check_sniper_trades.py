"""Check sniper_trades table contents"""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

print("=== SNIPER_TRADES TABLE ===")
res = supabase.table("sniper_trades").select("*").execute()
print(f"Total Rows: {len(res.data)}")

if res.data:
    for row in res.data[:10]:
        print(f"  {row.get('ticker')} | Status: {row.get('status')} | Entry: ${row.get('entry_price', 0):.2f} | AI: {row.get('ai_score', 'N/A')}")
else:
    print("  TABLE IS EMPTY!")
