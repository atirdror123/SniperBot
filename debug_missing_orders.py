"""
Debug Missing Orders
Checks ALL orders (Open, Closed, Rejected) for GPRK and TSM
"""
from alpaca_client import get_alpaca_client
from alpaca.trading.requests import GetOrdersRequest
from alpaca.trading.enums import OrderStatus

client = get_alpaca_client()

print("="*50)
print("🔍 ORDER HISTORY CHECK")
print("="*50)

for ticker in ["GPRK", "TSM", "VIST"]:
    print(f"\nChecking {ticker}...")
    try:
        # Check ALL orders (limit 5 most recent)
        req = GetOrdersRequest(status=OrderStatus.ALL, limit=5, nested=True, symbols=[ticker])
        orders = client.trading.get_orders(req)
        
        if not orders:
            print(f"  ❌ No orders found.")
        
        for o in orders:
            print(f"  - {o.side} {o.qty} shares | Status: {o.status} | Time: {o.submitted_at}")
            if o.status == 'rejected':
                 # Try to find rejection reason if possible (Alpaca API sometimes hides it in deep objects)
                 print(f"    ⚠️ REJECTED")
            
    except Exception as e:
        print(f"  Error: {e}")

print("\n" + "="*50)
