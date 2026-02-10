"""
Diagnose Alpaca Orders
Checks for open orders and positions to see why they aren't showing up.
"""
from alpaca_client import get_alpaca_client

client = get_alpaca_client()

print("="*50)
print("🔍 ALPACA DIAGNOSTICS")
print("="*50)

# 1. Check Positions (Filled)
positions = client.get_positions()
print(f"\n📂 OPEN POSITIONS (Filled): {len(positions)}")
for p in positions:
    print(f"  - {p.symbol}: {p.qty} shares")

# 2. Check Orders (Pending/Open)
# We need to access the trading client directly to list orders
try:
    from alpaca.trading.requests import GetOrdersRequest
    from alpaca.trading.enums import OrderStatus
    
    req = GetOrdersRequest(status=OrderStatus.OPEN, limit=10, nested=True)
    orders = client.trading.get_orders(req)
    
    print(f"\n⏳ PENDING ORDERS: {len(orders)}")
    for o in orders:
        print(f"  - {o.symbol} ({o.side}): {o.qty} shares | Status: {o.status}")
        print(f"    Submited at: {o.submitted_at}")

except Exception as e:
    print(f"Error fetching orders: {e}")

print("\n" + "="*50)
