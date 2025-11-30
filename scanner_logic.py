import yfinance as yf
import pandas as pd

class SniperScorer:
    def __init__(self):
        pass

    def analyze_stock(self, ticker: str) -> dict:
        """
        Analyzes a stock based on technical indicators and returns a score.
        """
        score = 0
        details = []
        
        try:
            stock = yf.Ticker(ticker)
            # Fetch 1 year of history to ensure enough data for SMA200
            hist = stock.history(period="1y")
            
            if hist.empty:
                return {'ticker': ticker, 'final_score': 0, 'details': "No data found"}

            current_price = hist['Close'].iloc[-1]
            
            # Hard Filter: Price < $2
            if current_price < 2:
                return {'ticker': ticker, 'final_score': 0, 'details': f"Price ${current_price:.2f} < $2 (Hard Filter)"}

            # --- Calculations ---
            
            # 1. MA Stack (SMA20 > SMA50 > SMA200)
            if len(hist) >= 200:
                sma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
                sma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
                sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
                
                if sma20 > sma50 > sma200:
                    score += 30
                    details.append("MA Stack (20>50>200): +30")
                else:
                    details.append(f"No MA Stack (20={sma20:.2f}, 50={sma50:.2f}, 200={sma200:.2f})")
            else:
                details.append("Not enough data for MA Stack")

            # 2. Relative Volume (RVOL)
            # Today's Vol / Avg 14-day Vol
            if len(hist) >= 15: # Need at least 14 days prior + today
                today_vol = hist['Volume'].iloc[-1]
                avg_vol_14 = hist['Volume'].iloc[-15:-1].mean() # Exclude today for average? Or include? 
                # Usually RVOL compares today vs average of PAST days.
                # Let's use last 14 days excluding today if possible, or just rolling mean.
                # Requirement: "Avg 14-day Vol".
                
                if avg_vol_14 > 0:
                    rvol = today_vol / avg_vol_14
                    if rvol > 1.5:
                        score += 20
                        details.append(f"RVOL {rvol:.2f} > 1.5: +20")
                    else:
                        details.append(f"RVOL {rvol:.2f} <= 1.5")
                else:
                     details.append("Avg Vol is 0")
            else:
                details.append("Not enough data for RVOL")

            # 3. Trend: Price within 5% of 52-Week High
            high_52w = hist['High'].max()
            if current_price >= high_52w * 0.95:
                score += 20
                details.append(f"Price within 5% of 52w High ({high_52w:.2f}): +20")
            else:
                details.append(f"Price not near 52w High ({high_52w:.2f})")

            # 4. Stability: ATR(14) < 5% of Price
            if len(hist) >= 15:
                # ATR Calculation
                high_low = hist['High'] - hist['Low']
                high_close = (hist['High'] - hist['Close'].shift()).abs()
                low_close = (hist['Low'] - hist['Close'].shift()).abs()
                
                ranges = pd.concat([high_low, high_close, low_close], axis=1)
                true_range = ranges.max(axis=1)
                atr_14 = true_range.rolling(window=14).mean().iloc[-1]
                
                atr_threshold = current_price * 0.05
                if atr_14 < atr_threshold:
                    score += 10
                    details.append(f"ATR ({atr_14:.2f}) < 5% Price ({atr_threshold:.2f}): +10")
                else:
                    details.append(f"ATR ({atr_14:.2f}) >= 5% Price")
            else:
                details.append("Not enough data for ATR")

            # 5. News Sentiment Analysis
            sentiment_score = self._analyze_sentiment(stock)
            score += sentiment_score
            if sentiment_score > 0:
                details.append(f"Positive News Sentiment: +{sentiment_score}")
            elif sentiment_score < 0:
                details.append(f"Negative News Sentiment: {sentiment_score}")
            else:
                details.append("Neutral/No News Sentiment")

            # 6. Analyst Data
            try:
                info = stock.info
                target_price = info.get('targetMeanPrice')
                recommendation = info.get('recommendationKey', '').lower()
                
                # Treat None as missing data (neutral)
                if target_price is not None:
                    # Upside Potential > 20%
                    if target_price > current_price * 1.20:
                        score += 10
                        details.append(f"Analyst Upside > 20% (Target ${target_price}): +10")
                    
                    # Overvaluation Risk
                    elif current_price > target_price:
                        score -= 10
                        details.append(f"Price > Analyst Target (${target_price}): -10")
                
                # Analyst Sentiment
                if recommendation in ['buy', 'strong_buy']:
                    score += 5
                    details.append(f"Analyst Rating '{recommendation}': +5")
                    
            except Exception:
                details.append("No Analyst Data")

            return {
                'ticker': ticker,
                'final_score': score,
                'details': "; ".join(details)
            }

        except Exception as e:
            return {'ticker': ticker, 'final_score': 0, 'details': f"Error: {str(e)}"}

    def _analyze_sentiment(self, stock) -> int:
        """
        Analyzes news sentiment using keyword matching.
        Returns sentiment score adjustment.
        """
        positive_keywords = ["upgrade", "buy", "surge", "jump", "growth", "beat", "record", "bull"]
        negative_keywords = ["downgrade", "sell", "drop", "miss", "loss", "lawsuit", "crash"]
        
        sentiment_score = 0
        
        try:
            news = stock.news
            if not news:
                return 0
            
            # Analyze last 3 news items
            for item in news[:3]:
                title = item.get('title', '').lower()
                
                # Check for positive keywords
                for keyword in positive_keywords:
                    if keyword in title:
                        sentiment_score += 10
                        break  # Only count once per article
                
                # Check for negative keywords
                for keyword in negative_keywords:
                    if keyword in title:
                        sentiment_score -= 20
                        break  # Only count once per article
            
            return sentiment_score
            
        except Exception as e:
            # If news fetching fails, return neutral
            return 0
