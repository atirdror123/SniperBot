from dotenv import load_dotenv
import os
import json
load_dotenv()
from supabase import create_client

sb = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
r = sb.table('sniper_signals').select('*').eq('portfolio', 'LEGACY').limit(2).execute()

for s in r.data:
    print(f"Ticker: {s['ticker']}")
    raw = s.get('raw_features', {}) or {}
    print(f"Raw features structure:")
    print(json.dumps(raw, indent=2))
    print("\n" + "="*50 + "\n")
