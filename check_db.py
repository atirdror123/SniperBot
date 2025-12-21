import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def check_recent_signals():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    try:
        supabase = create_client(url, key)
        # Fetch last 5 signals
        response = supabase.table("sniper_signals").select("*").order("created_at", desc=True).limit(5).execute()
        
        print(f"Total signals found: {len(response.data)}")
        for signal in response.data:
            print(f"- {signal['ticker']} | {signal['created_at']} | Score: {signal['confidence_score']}")
            
    except Exception as e:
        print(f"Error connecting to DB: {e}")

if __name__ == "__main__":
    check_recent_signals()
