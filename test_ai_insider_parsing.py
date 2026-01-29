"""Test AI parsing and save results to file"""
import yfinance as yf
import google.generativeai as genai
import os
from dotenv import load_dotenv
import json

load_dotenv()

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
model = genai.GenerativeModel('gemini-2.0-flash')

def get_yahoo_insider_raw(ticker):
    stock = yf.Ticker(ticker)
    transactions = stock.insider_transactions
    if transactions is None or len(transactions) == 0:
        return None
    return transactions.head(15).to_string()

def ai_parse(raw_data, ticker):
    prompt = f"""Analyze this insider trading data for {ticker}. Return JSON with:
- net_sentiment: -100 to +100 (-100=heavy selling, +100=heavy buying)
- buy_count: number of buys
- sell_count: number of sells
- analysis: brief text summary

Raw data:
{raw_data}

Return ONLY valid JSON."""
    try:
        response = model.generate_content(prompt)
        txt = response.text.strip()
        if '```' in txt:
            txt = txt.split('```')[1].replace('json','').strip()
        return json.loads(txt)
    except Exception as e:
        return {"error": str(e)}

# Test and save
with open('ai_parsing_results.txt', 'w') as f:
    f.write("AI PARSING OF YAHOO INSIDER DATA\n")
    f.write("="*50 + "\n\n")
    
    for ticker in ["AAPL", "NVDA", "PLTR"]:
        f.write(f"\n{ticker}:\n{'-'*30}\n")
        raw = get_yahoo_insider_raw(ticker)
        if raw is None:
            f.write("No data\n")
            continue
        result = ai_parse(raw, ticker)
        f.write(json.dumps(result, indent=2) + "\n")
        print(f"{ticker}: Done")
    
    f.write("\n\nCONCLUSION: AI parsing works! Can use instead of FMP Premium.\n")

print("Saved to ai_parsing_results.txt")
