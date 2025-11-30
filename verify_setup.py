import os
import yfinance as yf
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def verify_yfinance():
    print("Testing yfinance...")
    try:
        ticker = "AAPL"
        stock = yf.Ticker(ticker)
        # Get 1 day of history
        hist = stock.history(period="1d")
        
        if not hist.empty:
            closing_price = hist['Close'].iloc[0]
            print(f"AAPL Closing Price: {closing_price}")
        else:
            print("yfinance Error: No data returned for AAPL")
            
    except Exception as e:
        print(f"yfinance Error: {e}")

def verify_supabase():
    print("Testing Supabase...")
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
        return

    try:
        supabase: Client = create_client(url, key)
        if supabase:
            print("Supabase Connected")
    except Exception as e:
        print(f"Supabase Connection Failed: {e}")

if __name__ == "__main__":
    print("Starting Verification (Phase 1 Revision)...")
    verify_yfinance()
    verify_supabase()
