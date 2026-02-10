"""
Alpaca Markets API Client Wrapper
Paper Trading Integration for Sniper Bot
"""
import os
from dotenv import load_dotenv

load_dotenv()

# Alpaca SDK imports
try:
    from alpaca.trading.client import TradingClient
    from alpaca.trading.requests import MarketOrderRequest, StopLossRequest, GetOrdersRequest
    from alpaca.trading.enums import OrderSide, TimeInForce, OrderClass, OrderStatus
    from alpaca.data.live import StockDataStream
    from alpaca.data.historical import StockHistoricalDataClient
    from alpaca.data.requests import StockLatestQuoteRequest
    ALPACA_AVAILABLE = True
except ImportError:
    ALPACA_AVAILABLE = False
    print("⚠️ alpaca-py not installed. Run: pip install alpaca-py")


class AlpacaClient:
    """Wrapper for Alpaca Paper Trading API."""
    
    def __init__(self):
        self.api_key = os.getenv("ALPACA_API_KEY")
        self.secret_key = os.getenv("ALPACA_SECRET_KEY")
        self.base_url = os.getenv("ALPACA_BASE_URL", "https://paper-api.alpaca.markets")
        
        if not ALPACA_AVAILABLE:
            raise ImportError("alpaca-py library is not installed. Please run: pip install alpaca-py")
            
        if not self.api_key or not self.secret_key:
            raise ValueError("Missing ALPACA_API_KEY or ALPACA_SECRET_KEY in .env")
        
        # Clean up URL: remove trailing slashes and versioning (SDK adds /v2)
        base_url = self.base_url.rstrip("/")
        if base_url.endswith("/v2"):
            base_url = base_url[:-3]
        
        # Trading client
        self.trading = TradingClient(
            api_key=self.api_key,
            secret_key=self.secret_key,
            paper=True,  # Paper trading mode
            url_override=base_url if self.base_url else None
        )
        
        # Data client (for quotes)
        self.data = StockHistoricalDataClient(
            api_key=self.api_key,
            secret_key=self.secret_key
        )
    
    def get_account(self):
        """Get account info (equity, buying_power, etc.)."""
        return self.trading.get_account()
    
    def get_positions(self):
        """Get all open positions."""
        return self.trading.get_all_positions()

    def get_orders(self, status="open", limit=50):
        """Get orders by status (open, closed, all)."""
        # Map string status to Enum if needed
        status_filter = None
        try:
            if status.lower() == "closed": 
                status_filter = OrderStatus.CLOSED
            elif status.lower() == "all": 
                status_filter = OrderStatus.ALL
            else: 
                status_filter = OrderStatus.OPEN 
        except AttributeError:
            # Fallback to string if Enum is missing attributes
            status_filter = status.lower()
        
        req = GetOrdersRequest(status=status_filter, limit=limit, nested=True)
        return self.trading.get_orders(req)
    
    def get_position(self, ticker: str):
        """Get position for a specific ticker."""
        try:
            return self.trading.get_open_position(ticker)
        except Exception:
            return None
    
    def get_quote(self, ticker: str):
        """Get latest quote (bid/ask) for a ticker."""
        request = StockLatestQuoteRequest(symbol_or_symbols=ticker)
        quotes = self.data.get_stock_latest_quote(request)
        return quotes.get(ticker)
    
    def get_live_price(self, ticker: str) -> float:
        """Get current market price for a ticker."""
        quote = self.get_quote(ticker)
        if quote:
            # Use midpoint of bid/ask for fair price
            return (quote.bid_price + quote.ask_price) / 2
        return 0.0
    
    def submit_market_order(self, ticker: str, qty: int, side: str = "buy"):
        """Submit a simple market order."""
        order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
        
        order_data = MarketOrderRequest(
            symbol=ticker,
            qty=qty,
            side=order_side,
            time_in_force=TimeInForce.DAY
        )
        return self.trading.submit_order(order_data)
    
    def submit_bracket_order(self, ticker: str, qty: int, stop_loss_pct: float = 0.05, take_profit_pct: float = 0.10, current_price: float = None):
        """
        Submit a bracket order (Market + Stop Loss + Take Profit).
        
        Args:
            ticker: Stock symbol
            qty: Number of shares
            stop_loss_pct: Stop loss percentage (default 5%)
            take_profit_pct: Take profit percentage (default 10%)
            current_price: Optional override for limit calculations (useful if live price unavailable)
        """
        # Get current price if not provided
        if current_price is None or current_price <= 0:
            current_price = self.get_live_price(ticker)
        
        if current_price == 0:
            raise ValueError(f"Could not get price for {ticker}")
        
        stop_price = round(current_price * (1 - stop_loss_pct), 2)
        take_profit_price = round(current_price * (1 + take_profit_pct), 2)
        
        # Ensure prices are valid (min 0.01)
        stop_price = max(0.01, stop_price)
        take_profit_price = max(0.01, take_profit_price)
        
        order_data = MarketOrderRequest(
            symbol=ticker,
            qty=qty,
            side=OrderSide.BUY,
            time_in_force=TimeInForce.GTC,
            order_class=OrderClass.BRACKET,
            stop_loss=StopLossRequest(stop_price=stop_price),
            take_profit={"limit_price": take_profit_price}
        )
        return self.trading.submit_order(order_data)


# Singleton instance
_client = None

def get_alpaca_client() -> AlpacaClient:
    """Get or create Alpaca client singleton."""
    global _client
    if _client is None:
        _client = AlpacaClient()
    return _client


if __name__ == "__main__":
    print("Testing Alpaca Client...")
    try:
        client = get_alpaca_client()
        account = client.get_account()
        print(f"✅ Connected! Equity: ${float(account.equity):,.2f}")
    except Exception as e:
        print(f"❌ Error: {e}")
