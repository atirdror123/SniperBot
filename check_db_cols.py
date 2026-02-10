from dotenv import load_dotenv
import os
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("No credentials")
    exit()

supabase = create_client(url, key)

try:
    # Fetch one row to see columns
    res = supabase.table('sniper_trades').select('*').limit(1).execute()
    if res.data:
        print("Columns found:", list(res.data[0].keys()))
    else:
        print("Table empty, cannot infer columns easily via select. Trying partial insert to test.")
        # We can't easily DESCRIBE table via client, but we can try to insert dummy data and see if it fails?
        # Better: just Assume we need to Add them if we are unsure, OR relying on error handling.
        # But 'sniper_signals' definition in schema doesn't show them.
        pass
except Exception as e:
    print(e)
