import yfinance as yf
import pandas as pd

t = "AAPL"
tick = yf.Ticker(t)
holders = tick.major_holders

print("--- TESTING QUANT LOGIC ---")
print("Holders DF:")
print(holders)

s_holders = holders.astype(str)
for idx, row in s_holders.iterrows():
    line_str = " ".join(row.values)
    print(f"\nRow {idx} Line: '{line_str}'")
    
    if "institutionsPercentHeld" in line_str or "Institutions" in line_str:
        print("  MATCHED KEYWORD")
        for col in holders.columns:
            val = holders.loc[idx, col]
            print(f"    Col {col} Val: {val} (Type: {type(val)})")
            try:
                f_val = float(val)
                print(f"    -> Float: {f_val}")
                if f_val > 0.60:
                    print("    *** SUPER BULLISH (>0.60) ***")
            except:
                print("    -> Not a Float")
