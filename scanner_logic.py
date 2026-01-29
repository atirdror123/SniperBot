import yfinance as yf
import pandas as pd
import os
import json
import time
import logging
import google.generativeai as genai
from supabase import create_client
from scan_logger import get_logger

# Suppress YFinance HTTP 404 error spam for ETFs/non-stocks
logging.getLogger("yfinance").setLevel(logging.CRITICAL)
logging.getLogger("urllib3").setLevel(logging.WARNING)

logger = get_logger("SCANNER_LOGIC")

class SniperScorer:
    # Constants for retry logic
    MAX_RETRIES = 3
    RETRY_BACKOFF = 2  # seconds
    
    def __init__(self):
        # Initialize Gemini AI
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            self.ai_enabled = True
        else:
            self.ai_enabled = False

        # Initialize Supabase for Config
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
        self.weights = {
            'w_trend': 0.40, 
            'w_volatility': 0.30, 
            'w_fundamental': 0.15, 
            'w_sentiment': 0.15
        }
        
        if url and key:
            try:
                supabase = create_client(url, key)
                response = supabase.table('bot_config').select('*').eq('config_key', 'global_strategy').execute()
                if response.data:
                    config = response.data[0]
                    self.weights['w_trend'] = config.get('w_trend', 0.40)
                    self.weights['w_volatility'] = config.get('w_volatility', 0.30)
                    self.weights['w_fundamental'] = config.get('w_fundamental', 0.15)
                    self.weights['w_sentiment'] = config.get('w_sentiment', 0.15)
                    logger.info(f"Loaded Dynamic Weights: {self.weights}")
            except Exception as e:
                logger.warning(f"Failed to load bot_config, using defaults: {e}")

        # Map Sectors to SPDR ETFs
        self.sector_etf_map = {
            "Technology": "XLK",
            "Financial Services": "XLF", 
            "Healthcare": "XLV",
            "Consumer Cyclical": "XLY",
            "Consumer Defensive": "XLP",
            "Energy": "XLE",
            "Utilities": "XLU",
            "Industrials": "XLI",
            "Basic Materials": "XLB",
            "Real Estate": "XLRE",
            "Communication Services": "XLC"
        }
        
        # Pre-fetch Sector Trends
        self._prefetch_sector_trends()

    def _fetch_history_with_retry(self, ticker: str, period: str = "1y") -> pd.DataFrame:
        """
        Fetches historical data with retry logic and exponential backoff.
        Returns empty DataFrame on complete failure.
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period=period)
                
                # VALIDATION: Ensure we got data
                if not hist.empty:
                    return hist
                else:
                    logger.warning(f"{ticker}: Empty history on attempt {attempt}")
                    
            except Exception as e:
                logger.warning(f"{ticker}: YF error on attempt {attempt}: {type(e).__name__}: {e}")
            
            if attempt < self.MAX_RETRIES:
                time.sleep(self.RETRY_BACKOFF * attempt)
        
        return pd.DataFrame()  # Return empty on failure

    def analyze_stock(self, ticker: str, data: pd.DataFrame = None) -> dict:
        """
        Analyzes a stock based on Weighted Technical Indicators.
        Returns score, details, and raw_features.
        """
        # Initialize Sub-Scores (0-100 scale)
        s_trend = 0
        s_vol = 0
        s_fund = 0
        s_sent = 0
        
        details = []
        raw_features = {}
        ai_reason = "No AI analysis"
        is_backtest = data is not None
        
        # Initialize Ticker object for fundamental/sector data
        stock = yf.Ticker(ticker)
        
        try:
            if is_backtest:
                hist = data
                if len(hist) < 200:
                     return {'ticker': ticker, 'final_score': 0, 'details': "Not enough historical data (Backtest)"}
            else:
                # Use retry-enabled fetch
                hist = self._fetch_history_with_retry(ticker, period="1y")
            
            if hist.empty:
                return {'ticker': ticker, 'final_score': 0, 'details': "No data found (after retries)"}

            current_price = hist['Close'].iloc[-1]
            
            # Feature: Price < $2 (Hard Filter)
            if current_price < 2:
                return {'ticker': ticker, 'final_score': 0, 'details': f"Price ${current_price:.2f} < $2 (Hard Filter)"}

            # --- 1. TREND COMPONENT (Target: 100) ---
            # A. MA Stack (SMA20 > SMA50 > SMA200) -> 60 pts
            sma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
            sma50 = hist['Close'].rolling(window=50).mean().iloc[-1]
            sma200 = hist['Close'].rolling(window=200).mean().iloc[-1]
            
            raw_features['sma20'] = sma20
            raw_features['sma50'] = sma50
            raw_features['sma200'] = sma200
            
            # [HARD FILTER] Price must be above SMA200 (Long Term Trend)
            if current_price < sma200:
                 return {'ticker': ticker, 'final_score': 0, 'details': f"Price Below SMA200 (Bear Trend)", 'raw_features': raw_features}
            
            if sma20 > sma50 > sma200:
                s_trend += 60
                details.append("MA Stack (20>50>200): +Trend")
            else:
                details.append(f"No MA Stack")

            # B. Price vs 52w High -> 40 pts
            high_52w = hist['High'].max()
            raw_features['high_52w'] = high_52w
            
            if current_price >= high_52w * 0.95:
                s_trend += 40
                details.append(f"Near 52w High: +Trend")
            
            # C. Sector Penalty/Bonus (Impacts Trend Score)
            # Fetch Sector
            try:
                sector = stock.info.get('sector') if not is_backtest else "Unknown" 
                # Note: In backtest we skip sector usually, or need to mock info.
                
                if sector and sector != "Unknown":
                    # ... (Existing Sector Logic) ...
                    etf = self.sector_etf_map.get(sector)
                    # Simple fuzzy match fallback
                    if not etf:
                         for k, v in self.sector_etf_map.items():
                            if k.lower() in sector.lower():
                                etf = v
                                break
                                
                    if etf:
                         etf_status = self.sector_status.get(etf, 'Unknown')
                         raw_features['sector_status'] = etf_status
                         if etf_status == 'Weak':
                             s_trend -= 30 # Heavy penalty on trend
                             details.append(f"⚠️ Sector {etf} is in Downtrend (-Trend)")
                         elif etf_status == 'Strong':
                             s_trend += 10
                             details.append(f"Sector {etf} is Strong (+Trend)")
            except Exception:
                pass

            # Cap Trend Score
            s_trend = max(0, min(100, s_trend))


            # --- 2. VOLATILITY COMPONENT (Target: 100) ---
            # A. RVOL -> 60 pts
            if len(hist) >= 15:
                today_vol = hist['Volume'].iloc[-1]
                avg_vol_14 = hist['Volume'].iloc[-15:-1].mean()
                rvol = today_vol / avg_vol_14 if avg_vol_14 > 0 else 0
                raw_features['rvol'] = rvol
                
                if rvol > 1.5:
                    s_vol += 60
                    details.append(f"RVOL {rvol:.1f} > 1.5: +Vol")
            
            # B. ATR Stability -> 40 pts
            if len(hist) >= 15:
                 high_low = hist['High'] - hist['Low']
                 high_close = (hist['High'] - hist['Close'].shift()).abs()
                 low_close = (hist['Low'] - hist['Close'].shift()).abs()
                 true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                 atr_14 = true_range.rolling(window=14).mean().iloc[-1]
                 
                 atr_pct = atr_14 / current_price
                 raw_features['atr_pct'] = atr_pct
                 
                 if atr_pct < 0.05:
                     s_vol += 40
                     details.append(f"ATR < 5%: +Vol")

            s_vol = max(0, min(100, s_vol))


            # --- 3. FUNDAMENTAL COMPONENT (Target: 100) ---
            # Analyst Upside
            if not is_backtest:
                try:
                    info = stock.info
                    target_price = info.get('targetMeanPrice')
                    recommendation = info.get('recommendationKey', '').lower()
                    
                    raw_features['analyst_target'] = target_price
                    raw_features['recommendation'] = recommendation
                    
                    if target_price:
                        upside = (target_price - current_price) / current_price
                        raw_features['analyst_upside'] = upside
                        
                        if upside > 0.20:
                            s_fund += 60
                            details.append("Analyst Upside > 20%: +Fund")
                        elif current_price > target_price:
                            s_fund -= 20
                            details.append("Price > Analyst Target: -Fund")
                            
                    if recommendation in ['buy', 'strong_buy']:
                        s_fund += 40
                        details.append("Analyst Buy Rating: +Fund")
                        
                except Exception:
                    pass
            
            s_fund = max(0, min(100, s_fund))


            # --- 4. SENTIMENT COMPONENT (Target: 100) ---
            # Combination of News Keywords + AI
            if not is_backtest:
                sentiment_score = self._analyze_sentiment(stock) # Returns -20 to +20 roughly
                # Normalize to 0-100? 
                # Let's say sentiment_score > 0 is good.
                # Map range -20..+20 to 0..100?
                # Simple Logic: Positive = 60, Neutral = 50, Negative = 20?
                
                raw_features['news_sentiment_raw'] = sentiment_score
                
                if sentiment_score > 0:
                    s_sent = 80
                    details.append("Positive News: +Sent")
                elif sentiment_score < 0:
                    s_sent = 20
                    details.append("Negative News: -Sent")
                else:
                    s_sent = 50 # Neutral
            else:
                s_sent = 50 # Default for backtest
            
            # --- 5. EARNINGS FILTER (Penalty on TOTAL) ---
            earnings_penalty = 0
            if not is_backtest:
                # ... (Keep existing Earnings Logic) ...
                try:
                    # (Simplified for brevity - relying on raw logic existing or re-implementing safely)
                    # We can re-use the block from previous step, but let's keep it compact
                    from datetime import datetime
                    today = datetime.now().date()
                    next_earnings_date = None
                    
                    # Strategy A
                    try:
                        cal = stock.calendar
                        if isinstance(cal, dict):
                             dates = cal.get('Earnings Date')
                             if dates:
                                 future_dates = [d for d in dates if d >= today]
                                 if future_dates: next_earnings_date = future_dates[0]
                    except: pass
                    
                    # Strategy B
                    if not next_earnings_date:
                        try:
                            ed_df = stock.earnings_dates
                            if ed_df is not None and not ed_df.empty:
                                future_earnings = ed_df.index[ed_df.index.date >= today]
                                if not future_earnings.empty: next_earnings_date = future_earnings.sort_values()[0].date()
                        except: pass
                    
                    if next_earnings_date:
                        days_until = (next_earnings_date - today).days
                        raw_features['days_to_earnings'] = days_until
                        if days_until <= 7:
                            earnings_penalty = 50
                            details.append(f"🛑 Earnings Risk! Within 7 days (-50 pts)")
                        else:
                            details.append(f"✅ Earnings Safe (Next: {next_earnings_date})")
                except Exception:
                    pass

            # --- FINAL CALCULATION ---
            # Weighted Average
            w = self.weights.copy()
            
            # Adjust weights for backtest (missing Fund/Sent data)
            if is_backtest:
                # Re-distribute Fund/Sent weights to Trend/Vol roughly proportionally
                # Current: Trend 0.3, Vol 0.2 (Total 0.5)
                # New: Trend 0.6, Vol 0.4 (Total 1.0)
                w['w_trend'] = 0.6
                w['w_vol'] = 0.4
                w['w_fundamental'] = 0.0
                w['w_sentiment'] = 0.0
                
            weighted_score = (
                (s_trend * w['w_trend']) +
                (s_vol * w['w_volatility']) +
                (s_fund * w['w_fundamental']) +
                (s_sent * w['w_sentiment'])
            )
            
            # Apply Penalties (Earnings, etc.)
            final_score = weighted_score - earnings_penalty
            final_score = int(max(0, min(100, final_score)))
            
            # AI Check (Only if score high)
            if self.ai_enabled and final_score >= 80 and not is_backtest:
                # ... (Existing AI Logic call) ...
                # Use sub-scores score as base
                try:
                    news = stock.news if stock.news else []
                    tech_summary = "; ".join(details)
                    ai_result = self.get_ai_analysis(ticker, news[:5], tech_summary, final_score)
                    
                    final_score = ai_result.get('score', final_score)
                    ai_reason = ai_result.get('reason', 'AI analysis completed')
                    details.insert(0, f"🤖 AI INSIGHT: {ai_reason}")
                except Exception as e:
                    details.append(f"AI Failed: {e}")
            
            elif is_backtest:
                # details.append("AI Skipped (Backtest)")
                pass

            return {
                'ticker': ticker,
                'final_score': final_score,
                'details': "; ".join(details),
                'ai_reason': ai_reason,
                'raw_features': raw_features # NEW
            }

        except Exception as e:
            return {'ticker': ticker, 'final_score': 0, 'details': f"Error: {str(e)}", 'raw_features': {}}




    def _prefetch_sector_trends(self):
        """
        Prefetches data for all S&P 500 Sector ETFs to determine their trend.
        Uses SMA50 as the trend filter.
        """
        print("Analying Sector Trends (ETF vs SMA50)...")
        self.sector_status = {} # Ticker -> 'Weak' | 'Strong'
        
        # S&P 500 Sector ETFs
        etfs = list(set(self.sector_etf_map.values()))
        
        try:
            # Batch download 6mo data
            data = yf.download(etfs, period="6mo", interval="1d", group_by='ticker', progress=False, threads=True)
            
            for etf in etfs:
                try:
                    if etf not in data.columns.levels[0]:
                        continue
                        
                    df = data[etf]
                    if df.empty or len(df) < 50:
                        continue
                        
                    current_price = df['Close'].iloc[-1]
                    sma50 = df['Close'].rolling(window=50).mean().iloc[-1]
                    
                    if current_price < sma50:
                        self.sector_status[etf] = 'Weak'
                        # print(f"  {etf} is WEAK (< SMA50)")
                    else:
                        self.sector_status[etf] = 'Strong'
                        # print(f"  {etf} is Strong (> SMA50)")
                        
                except Exception:
                    continue
            
            print(f"Sector Trends Updated: {len(self.sector_status)} ETFs analyzed.")
                    
        except Exception as e:
            print(f"Warning: Failed to fetch Sector ETF data: {e}")

    def get_ai_analysis(self, ticker: str, news_list: list, technical_summary: str, base_score: int) -> dict:
        """
        Uses Google Gemini AI to perform a deep analysis of the stock.
        Combines technicals, news, and base score to generate a final conviction score.
        
        Args:
            ticker: Stock ticker symbol
            news_list: List of news items
            technical_summary: String summary of technical indicators
            base_score: The rule-based score calculated so far
        
        Returns:
            dict: {'score': int (0-100), 'reason': str}
        """
        try:
            # Extract headlines
            headlines = [item.get('title', '') for item in news_list if item.get('title')]
            headlines_text = "\n".join([f"- {h}" for h in headlines]) if headlines else "No recent news headlines found."
            
            # Construct prompt
            prompt = f"""Act as a friendly investment assistant. Analyze {ticker} for a potential breakout trade.

CONTEXT:
This stock has passed our strict technical filters with a Base Score of {base_score}/100.
Technical Summary:
{technical_summary}

NEWS HEADLINES:
{headlines_text}

TASK:
1. Evaluate the "Breakout Conviction" score (0-100).
2. Write a SIMPLE, CLEAR summary paragraph explaining WHY this stock is interesting. 
   - Use plain English. Avoid complex jargon.
   - Explain what the technicals and news mean for a normal investor.
   - If there is good news, explain why it matters.
   - Keep it under 60 words.

OUTPUT:
Return ONLY a JSON string with this exact format:
{{"score": <integer 0-100>, "reason": "<Your simple, clear summary paragraph here.>"}}
"""

            # Call Gemini AI
            model = genai.GenerativeModel('gemini-flash-latest')
            response = model.generate_content(prompt)
            
            # Parse JSON response
            response_text = response.text.strip()
            
            # Remove markdown code blocks if present
            if response_text.startswith('```'):
                response_text = response_text.split('```')[1]
                if response_text.startswith('json'):
                    response_text = response_text[4:]
                response_text = response_text.strip()
            
            result = json.loads(response_text)
            
            # Validate score
            score = int(result.get('score', base_score))
            score = max(0, min(100, score))
            
            reason = result.get('reason', 'AI analysis completed.')
            
            return {'score': score, 'reason': reason}
            
        except Exception as e:
            # Fallback to base score if AI fails
            return {'score': base_score, 'reason': f'AI error: {str(e)[:30]}'}

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
