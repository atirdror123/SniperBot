import os
import json
import time
import warnings
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv
import pandas as pd
import yfinance as yf
import requests
from supabase import create_client

warnings.filterwarnings('ignore')
load_dotenv()

print("Imports done", flush=True)
t = yf.Ticker("NVDA")
print("Ticker done", flush=True)
try:
    print(t.insider_transactions.head(), flush=True)
except Exception as e:
    print(f"Error: {e}", flush=True)
print("Done", flush=True)
