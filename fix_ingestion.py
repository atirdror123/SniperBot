import yfinance as yf
import pandas as pd

t = "AAPL"
tick = yf.Ticker(t)

print("--- DEBUG QUANT ---")
holders = tick.major_holders
print(holders)
# Robust Logic:
try:
    # Try iloc 1 (Institutions %)
    val = holders.iloc[1, 1] # Row 1, Col 1 (Value)
    print(f"Row 1 Col 1 Value: {val}")
    
    # Clean string
    if isinstance(val, str):
        val = float(val.replace('%', '')) / 100.0
    print(f"Parsed Float: {val}")
    
    if val > 0.40:
        print("PASS: Inst Buying > 40%")
except Exception as e:
    print(f"Quant Error: {e}")

print("\n--- DEBUG HUNTER ---")
trans = tick.insider_transactions
if trans is not None:
    print(f"Cols: {trans.columns}")
    # Check first 5 rows 'Transaction' and 'Text'
    for i in range(5):
        row = trans.iloc[i]
        print(f"Row {i}: Trans='{row.get('Transaction')}' Text='{row.get('Text')}'")
