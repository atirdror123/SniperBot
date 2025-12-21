from data_ingestion import DataIngestor
import os
from dotenv import load_dotenv

load_dotenv()

d = DataIngestor()
ticker = "AAPL"

print(f"--- Testing DataIngestor for {ticker} ---")

# 1. Fundamentals (Should succeed via Stable)
print("\n1. Fundamentals:")
try:
    f = d.get_fundamentals(ticker)
    print(f"Result: {f}")
except Exception as e:
    print(f"Error: {e}")

# 2. Insider (Should skip FMP, maybe find YF or None)
print("\n2. Insider:")
try:
    i = d.get_insider_activity(ticker)
    print(f"Result: {i}")
except Exception as e:
    print(f"Error: {e}")

# 3. Institutional (Should skip FMP, maybe find YF or None)
print("\n3. Institutional:")
try:
    inst = d.get_dark_pool_activity(ticker)
    print(f"Result: {inst}")
except Exception as e:
    print(f"Error: {e}")
