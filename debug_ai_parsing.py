"""Debug the AI parsing - save all output to file."""
import os
import json
import warnings
import sys
from dotenv import load_dotenv

warnings.filterwarnings('ignore')
load_dotenv()

# Redirect to file
output_file = open('debug_output.txt', 'w', encoding='utf-8')
def log(msg):
    print(msg)
    output_file.write(str(msg) + '\n')
    output_file.flush()

import yfinance as yf
import google.generativeai as genai

GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
log(f"API Key present: {bool(GOOGLE_API_KEY)}")

genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# Test with AAPL
ticker = 'AAPL'
log(f"\n{'='*50}")
log(f"Testing {ticker}")
log('='*50)

# 1. Get Yahoo data
stock = yf.Ticker(ticker)

log("\n1. Insider Transactions:")
insider_text = ""
try:
    insider = stock.insider_transactions
    if insider is not None and not insider.empty:
        log(f"   Found {len(insider)} rows")
        insider_text = insider.to_string()
        log(insider.head(3).to_string())
    else:
        log("   No insider data")
except Exception as e:
    log(f"   Error: {e}")

log("\n2. Major Holders:")
holders_text = ""
try:
    holders = stock.major_holders
    if holders is not None and not holders.empty:
        holders_text = holders.to_string()
        log(holders_text)
    else:
        log("   No holders data")
except Exception as e:
    log(f"   Error: {e}")

has_data = bool(insider_text or holders_text)
log(f"\nHas data: {has_data}")

if not has_data:
    log("PROBLEM: No data from Yahoo!")
    output_file.close()
    sys.exit(1)

# 4. Test AI parsing (with delay for rate limit)
log("\n4. Testing AI Parsing...")
import time
log("Waiting 5 seconds for rate limit...")
time.sleep(5)

prompt = f"""Analyze this stock data for AAPL and return ONLY a JSON object.

INSIDER TRANSACTIONS:
{insider_text[:1000] if insider_text else 'No data'}

MAJOR HOLDERS:
{holders_text[:300] if holders_text else 'No data'}

Return ONLY valid JSON, nothing else:
{{"insider_sentiment": -100 to +100, "insider_buys": count, "insider_sells": count}}"""

log(f"\nPrompt length: {len(prompt)} chars")

try:
    response = model.generate_content(prompt)
    log(f"\nRaw response:")
    log(response.text)
    
    # Try to parse
    text = response.text.strip()
    
    # Clean markdown
    if '```' in text:
        start = text.find('{')
        end = text.rfind('}') + 1
        if start != -1 and end > start:
            text = text[start:end]
    
    log(f"\nCleaned: {text}")
    
    data = json.loads(text)
    log(f"\nSUCCESS! Parsed: {data}")
        
except Exception as e:
    log(f"\nERROR: {type(e).__name__}: {e}")

output_file.close()
print("\nOutput saved to debug_output.txt")
