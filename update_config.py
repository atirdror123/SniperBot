import os
import sys
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

if not url or not key:
    print("Missing Supabase credentials")
    sys.exit(1)

supabase = create_client(url, key)

def update_weights():
    print("--- UPDATING BOT CONFIG WEIGHTS ---")
    
    # New rigorous weights
    new_config = {
        "w_trend": 0.40, 
        "w_volatility": 0.30, 
        "w_fundamental": 0.15, 
        "w_sentiment": 0.15
    }
    
    try:
        # Check if row exists
        resp = supabase.table("bot_config").select("*").eq("config_key", "global_strategy").execute()
        
        if resp.data:
            print("Updating existing config...")
            supabase.table("bot_config").update(new_config).eq("config_key", "global_strategy").execute()
        else:
            print("Creating new config...")
            new_config["config_key"] = "global_strategy"
            supabase.table("bot_config").insert(new_config).execute()
            
        print("SUCCESS: Weights updated.")
        print(f"New Weights: {new_config}")
        
    except Exception as e:
        print(f"ERROR: {e}")

if __name__ == "__main__":
    update_weights()
