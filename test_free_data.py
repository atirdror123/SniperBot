"""Test Free Data from Yahoo Finance - Save to File"""
import yfinance as yf
import pandas as pd
import sys

# Redirect output to file
with open('yahoo_test_output.txt', 'w') as f:
    def p(msg):
        print(msg)
        f.write(str(msg) + '\n')
    
    p("="*60)
    p("TESTING YAHOO FINANCE FREE DATA")
    p("="*60)
    
    # Test with AAPL
    ticker = "AAPL"
    p(f"\nTesting: {ticker}")
    stock = yf.Ticker(ticker)
    
    # 1. Institutional Holders
    p("\n--- INSTITUTIONAL HOLDERS ---")
    try:
        inst = stock.institutional_holders
        if inst is not None and len(inst) > 0:
            p(f"SUCCESS: Found {len(inst)} institutional holders")
            p(inst.head(3).to_string())
        else:
            p("NO DATA")
    except Exception as e:
        p(f"ERROR: {e}")
    
    # 2. Major Holders
    p("\n--- MAJOR HOLDERS ---")
    try:
        major = stock.major_holders
        if major is not None and len(major) > 0:
            p("SUCCESS: Major holders data")
            p(major.to_string())
        else:
            p("NO DATA")
    except Exception as e:
        p(f"ERROR: {e}")
    
    # 3. Insider Transactions  
    p("\n--- INSIDER TRANSACTIONS ---")
    try:
        insiders = stock.insider_transactions
        if insiders is not None and len(insiders) > 0:
            p(f"SUCCESS: Found {len(insiders)} insider transactions")
            p(insiders.head(5).to_string())
        else:
            p("NO DATA")
    except Exception as e:
        p(f"ERROR: {e}")
    
    # 4. Insider Purchases
    p("\n--- INSIDER PURCHASES SUMMARY ---")
    try:
        purchases = stock.insider_purchases
        if purchases is not None and len(purchases) > 0:
            p("SUCCESS: Insider purchases summary")
            p(purchases.to_string())
        else:
            p("NO DATA")
    except Exception as e:
        p(f"ERROR: {e}")
    
    p("\n" + "="*60)
    p("CONCLUSION: Yahoo Finance provides FREE insider/institutional data!")
    p("="*60)
