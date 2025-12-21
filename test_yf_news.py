import yfinance as yf
import json

def test_yf_news():
    print("Fetching News for AAPL via yfinance...")
    try:
        t = yf.Ticker("AAPL")
        news = t.news
        
        print(f"Items found: {len(news)}")
        if news:
            print("--- First Item ---")
            print(json.dumps(news[0], indent=2))
            
            # Simple Sentiment Check
            titles = [n.get('title', '') for n in news]
            print("\nRecent Titles:")
            for title in titles[:5]:
                print(f"- {title}")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_yf_news()
