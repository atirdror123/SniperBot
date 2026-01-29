"""Quick test of AI parsing for one stock"""
import yfinance as yf
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

# Get AAPL insider data
stock = yf.Ticker('AAPL')
trans = stock.insider_transactions

print("=== RAW YAHOO DATA ===")
print(trans.head(8).to_string())

# AI Parse
raw = trans.head(10).to_string()

prompt = f"""Analyze this insider trading data for AAPL.
Return ONLY a JSON object with these exact keys:
- sentiment: integer from -100 to 100 (-100=heavy selling, 0=neutral, 100=heavy buying)
- buys: number of buy transactions
- sells: number of sell transactions  
- executive_buys: true if CEO/CFO/executives bought, false otherwise

Data:
{raw}

Return ONLY valid JSON, no markdown or explanation."""

print("\n=== AI PARSING ===")
try:
    response = model.generate_content(prompt)
    print(f"Raw response: {response.text}")
    
    txt = response.text.strip()
    if '```' in txt:
        txt = txt.split('```')[1].replace('json','').strip()
    
    result = json.loads(txt)
    print(f"\nParsed result:")
    print(json.dumps(result, indent=2))
except Exception as e:
    print(f"ERROR: {e}")
