"""
Alpaca Connection Verification Script
Confirms API connection and tests live price feed.
"""
import os
from dotenv import load_dotenv

load_dotenv()

def verify_alpaca():
    print("=" * 50)
    print("🔍 ALPACA CONNECTION VERIFICATION")
    print("=" * 50)
    
    # Check keys
    api_key = os.getenv("ALPACA_API_KEY")
    secret_key = os.getenv("ALPACA_SECRET_KEY")
    
    if not api_key or not secret_key:
        print("\n❌ MISSING API KEYS!")
        print("Add these to your .env file:")
        print("  ALPACA_API_KEY=your_key")
        print("  ALPACA_SECRET_KEY=your_secret")
        print("  ALPACA_BASE_URL=https://paper-api.alpaca.markets")
        return False
    
    print(f"\n✅ API Key found: {api_key[:8]}...")
    
    try:
        from alpaca_client import get_alpaca_client
        client = get_alpaca_client()
        
        # 1. Account Info
        print("\n📊 ACCOUNT INFO:")
        account = client.get_account()
        print(f"  Equity: ${float(account.equity):,.2f}")
        print(f"  Buying Power: ${float(account.buying_power):,.2f}")
        print(f"  Cash: ${float(account.cash):,.2f}")
        
        # 2. Test TSM Price (the problematic stock)
        print("\n💹 LIVE PRICE TEST (TSM):")
        tsm_price = client.get_live_price("TSM")
        print(f"  TSM Current Price: ${tsm_price:.2f}")
        
        if 150 < tsm_price < 250:
            print("  ✅ Price is realistic (~$200 range)")
        else:
            print(f"  ⚠️ Price seems unusual (expected ~$200)")
        
        # 3. Open Positions
        print("\n📂 OPEN POSITIONS:")
        positions = client.get_positions()
        if positions:
            for pos in positions:
                pl = float(pos.unrealized_pl)
                pl_pct = float(pos.unrealized_plpc) * 100
                color = "🟢" if pl >= 0 else "🔴"
                print(f"  {color} {pos.symbol}: {pos.qty} shares @ ${float(pos.avg_entry_price):.2f} | P/L: ${pl:+,.2f} ({pl_pct:+.2f}%)")
        else:
            print("  (No open positions)")
        
        print("\n" + "=" * 50)
        print("✅ ALPACA VERIFICATION COMPLETE")
        print("=" * 50)
        return True
        
    except ImportError:
        print("\n❌ alpaca-py not installed!")
        print("Run: pip install alpaca-py")
        return False
    except Exception as e:
        print(f"\n❌ Connection Error: {e}")
        return False


if __name__ == "__main__":
    verify_alpaca()
