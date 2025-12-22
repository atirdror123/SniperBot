import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

print("Attempting to force-set status to RUNNING...")
try:
    # Try to write directly
    data = {"key": "scan_status", "value": "RUNNING"}
    res = supabase.table("system_status").upsert(data).execute()
    print(f"SUCCESS: Status updated. Dashboard should turn GREEN. Data: {res.data}")
except Exception as e:
    print(f"FAILED: {e}")
    print("\nLikely cause: Table 'system_status' does not exist.")
