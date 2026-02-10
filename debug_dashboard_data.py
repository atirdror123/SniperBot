"""Check what's actually in sniper_trades table for today"""
from dotenv import load_dotenv
import os
from supabase import create_client
from datetime import datetime, timedelta

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

supabase = create_client(url, key)

# Fetch ALL open trades
res = supabase.table('sniper_trades').select('*').eq('status', 'OPEN').execute()
print(f"Total OPEN trades: {len(res.data)}")
for row in res.data:
    print(f"  - {row.get('ticker')}: Entry={row.get('entry_price')}, Score={row.get('ai_score')}, Created={row.get('created_at')}")

# Also check if there are any recent trades regardless of status
print("\n--- All trades from last 2 days ---")
two_days_ago = (datetime.now() - timedelta(days=2)).isoformat()
res2 = supabase.table('sniper_trades').select('*').gte('created_at', two_days_ago).execute()
for row in res2.data:
    print(f"  - {row.get('ticker')}: Status={row.get('status')}, Score={row.get('ai_score')}, Created={row.get('created_at')}")
