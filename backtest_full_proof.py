"""
Full Proof of Concept - Slow & Steady
-------------------------------------
Tests ALL 3 AI Lenses on 3 diverse stocks.
Uses 60s delays to GUARANTEE we bypass rate limits.
This will take ~6-10 minutes to run.

LENSES:
1. HUNTER (Insider Sentiment) - Parses transaction text
2. QUANT (Institutional Quality) - Parses holder table
3. ORACLE (Overall Sentiment) - Synthesizes both
"""
import os
import time
import json
import warnings
from datetime import datetime
from dotenv import load_dotenv
import pandas as pd
import yfinance as yf
import google.generativeai as genai

warnings.filterwarnings('ignore')
load_dotenv()

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))
# Use flash model for speed/cost
model = genai.GenerativeModel('gemini-2.0-flash')

STOCKS = [
    'NVDA', # High Growth, heavily traded
    'PLTR', # Retail favorite, controversial insider selling
    'PFE'   # Boring Value, stable
]

def get_data(ticker):
    print(f"  Fetching data for {ticker}...")
    stock = yf.Ticker(ticker)
    
    # Insider
    insider = ""
    try:
        if stock.insider_transactions is not None:
            insider = stock.insider_transactions.head(20).to_string()
    except: pass
    
    # Institutional
    inst = ""
    try:
        if stock.institutional_holders is not None:
            inst = stock.institutional_holders.head(10).to_string()
    except: pass
    
    return {'insider': insider, 'institutional': inst}

def get_hunter_score(ticker, text):
    if not text: return 0, "No Data"
    prompt = f"""Analyze {ticker} INSIDER TRANSACTIONS.
Determine sentiment (-100 to +100).
-100 = Panic Selling
0 = Neutral / Routine / Gifts / Options
+100 = Aggressive Buying

Data:
{text[:2000]}

Return JSON: {{ "score": <int>, "reason": "string" }}"""
    try:
        res = model.generate_content(prompt)
        js = json.loads(res.text.replace('```json','').replace('```','').strip())
        return js.get('score', 0), js.get('reason', 'Parsed')
    except Exception as e:
        return 0, str(e)

def get_quant_score(ticker, text):
    if not text: return 0, "No Data"
    prompt = f"""Analyze {ticker} INSTITUTIONAL HOLDERS.
Score the "Quality" of ownership (0-100).
Higher score for: Top funds (Vanguard, Blackrock), increasing positions.
Lower score for: Unknown holders, decreasing positions.

Data:
{text[:2000]}

Return JSON: {{ "score": <int>, "reason": "string" }}"""
    try:
        res = model.generate_content(prompt)
        js = json.loads(res.text.replace('```json','').replace('```','').strip())
        return js.get('score', 0), js.get('reason', 'Parsed')
    except Exception as e:
        return 0, str(e)

def get_oracle_score(ticker, insider, inst):
    prompt = f"""Synthesize a FORECAST score (-100 to +100) for {ticker}.
Based on:
Insider: {insider[:1000]}
Institutional: {inst[:1000]}

Return JSON: {{ "score": <int>, "reason": "string" }}"""
    try:
        res = model.generate_content(prompt)
        js = json.loads(res.text.replace('```json','').replace('```','').strip())
        return js.get('score', 0), js.get('reason', 'Parsed')
    except Exception as e:
        return 0, str(e)

def run():
    print("="*60)
    print("SLOW & STEADY PROOF OF CONCEPT (3 STOCKS)")
    print("="*60)
    
    results = []
    
    for i, ticker in enumerate(STOCKS):
        print(f"\nProcessing {ticker} [{i+1}/{len(STOCKS)}]")
        
        # 1. Fetch
        data = get_data(ticker)
        
        # 2. HUNTER
        if i > 0: 
            print("  Waiting 60s (Rate Limit)...")
            time.sleep(60)
        
        hunter, h_reason = get_hunter_score(ticker, data['insider'])
        print(f"  HUNTER: {hunter} ({h_reason})")
        
        # 3. QUANT
        print("  Waiting 60s (Rate Limit)...")
        time.sleep(60)
        quant, q_reason = get_quant_score(ticker, data['institutional'])
        print(f"  QUANT:  {quant} ({q_reason})")
        
        # 4. ORACLE
        print("  Waiting 60s (Rate Limit)...")
        time.sleep(60)
        oracle, o_reason = get_oracle_score(ticker, data['insider'], data['institutional'])
        print(f"  ORACLE: {oracle} ({o_reason})")
        
        results.append({
            'Ticker': ticker,
            'HUNTER': hunter,
            'QUANT': quant,
            'ORACLE': oracle,
            'H_Reason': h_reason,
            'Q_Reason': q_reason,
            'O_Reason': o_reason
        })
        
    print("\n" + "="*60)
    print("FINAL PROOF RESULTS")
    print("="*60)
    df = pd.DataFrame(results)
    print(df[['Ticker', 'HUNTER', 'QUANT', 'ORACLE']])
    
    # Valid Non-Zero Check
    non_zeros = df[['HUNTER', 'QUANT', 'ORACLE']].astype(bool).sum().sum()
    total_cells = len(df) * 3
    print(f"\nNon-Zero Scores: {non_zeros}/{total_cells}")
    
    if non_zeros > total_cells * 0.5:
        print("✅ SUCCESS: AI Lens System is generating data-based scores!")
    else:
        print("❌ FAILURE: Still getting too many zeros.")
        
    df.to_csv('full_proof_results.csv', index=False)

if __name__ == "__main__":
    run()
