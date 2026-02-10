"""
Interval-Based Position Monitor (Simplified)
=============================================
Replaces the complex hourly/nightly learning system with
a predictable interval-based check at fixed days:
10, 20, 30, 40, 50, 60 days after entry.

Run this script ONCE DAILY (via cron or GitHub Actions).
"""
import os
from datetime import datetime, timezone
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Configuration
CHECK_INTERVALS = [10, 20, 30, 40, 50, 60]  # Days after entry to check position

def get_supabase() -> Client:
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    if not url or not key:
        raise ValueError("SUPABASE_URL or SUPABASE_KEY not set")
    return create_client(url, key)


def calculate_days_held(entry_date_str: str) -> int:
    """Calculate days since position was opened."""
    try:
        # Handle ISO format with or without timezone
        if 'T' in entry_date_str:
            entry_date = datetime.fromisoformat(entry_date_str.replace('Z', '+00:00'))
        else:
            entry_date = datetime.strptime(entry_date_str[:10], '%Y-%m-%d')
            entry_date = entry_date.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        return (now - entry_date).days
    except Exception as e:
        print(f"  Error parsing date '{entry_date_str}': {e}")
        return -1


def check_position_health(ticker: str, entry_price: float) -> dict:
    """
    Perform a comprehensive check on position health.
    This is where you can add AI analysis, technical checks, etc.
    """
    import yfinance as yf
    
    result = {
        'ticker': ticker,
        'action': 'HOLD',
        'reason': ''
    }
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period='5d')
        
        if hist.empty:
            result['reason'] = 'No price data available'
            return result
        
        current_price = hist['Close'].iloc[-1]
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        
        result['current_price'] = round(current_price, 2)
        result['pnl_pct'] = round(pnl_pct, 2)
        
        # Simple rules - can be expanded
        if pnl_pct <= -10:
            result['action'] = 'REVIEW'
            result['reason'] = f'Down {pnl_pct:.1f}% - Consider stop loss'
        elif pnl_pct >= 20:
            result['action'] = 'REVIEW'
            result['reason'] = f'Up {pnl_pct:.1f}% - Consider taking profits'
        else:
            result['action'] = 'HOLD'
            result['reason'] = f'P&L: {pnl_pct:+.1f}%'
        
        return result
        
    except Exception as e:
        result['reason'] = f'Error: {str(e)}'
        return result


def run_interval_monitor():
    """Main monitoring loop - run once daily."""
    print("=" * 60)
    print("INTERVAL-BASED POSITION MONITOR")
    print(f"Check Intervals: {CHECK_INTERVALS} days")
    print(f"Run Time: {datetime.now().isoformat()}")
    print("=" * 60)
    
    supabase = get_supabase()
    
    # Get all OPEN positions
    response = supabase.table('sniper_trades').select('*').eq('status', 'OPEN').execute()
    positions = response.data or []
    
    print(f"\nFound {len(positions)} OPEN positions.\n")
    
    if not positions:
        print("No positions to monitor.")
        return
    
    actions_needed = []
    
    for pos in positions:
        ticker = pos['ticker']
        entry_price = pos.get('entry_price', 0)
        created_at = pos.get('created_at', '')
        
        days_held = calculate_days_held(created_at)
        
        print(f"{ticker}: Day {days_held}", end=" ")
        
        # Check if today is an interval day
        if days_held in CHECK_INTERVALS:
            print(f"→ 🔍 INTERVAL CHECK (Day {days_held})")
            
            health = check_position_health(ticker, entry_price)
            print(f"    Price: ${health.get('current_price', 'N/A')} | {health['reason']}")
            
            if health['action'] == 'REVIEW':
                actions_needed.append({
                    'ticker': ticker,
                    'days_held': days_held,
                    **health
                })
        else:
            # Find next check interval
            next_check = min([d for d in CHECK_INTERVALS if d > days_held], default=None)
            if next_check:
                print(f"→ ⏭️ Skipping (Next check in {next_check - days_held} days)")
            else:
                print(f"→ ⚠️ Past all intervals ({max(CHECK_INTERVALS)} day max)")
    
    # Summary
    print("\n" + "=" * 60)
    print("MONITOR SUMMARY")
    print("=" * 60)
    
    if actions_needed:
        print(f"\n⚠️  {len(actions_needed)} position(s) need review:\n")
        for action in actions_needed:
            print(f"  • {action['ticker']} (Day {action['days_held']}): {action['reason']}")
    else:
        print("\n✅ All positions healthy. No action needed.")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_interval_monitor()
