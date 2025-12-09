import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

print("Starting minimal test...")
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("Missing keys")
else:
    print("Keys found")
    try:
        supabase = create_client(url, key)
        print("Client created")
        response = supabase.table('sniper_signals').select('count', count='exact').execute()
        print(f"Count response: {response}")
    except Exception as e:
        print(f"Error: {e}")
print("End of test")
