import os
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

def audit():
    supabase = get_supabase()
    print("=== AUDIT START ===\n")

    # 1. Check PORTFOLIO CONFIG
    print("--- 1. PORTFOLIO CONFIG ---")
    try:
        res = supabase.table("portfolio_config").select("*").execute()
        df = pd.DataFrame(res.data)
        if not df.empty:
            print(df.to_string())
        else:
            print("No portfolio config found.")
    except Exception as e:
        print(f"Error reading portfolio_config: {e}")
    print("\n")

    # 2. Check SNIPER SIGNALS (Dashboard Source)
    print("--- 2. SNIPER SIGNALS (Dashboard Source) ---")
    try:
        res = supabase.table("sniper_signals").select("*").execute()
        df = pd.DataFrame(res.data)
        print(f"Total Rows: {len(df)}")
        if not df.empty:
            print(f"Status Counts:\n{df['status'].value_counts()}")
            if 'portfolio' in df.columns:
                print(f"Portfolio Counts:\n{df['portfolio'].value_counts()}")
            else:
                print("No 'portfolio' column in sniper_signals")
            
            # Show a few sample rows
            print("\nSample Data (First 3):")
            print(df.head(3)[['ticker', 'status', 'created_at', 'confidence_score']].to_string())
    except Exception as e:
        print(f"Error reading sniper_signals: {e}")
    print("\n")

    # 3. Check PAPER POSITIONS (Equity Source)
    print("--- 3. PAPER POSITIONS (Equity Source) ---")
    try:
        res = supabase.table("paper_positions").select("*").execute()
        df = pd.DataFrame(res.data)
        print(f"Total Rows: {len(df)}")
        if not df.empty:
            print(f"Status Counts:\n{df['status'].value_counts()}")
            if 'portfolio' in df.columns:
                print(f"Portfolio Counts:\n{df['portfolio'].value_counts()}")
            else:
                print("No 'portfolio' column in paper_positions")

            # Calculate Equity Impact
            # Unrealized
            open_pos = df[(df['status'] == 'OPEN') & (df['portfolio'] == 'SNIPER')]
            print(f"\nOpen SNIPER Positions: {len(open_pos)}")
            
            # Realized
            closed_pos = df[(df['status'] == 'CLOSED') & (df['portfolio'] == 'SNIPER')]
            print(f"Closed SNIPER Positions: {len(closed_pos)}")
            
            total_realized_pnl = closed_pos['pnl'].sum() if 'pnl' in closed_pos.columns else 0
            print(f"Calculated Realized PnL (Closed): ${total_realized_pnl:,.2f}")

            # Identify huge losses
            if 'pnl' in df.columns:
                worst_trades = df.sort_values('pnl', ascending=True).head(5)
                print("\nWorst 5 Trades (PnL):")
                print(worst_trades[['ticker', 'portfolio', 'status', 'entry_price', 'exit_price', 'pnl']].to_string())

    except Exception as e:
        print(f"Error reading paper_positions: {e}")
    print("\n")

if __name__ == "__main__":
    audit()
