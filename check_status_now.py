import os
from supabase import create_client
from dotenv import load_dotenv
import time

load_dotenv()

def check_status():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("Missing Supabase credentials")
        return

    supabase = create_client(url, key)
    
    # 1. Check System Status
    try:
        res = supabase.table('system_status').select("*").execute()
        print("--- System Status ---")
        for row in res.data:
            print(row)
    except Exception as e:
        print(f"Error checking status: {e}")

    # 2. Check Last Scan Summary
    try:
        res = supabase.table('scan_summaries').select("*").order("date", desc=True).limit(3).execute()
        print("\n--- Recent Scan Summaries ---")
        for row in res.data:
            print(f"Date: {row.get('date')}, Scanned: {row.get('scanned_count')}, Saved: {row.get('saved_count')}")
    except Exception as e:
        print(f"Error checking summaries: {e}")

if __name__ == "__main__":
    check_status()
