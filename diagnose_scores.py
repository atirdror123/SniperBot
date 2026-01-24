"""Check why APLE was saved"""
import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

print("=== APLE Signal Details ===\n")
try:
    data = supabase.table("sniper_signals").select("*").eq("ticker", "APLE").execute()
    if data.data:
        for row in data.data:
            print(f"Date: {row.get('created_at', 'N/A')[:10]}")
            print(f"Entry Price: ${row.get('entry_price', 0)}")
            print(f"Confidence Score: {row.get('confidence_score', 0)}")
            print(f"Reasons: {row.get('reasons', 'N/A')}")
            print(f"\nRaw Features:")
            raw = row.get('raw_features', {})
            if raw:
                lens_scores = raw.get('lens_scores', {})
                for lens, score in lens_scores.items():
                    print(f"  {lens}: {score}")
    else:
        print("APLE not found in signals. Checking if you meant AAPL...")
        data2 = supabase.table("sniper_signals").select("*").eq("ticker", "AAPL").execute()
        if data2.data:
            for row in data2.data:
                print(f"Date: {row.get('created_at', 'N/A')[:10]}")
                print(f"Entry Price: ${row.get('entry_price', 0)}")
                print(f"Confidence Score: {row.get('confidence_score', 0)}")
                print(f"Reasons: {row.get('reasons', 'N/A')}")
                raw = row.get('raw_features', {})
                if raw:
                    lens_scores = raw.get('lens_scores', {})
                    print(f"\nLens Scores:")
                    for lens, score in lens_scores.items():
                        print(f"  {lens}: {score}")
except Exception as e:
    print(f"Error: {e}")
