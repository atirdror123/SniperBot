import os
from dotenv import load_dotenv
from supabase import create_client, Client
from scanner_logic import SniperScorer
import yfinance as yf

# Load environment variables
load_dotenv()

def analyze_single_ticker(ticker):
    """Analyze a single ticker and print detailed results"""
    scorer = SniperScorer()
    
    print(f"Analyzing {ticker}...")
    print("="*60)
    
    result = scorer.analyze_stock(ticker)
    score = result['final_score']
    
    # Get current price
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1d")
        entry_price = hist['Close'].iloc[-1] if not hist.empty else 0.0
    except:
        entry_price = 0.0
    
    # Print detailed results
    print(f"\n>>> TICKER: {ticker}")
    print(f">>> Final Score: {score}")
    print(f">>> Entry Price: ${entry_price:.2f}")
    print(f">>> Threshold: 75 (Pass: {'YES' if score > 75 else 'NO'})")
    print(f"\n>>> Detailed Breakdown:")
    for reason in result['details'].split('; '):
        print(f"    - {reason}")
    print("="*60)
    
    return result, entry_price

if __name__ == "__main__":
    ticker = "A"  # Agilent Technologies
    analyze_single_ticker(ticker)
