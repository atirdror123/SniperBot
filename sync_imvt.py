"""
Sync IMVT to Alpaca
===================
Reads IMVT details from Supabase and submits the missing order to Alpaca.
"""
import os
import json
from dotenv import load_dotenv
from supabase import create_client
from alpaca_client import get_alpaca_client

load_dotenv()

def sync_imvt():
    # 1. Fetch from Database
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    print("Fetching IMVT from database...")
    res = supabase.table('sniper_trades').select('*').eq('ticker', 'IMVT').execute()
    
    if not res.data:
        print("❌ IMVT not found in database!")
        return

    trade = res.data[0]
    print(f"✅ Found IMVT in DB:")
    print(f"   Entry Price: ${trade.get('entry_price')}")
    print(f"   Quantity: {trade.get('quantity')}")
    print(f"   Invested: ${trade.get('invested_amount')}")
    
    # 2. Submit to Alpaca
    print("\nConnecting to Alpaca...")
    try:
        alpaca = get_alpaca_client()
        
        qty = trade.get('quantity')
        if not qty:
            print("❌ Quantity invalid.")
            return

        print(f"🚀 Submitting Order: Buy {qty} IMVT...")
        order = alpaca.submit_bracket_order(
            ticker='IMVT',
            qty=qty,
            stop_loss_pct=0.05,
            take_profit_pct=0.10,
            current_price=trade.get('entry_price')  # Use DB price to ensure valid limits
        )
        print(f"✅ SUCCESS! Order ID: {order.id}")
        
    except Exception as e:
        print(f"❌ Alpaca Error: {e}")

if __name__ == "__main__":
    sync_imvt()
