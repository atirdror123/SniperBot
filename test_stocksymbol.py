from stocksymbol import StockSymbol

try:
    api_key = '' # No key provided
    ss = StockSymbol(api_key)
    symbol_list_us = ss.get_symbol_list(market="US")
    print(f"Success! Found {len(symbol_list_us)} symbols.")
    print(symbol_list_us[:5])
except Exception as e:
    print(f"Error: {e}")
