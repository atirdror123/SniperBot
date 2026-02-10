"""Insert GPRK test trade into sniper_trades"""
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client
import yfinance as yf

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase = create_client(url, key)

# Get current GPRK price
ticker = "GPRK"
stock = yf.Ticker(ticker)
hist = stock.history(period="1d")
entry_price = float(hist['Close'].iloc[-1]) if not hist.empty else 55.48

# Insert trade
trade_data = {
    'ticker': ticker,
    'entry_price': entry_price,
    'quantity': 1,
    'status': 'OPEN',
    'ai_score': 100,
    'stop_loss_price': entry_price * 0.97,
    'take_profit_price': entry_price * 1.10,
    'notes': 'Manually inserted - Scanner AI error prevented save',
    'entry_date': datetime.now().isoformat()
}

print(f"Inserting GPRK trade at ${entry_price:.2f}...")
supabase.table("sniper_trades").insert(trade_data).execute()
print("✅ GPRK inserted successfully!")

# Verify
res = supabase.table("sniper_trades").select("*").eq("status", "OPEN").execute()
print(f"\nOpen trades: {len(res.data)}")
for row in res.data:
    print(f"  {row.get('ticker')} | ${row.get('entry_price'):.2f} | Score: {row.get('ai_score')}")
