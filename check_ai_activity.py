import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def check_ai_usage():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        print("Error: Missing keys")
        return

    supabase = create_client(url, key)
    
    print("Checking for AI Activity in Database...")
    
    # Query for reasons containing "AI INSIGHT"
    # Note: 'reasons' is a TEXT column. We use ilike.
    try:
        response = supabase.table('sniper_signals').select('*').ilike('reasons', '%AI INSIGHT%').order('created_at', desc=True).limit(5).execute()
        signals = response.data
        
        if not signals:
            print("No signals found with 'AI INSIGHT'.")
            print("This suggests the AI layer hasn't triggered yet, or failed silently.")
        else:
            print(f"✅ Found {len(signals)} signals modified by AI!")
            for s in signals:
                print(f"- {s['ticker']} (Score: {s['confidence_score']}) | Date: {s['created_at']}")
                print(f"  Reason Snippet: {s['reasons'][:100]}...")
                
    except Exception as e:
        print(f"Error querying DB: {e}")

if __name__ == "__main__":
    check_ai_usage()
