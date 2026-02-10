import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def get_supabase():
    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        return create_client(url, key)
    except:
        return None

def run():
    supabase = get_supabase()
    if not supabase:
        print("Failed to connect to Supabase")
        return

    print("--- DATA AUDIT ---")

    # 1. Sniper Signals (Dashboard)
    try:
        res = supabase.table("sniper_signals").select("*", count="exact").eq("status", "OPEN").execute()
        count = len(res.data)
        print(f"Sniper Signals (OPEN): {count}")
    except Exception as e:
        print(f"Error reading signals: {e}")

    # 2. Paper Positions (Logic)
    try:
        res = supabase.table("paper_positions").select("*").execute()
        data = res.data
        
        open_sniper = [d for d in data if d.get('status') == 'OPEN' and d.get('portfolio') == 'SNIPER']
        print(f"Paper Positions (OPEN, SNIPER): {len(open_sniper)}")
        
        # Check for Legacy
        legacy_portfolio = [d for d in data if d.get('portfolio') == 'LEGACY']
        print(f"Paper Positions (LEGACY): {len(legacy_portfolio)}")
        
        # Check for empty portfolio
        empty_portfolio = [d for d in data if not d.get('portfolio')]
        print(f"Paper Positions (No Portfolio): {len(empty_portfolio)}")

        # Calculate Equity components
        realized = sum(d.get('pnl', 0) or 0 for d in data if d.get('status') == 'CLOSED' and d.get('portfolio') == 'SNIPER')
        print(f"Realized PnL (SNIPER): ${realized:,.2f}")

        # Check for huge negative PnL in CLOSED
        worst = sorted([d for d in data if d.get('status') == 'CLOSED'], key=lambda x: x.get('pnl', 0) or 0)[:3]
        print("Worst 3 Closed Trades:")
        for w in worst:
            print(f"  {w.get('ticker')} ({w.get('portfolio')}): ${w.get('pnl', 0):,.2f}")
            
    except Exception as e:
        print(f"Error reading positions: {e}")

if __name__ == "__main__":
    run()
