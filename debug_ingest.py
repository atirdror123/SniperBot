from dotenv import load_dotenv
load_dotenv() # Load keys!

from data_ingestion import DataIngestor

ingestor = DataIngestor()
print("--- DEBUG INGESTION (WITH KEYS) ---")
t = "AAPL"

print("1. Dark Pool (Quant):")
dp = ingestor.get_dark_pool_activity(t)
print(dp)

print("\n2. Insider (Hunter):")
ins = ingestor.get_insider_activity(t)
print(ins)

print("\n3. Earnings (Oracle):")
earn = ingestor.get_earnings_sentiment(t)
print(earn)
