import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

today_str = datetime.now().strftime("%Y-%m-%d")
print(f"Checking for signals on: {today_str}")

try:
    # Check for any signal created today
    res = supabase.table("sniper_signals") \
        .select("ticker, created_at, confidence_score") \
        .gte("created_at", today_str + " 00:00:00") \
        .execute()
    
    if res.data:
        print(f"FOUND {len(res.data)} signals:")
        for s in res.data:
            print(f"- {s['ticker']} at {s['created_at']}")
    else:
        print("NO SIGNALS found for today.")
        
    # Check System Status
    st = supabase.table("system_status").select("*").execute()
    print(f"System Status: {st.data}")

except Exception as e:
    print(f"Error: {e}")
