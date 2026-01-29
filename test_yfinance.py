import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

print("Init supabase...", flush=True)
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
print("Supabase done", flush=True)

import yfinance as yf
print("Fetching NVDA...", flush=True)
t = yf.Ticker("NVDA")
print(t.insider_transactions.head(), flush=True)
print("Done", flush=True)
