"""
Test script for Google Gemini AI integration in scanner_logic.py

This script tests the AI-powered sentiment analysis feature.
Make sure to set GOOGLE_API_KEY in your .env file before running.
"""

import os
from dotenv import load_dotenv
from scanner_logic import SniperScorer

# Load environment variables
load_dotenv()

def test_ai_sentiment():
    print("=" * 60)
    print("Testing Google Gemini AI Integration")
    print("=" * 60)
    
    # Check if API key is set
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("\n⚠️  WARNING: GOOGLE_API_KEY not found in environment variables")
        print("The AI sentiment analysis will be skipped.")
        print("\nTo enable AI analysis:")
        print("1. Add GOOGLE_API_KEY=your_key_here to your .env file")
        print("2. Get your API key from: https://makersuite.google.com/app/apikey")
    else:
        print(f"\n✅ GOOGLE_API_KEY found (length: {len(api_key)} chars)")
    
    print("\n" + "-" * 60)
    print("Testing with ticker: NVDA")
    print("-" * 60)
    
    # Initialize scorer
    scorer = SniperScorer()
    
    # Analyze stock
    result = scorer.analyze_stock("NVDA")
    
    # Display results
    print(f"\n📊 Analysis Results for {result['ticker']}:")
    print(f"   Final Score: {result['final_score']}")
    print(f"\n📝 Details:")
    print(f"   {result['details']}")
    
    if 'ai_score' in result:
        print(f"\n🤖 AI Sentiment Analysis:")
        print(f"   Score: {result['ai_score']:+d}")
        print(f"   Reason: {result['ai_reason']}")
    
    print("\n" + "=" * 60)
    print("Test Complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_ai_sentiment()
