import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

print("Fetching latest signal...")
res = supabase.table("sniper_signals").select("ticker, raw_features").order("created_at", desc=True).limit(1).execute()

if res.data:
    row = res.data[0]
    print(f"Ticker: {row['ticker']}")
    print(f"Raw Features Type: {type(row['raw_features'])}")
    print(f"Raw Features Content: {row['raw_features']}")
else:
    print("No signals found.")
