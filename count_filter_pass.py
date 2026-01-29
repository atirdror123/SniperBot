"""
Quick test to see how many stocks pass the Pressure Cooker filter.
This helps determine the feasibility of AI parsing costs.
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_ingestion import DataIngestor
from sniper_scanner import get_stock_data
from pressure_cooker import pressure_cooker_filter

def count_pressure_cooker_pass():
    """Count how many stocks pass the pressure cooker filter."""
    ingestor = DataIngestor()
    universe = ingestor.fetch_universe()
    
    if not universe:
        print("Failed to fetch universe!")
        return
    
    print(f"Universe size: {len(universe)} stocks")
    print("\nRunning Pressure Cooker filter...")
    
    passed = 0
    failed_data = 0
    failed_filter = 0
    
    for i, ticker in enumerate(universe):
        if i % 100 == 0:
            print(f"  Progress: {i}/{len(universe)} | Passed so far: {passed}")
        
        try:
            df = get_stock_data(ticker, period="6mo")
            if df.empty or len(df) < 50:
                failed_data += 1
                continue
            
            result = pressure_cooker_filter(df, ticker)
            
            if result['passes']:
                passed += 1
            else:
                failed_filter += 1
        
        except Exception as e:
            failed_data += 1
    
    print("\n" + "=" * 50)
    print("PRESSURE COOKER FILTER RESULTS")
    print("=" * 50)
    print(f"Total Universe:     {len(universe)}")
    print(f"Failed Data/Short:  {failed_data}")
    print(f"Failed Filter:      {failed_filter}")
    print(f"PASSED FILTER:      {passed}")
    print(f"\nPass Rate: {passed/len(universe)*100:.2f}%")
    print("=" * 50)
    
    # Cost analysis for AI parsing
    print("\n📊 AI PARSING COST ANALYSIS:")
    print("-" * 40)
    print(f"Stocks needing AI parsing: {passed}")
    print(f"Gemini Free Tier (15 req/min): Would take {passed/15:.1f} minutes")
    print(f"Gemini Paid (~$0.10/1000 req): ~${passed*0.0001:.4f} per scan")
    print(f"FMP Ultimate ($99/month): Flat rate, unlimited API calls")

if __name__ == "__main__":
    count_pressure_cooker_pass()
