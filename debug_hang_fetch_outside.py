import time
print("Start", flush=True)
from ai_signal_engine import AISignalEngine
import yfinance as yf
print("Imports done", flush=True)

engine = AISignalEngine()
print("Engine created", flush=True)

ticker = "NVDA"
print(f"Fetching {ticker} outside engine...", flush=True)
stock = yf.Ticker(ticker)
print(stock.insider_transactions.head(), flush=True)
print("Fetch done", flush=True)
