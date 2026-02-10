from supabase import create_client
import os
from dotenv import load_dotenv
import json

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
sb = create_client(url, key)

res = sb.table('sniper_trades').select('*').eq('ticker', 'VIST').execute()

print(f"Found {len(res.data)} records for VIST")
for item in res.data:
    print(f"ID: {item.get('id')}")
    print(f"Status: {item.get('status')}")
    print(f"Created At: {item.get('created_at')}")
    print("-" * 30)
