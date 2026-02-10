import os
import json
from dotenv import load_dotenv
from supabase import create_client
from alpaca_client import get_alpaca_client

load_dotenv()

def check_imvt():
    print("="*60)
    print("🔍 DIAGNOSTIC: IMVT STATUS")
    print("="*60)

    # 1. DB CHECK
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    supabase = create_client(url, key)
    
    res = supabase.table('sniper_trades').select('*').eq('ticker', 'IMVT').execute()
    if res.data:
        data = res.data[0]
        print(f"✅ DB STATUS: FOUND")
        print(f"   ID: {data.get('id')}")
        print(f"   Status: {data.get('status')}")
        print(f"   Created: {data.get('created_at')}")
        print(f"   Qty: {data.get('quantity')}")
    else:
        print("❌ DB STATUS: NOT FOUND")

    # 2. ALPACA CHECK
    try:
        alpaca = get_alpaca_client()
        
        # Check Positions
        try:
            pos = alpaca.get_position('IMVT')
            print(f"✅ ALPACA POSITION: FOUND")
            print(f"   Qty: {pos.qty}")
            print(f"   Value: ${pos.market_value}")
        except:
            print("❌ ALPACA POSITION: NOT FOUND")
            
        # Check Orders
        orders = alpaca.get_orders(status='all', limit=5)
        # Filter for IMVT manually since get_orders wrapper might not support symbols arg
        orders = [o for o in orders if o.symbol == 'IMVT'] if orders else []
        if orders:
            print(f"ℹ️ ALPACA RECENT ORDERS ({len(orders)}):")
            for o in orders:
                print(f"   {o.submitted_at.strftime('%H:%M:%S')} - {o.side} {o.qty} @ {o.limit_price} ({o.status})")
        else:
            print("❌ ALPACA ORDERS: NONE FOUND")

    except Exception as e:
        print(f"⚠️ Alpaca Check Failed: {e}")

if __name__ == "__main__":
    check_imvt()
