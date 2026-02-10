"""
Sync VIST to Alpaca
===================
Reads VIST details from Supabase and submits the missing order to Alpaca.
"""
import os
import json
from dotenv import load_dotenv
from supabase import create_client
from alpaca_client import get_alpaca_client

load_dotenv()

def sync_vist():
    # 1. Fetch from Database
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    print("Fetching VIST from database...")
    res = supabase.table('sniper_trades').select('*').eq('ticker', 'VIST').execute()
    
    if not res.data:
        print("❌ VIST not found in database!")
        return

    trade = res.data[0]
    print(f"✅ Found VIST in DB:")
    print(f"   Entry Price: ${trade.get('entry_price')}")
    print(f"   Quantity: {trade.get('quantity')}")
    print(f"   Invested: ${trade.get('invested_amount')}")
    print(f"   Status: {trade.get('status')}")
    
    # 2. Submit to Alpaca
    print("\nConnecting to Alpaca...")
    try:
        alpaca = get_alpaca_client()
        
        # Check if already open (double check)
        try:
            pos = alpaca.get_position('VIST')
            print(f"⚠️ VIST is ALREADY in Alpaca! Qty: {pos.qty}")
            return
        except:
            print("   (Confirmed VIST is missing from Alpaca)")
        
        qty = trade.get('quantity')
        if not qty:
            print("❌ Quantity invalid.")
            return

        print(f"🚀 Submitting Order: Buy {qty} VIST...")
        order = alpaca.submit_bracket_order(
            ticker='VIST',
            qty=qty,
            stop_loss_pct=0.05,
            take_profit_pct=0.10
        )
        print(f"✅ SUCCESS! Order ID: {order.id}")
        
    except Exception as e:
        print(f"❌ Alpaca Error: {e}")

if __name__ == "__main__":
    sync_vist()
