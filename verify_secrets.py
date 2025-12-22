import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print(f"URL: {url}")
print(f"Key Length: {len(key) if key else 0}")
if key:
    print(f"Key Preview: {key[:10]} ... {key[-10:]}")

print("\nTesting Connection...")
try:
    supabase = create_client(url, key)
    # Try a lightweight read (system_status or empty query)
    resp = supabase.table("system_status").select("*").limit(1).execute()
    print("SUCCESS: Connection Established.")
    print(f"Data: {resp.data}")
except Exception as e:
    print(f"FAILED: {e}")
