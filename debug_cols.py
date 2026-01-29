"""Debug Columns"""
import yfinance as yf
ticker = 'NVDA'
stock = yf.Ticker(ticker)
df = stock.insider_transactions
if df is not None:
    print(list(df.columns))
    print(df.head(1).to_dict())
