"""
Simplified test script for Google Gemini AI integration (Deep Analysis)
"""

import os
from dotenv import load_dotenv
from scanner_logic import SniperScorer

load_dotenv()

def main():
    print("=" * 60)
    print("Google Gemini AI Deep Analysis Test")
    print("=" * 60)
    
    # Check API key
    print(f"Current working directory: {os.getcwd()}")
    print(f"Environment variables loaded: {list(os.environ.keys())}")
    
    # Try loading explicitly
    from pathlib import Path
    env_path = Path('.') / '.env'
    load_dotenv(dotenv_path=env_path)
    
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\nERROR: GOOGLE_API_KEY not found in .env")
        # Check what keys ARE there
        import dotenv
        config = dotenv.dotenv_values(".env")
        print(f"Keys in .env file: {list(config.keys())}")
        return
    
    print(f"\nAPI Key: Found ({len(api_key)} chars)")
    
    # Test with NVDA
    print("\nTesting with ticker: NVDA")
    print("-" * 60)
    
    scorer = SniperScorer()
    
    # Force AI enabled for test even if key check fails in class (it shouldn't if env is loaded)
    scorer.ai_enabled = True 
    
    result = scorer.analyze_stock("NVDA")
    
    print(f"\nTicker: {result['ticker']}")
    print(f"Final Score: {result['final_score']}")
    print(f"\nAI Score: {result.get('ai_score', 'N/A')}")
    print(f"AI Reason: {result.get('ai_reason', 'N/A')}")
    print(f"\nDetails:\n{result['details']}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
