"""
Database Migration Script: Hard Separation
Creates legacy_portfolio and sniper_trades tables, migrates data, and resets equity.
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

def migrate():
    supabase = get_supabase()
    print("=" * 60)
    print("HARD SEPARATION MIGRATION")
    print("=" * 60)

    # =========================================================================
    # STEP 1: Create legacy_portfolio table (via insert - tables auto-create in Supabase)
    # =========================================================================
    print("\n--- STEP 1: Migrate data to legacy_portfolio ---")
    
    try:
        # Fetch all existing data from paper_positions
        res = supabase.table("paper_positions").select("*").execute()
        existing_data = res.data
        print(f"Found {len(existing_data)} rows in paper_positions")
        
        if existing_data:
            # Prepare data for legacy_portfolio (keeping same structure)
            legacy_data = []
            for row in existing_data:
                legacy_row = {
                    'ticker': row.get('ticker'),
                    'entry_price': row.get('entry_price'),
                    'quantity': row.get('quantity', 1),
                    'cost_basis': row.get('cost_basis'),
                    'status': row.get('status', 'OPEN'),
                    'entry_date': row.get('entry_date') or row.get('created_at'),
                    'exit_price': row.get('exit_price'),
                    'exit_date': row.get('exit_date'),
                    'exit_reason': row.get('exit_reason'),
                    'pnl': row.get('pnl'),
                    'notes': 'Migrated from paper_positions'
                }
                legacy_data.append(legacy_row)
            
            # Insert into legacy_portfolio
            supabase.table("legacy_portfolio").insert(legacy_data).execute()
            print(f"✅ Migrated {len(legacy_data)} rows to legacy_portfolio")
        else:
            print("No data to migrate.")
            
    except Exception as e:
        print(f"❌ Step 1 Error: {e}")
        print("Note: You may need to create the 'legacy_portfolio' table in Supabase first.")
        print("Schema: ticker(text), entry_price(float8), quantity(int4), cost_basis(float8),")
        print("        status(text), entry_date(timestamptz), exit_price(float8),")
        print("        exit_date(timestamptz), exit_reason(text), pnl(float8), notes(text)")
        return

    # =========================================================================
    # STEP 2: Verify sniper_trades table exists (or create structure)
    # =========================================================================
    print("\n--- STEP 2: Verify sniper_trades table ---")
    
    try:
        # Check if table exists by trying to select
        res = supabase.table("sniper_trades").select("*").limit(1).execute()
        print(f"✅ sniper_trades table exists. Current rows: {len(res.data)}")
    except Exception as e:
        print(f"❌ sniper_trades table may not exist: {e}")
        print("Please create 'sniper_trades' table in Supabase with schema:")
        print("  id (uuid, pk), ticker (text), entry_price (float8), current_price (float8),")
        print("  quantity (int4), status (text), entry_date (timestamptz), exit_date (timestamptz),")
        print("  stop_loss_price (float8), take_profit_price (float8), ai_score (float8),")
        print("  pnl (float8), notes (text)")
        return

    # =========================================================================
    # STEP 3: Reset Portfolio Config for Sniper
    # =========================================================================
    print("\n--- STEP 3: Reset Portfolio Config ---")
    
    try:
        supabase.table("portfolio_config").upsert({
            'id': 'SNIPER',
            'starting_capital': 100000,
            'current_equity': 100000,
            'cash_balance': 100000,
            'notes': f'Reset on {datetime.now().isoformat()}'
        }).execute()
        print("✅ Portfolio Config reset to $100,000")
    except Exception as e:
        print(f"❌ Step 3 Error: {e}")

    # =========================================================================
    # STEP 4: Clear Equity History for fresh start (optional)
    # =========================================================================
    print("\n--- STEP 4: Reset Equity History ---")
    
    try:
        # Delete old SNIPER equity history
        supabase.table("equity_history").delete().eq("portfolio", "SNIPER").execute()
        
        # Insert fresh baseline
        supabase.table("equity_history").insert({
            'portfolio': 'SNIPER',
            'equity': 100000
        }).execute()
        print("✅ Equity History reset (Fresh $100k baseline)")
    except Exception as e:
        print(f"❌ Step 4 Error: {e}")

    # =========================================================================
    # STEP 5: Verification
    # =========================================================================
    print("\n--- STEP 5: Verification ---")
    
    try:
        # Legacy count
        legacy_res = supabase.table("legacy_portfolio").select("*", count="exact").execute()
        legacy_count = len(legacy_res.data)
        print(f"legacy_portfolio rows: {legacy_count}")
        
        # Sniper trades count
        sniper_res = supabase.table("sniper_trades").select("*", count="exact").execute()
        sniper_count = len(sniper_res.data)
        print(f"sniper_trades rows: {sniper_count}")
        
        # Portfolio config
        config_res = supabase.table("portfolio_config").select("*").eq("id", "SNIPER").execute()
        if config_res.data:
            equity = config_res.data[0].get('current_equity', 0)
            print(f"SNIPER Equity: ${equity:,.2f}")
        
    except Exception as e:
        print(f"Verification Error: {e}")

    print("\n" + "=" * 60)
    print("MIGRATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    migrate()
