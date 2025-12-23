import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

today_str = datetime.now().strftime("%Y-%m-%d")
print(f"Cleaning signals from: {today_str}")

try:
    # Delete
    res = supabase.table("sniper_signals") \
        .delete() \
        .gte("created_at", today_str + " 00:00:00") \
        .execute()
    
    # Supabase delete returns the deleted rows usually
    count = len(res.data) if res.data else 0
    print(f"Deleted {count} signals.")

except Exception as e:
    print(f"Error: {e}")
