import os
from supabase import create_client, Client
from dotenv import load_dotenv
import json

load_dotenv()
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

print("--- LATEST SCAN SUMMARY ---")
try:
    data = supabase.table("scan_summaries").select("*").order("date", desc=True).limit(1).execute()
    if data.data:
        print(json.dumps(data.data[0], indent=2))
    else:
        print("No scan summaries found.")
except Exception as e:
    print(f"Error: {e}")
