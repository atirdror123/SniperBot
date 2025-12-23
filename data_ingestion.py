import os
import requests
import random
from datetime import datetime, timedelta
from typing import Dict, Any

class DataIngestor:
    """
    Layer 2 Support: Ingests data from Financial Modeling Prep (FMP).
    Replaces Mocks with Real Data for:
    - Fundamentals (ROE, PEG)
    - Earnings NLP (Transcripts)
    - Insider Trading (Transactions)
    """

    def __init__(self):
        self.api_key = os.getenv("FMP_API_KEY")
        self.base_url = "https://financialmodelingprep.com/api/v3"
        if not self.api_key:
            print("[DATA] WARNING: FMP_API_KEY not found. Using Mocks.")

    def fetch_universe(self, limit: int = 10000) -> list:
        """
        Fetches the universe using NASDAQ API (Free).
        Filters locally for Cap > 100M, Price > 2, Vol > 50k.
        """
        print("[DATA] Fetching Universe from NASDAQ API...")
        try:
            # Use a higher limit to get the full list (or assume download=true ignores it, but safer to be explicit)
            url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=25000&offset=0&download=true"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                print(f"[DATA] NASDAQ API Failed: {resp.status_code}")
                rows = [] # Trigger Fallback
            else:
                data = resp.json()
                rows = data.get('data', {}).get('rows', [])
            
            if not rows:
                print("[DATA] NASDAQ returned no rows. Trying Falback...")
                # FALLBACK: S&P 500 from Wikipedia
                try:
                    import pandas as pd
                    print("[DATA] Fetching S&P 500 fallback...")
                    sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
                    # Create mock rows structure
                    rows = [{'symbol': x, 'lastsale': '$100.00', 'marketCap': '10000000000'} for x in sp500['Symbol'].tolist()]
                except Exception as e:
                    print(f"[DATA] Fallback failed: {e}")
                    return []
                
            print(f"[DATA] Processing {len(rows)} raw tickers...")
            
            filtered = []
            count = 0
            
            for row in rows:
                if count >= limit: break
                
                try:
                    # 1. Parse Symbol
                    symbol = row.get('symbol', '')
                    if not symbol or not symbol.isalpha(): continue # Skip tickers with special chars
                    
                    # 2. Parse Price (remove '$' and ',')
                    price_str = row.get('lastsale', '$0.00').replace('$', '').replace(',', '')
                    try:
                        price = float(price_str)
                    except:
                        price = 0
                        
                    # 3. Parse Market Cap
                    cap_str = row.get('marketCap', '0').replace(',', '').replace('$', '')
                    if not cap_str: cap_str = '0'
                    try:
                        # Handle 'B'/'M' suffixes if they exist? NASDAQ usually sends raw numbers or formatted strings
                        # Detailed debug showed standard numbers e.g. "123456".
                        # Just in case, try float direct
                        cap = float(cap_str) 
                    except:
                        cap = 0
                    
                    if price < 2.0: continue
                    if cap < 100_000_000: continue # 100M
                    
                    filtered.append(symbol)
                    count += 1
                except:
                    continue
                    
            print(f"[DATA] NASDAQ Filtered Universe: {len(filtered)} stocks.")
            return filtered

        except Exception as e:
            print(f"[DATA] NASDAQ Fetch Error: {e}")
            return []

    def _get_json(self, endpoint: str, params: Dict = None):
        if not self.api_key: return None
        if params is None: params = {}
        params['apikey'] = self.api_key
        try:
            url = f"{self.base_url}/{endpoint}"
            resp = requests.get(url, params=params, timeout=10)
            
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) == 0: return None
                return data
            elif resp.status_code == 403:
                # SILENTLY FAIL for Plan Restrictions (Basic Plan)
                # Do not spam console.
                return None
            else:
                # Print real errors (500s, 404s, etc)
                print(f"[DATA] API Error {endpoint}: Status {resp.status_code}")
                return None
        except Exception as e:
            # Print connection errors
            print(f"[DATA] API Connection Error {endpoint}: {e}")
            return None

    def get_dark_pool_activity(self, ticker: str) -> Dict[str, Any]:
        """
        [Hybrid] FMP Institutional -> YF Institutional Fallback.
        """
        inst_buying = False
        
        # 1. Try FMP (Tier A) - DISABLED (Plan Restriction 403)
        # if self.api_key:
        #     data = self._get_json(f"institutional-holder/{ticker}")
        #     if data:
        #         total_held = sum([x.get('shares', 0) for x in data[:5]])
        #         if total_held > 10_000_000: inst_buying = True
        #         return {
        #             "net_signature_volume": 0,
        #             "gamma_exposure": 0,
        #             "institutions_buying": inst_buying
        #         }

        # 2. Try YFinance (Tier B)
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            inst = t.institutional_holders
            if inst is not None and not inst.empty:
                # Check top holders shares
                # Column is usually 'Shares' or 0
                total_shares = inst.iloc[:5, 0].sum() # Assumes col 0 is Shares
                if total_shares > 10_000_000: inst_buying = True
        except: pass
        
    def get_dark_pool_activity(self, ticker: str) -> Dict[str, Any]:
        """
        [Hybrid] FMP -> YFinance Fallback for Institutional Data.
        """
        inst_buying = False
        
        # 1. Try YFinance Major Holders (Tier B - Free)
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            holders = t.major_holders
            
            if holders is not None and not holders.empty:
                # Robust Parsing for "institutionsPercentHeld"
                # Convert to string and search
                s_holders = holders.astype(str)
                
                # Check for row containing "institutionsPercentHeld"
                for idx, row in s_holders.iterrows():
                    # Check Index AND Values for the key
                    line_str = str(idx) + " " + " ".join(row.values)
                    
                    if "institutionsPercentHeld" in line_str or "Institutions" in line_str:
                        # Try to find the float value in this row
                        # If index matched, value is in columns.
                        for col in holders.columns:
                            val = holders.loc[idx, col]
                            try:
                                f_val = float(val)
                                if f_val > 0.40: # If > 40% owned by institutions, considered bullish/safe
                                    inst_buying = True
                            except:
                                continue
        except: pass

        return {
            "net_signature_volume": 0,
            "gamma_exposure": 0,
            "institutions_buying": inst_buying
        }

    def get_insider_activity(self, ticker: str) -> Dict[str, Any]:
        """
        [Hybrid] FMP Insider -> YF Insider Fallback.
        """
        buys_90d = 0
        ceo_buy = False
        
        # 2. Try YFinance (Tier B)
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            trans = t.insider_transactions
            
            if trans is not None and not trans.empty:
                # Columns: ['Shares', 'Value', 'URL', 'Text', 'Transaction', 'Start Date', 'Ownership']
                # Filter for recent buys
                recent = trans.head(20)
                
                for idx, row in recent.iterrows():
                    # Check Transaction Type or Text
                    t_type = str(row.get('Transaction', '')).lower()
                    text = str(row.get('Text', '')).lower()
                    
                    is_buy = 'buy' in t_type or 'purchase' in t_type or 'buy' in text or 'purchase' in text
                    
                    if is_buy:
                        buys_90d += 1
                        # Check if CEO
                        owner = str(row.get('Ownership', '')).lower() 
                        # Or sometimes ownership is the name, relationship is missing. 
                        # YF data is tricky. We assume 'D' is Direct.
                        # Strict CEO check is hard. We'll skip forcing CEO buy unless text says so.
                        if 'ceo' in text or 'chief executive' in text:
                            ceo_buy = True
        except: pass
        
        return {"net_insider_buys_90d": buys_90d, "ceo_purchase": ceo_buy}

    def get_earnings_sentiment(self, ticker: str) -> Dict[str, Any]:
        """
        Fetches Sentiment via Yahoo Finance News (Free & Reliable).
        """
        # (Existing YF Logic is good)
        try:
            import yfinance as yf
            t = yf.Ticker(ticker)
            news = t.news
            if news:
                titles = [n.get('title', '').lower() for n in news]
                combined_text = " ".join(titles)
                pos_words = ['soars', 'jumps', 'buy', 'upgrade', 'record', 'bull', 'strong']
                neg_words = ['plunges', 'drops', 'sell', 'downgrade', 'warns', 'bear', 'weak']
                score = 0
                for w in pos_words: score += combined_text.count(w)
                for w in neg_words: score -= combined_text.count(w)
                final_score = max(-1.0, min(1.0, score / 3.0)) 
                summary = f"News Sentiment ({len(news)} items)"
                return {"sentiment_score": final_score, "summary": summary}
        except Exception:
            pass

        return {"sentiment_score": 0, "summary": "Neutral (No Data)"}

    def get_social_sentiment(self, ticker: str) -> float:
        """
        [REAL] FMP offers Social Sentiment Endpoint.
        """
        if self.api_key:
            data = self._get_json(f"social-sentiment/stock", params={"symbol": ticker})
            if data and isinstance(data, list):
                 try:
                    s = data[0].get('stocktwitsSentiment', 0)
                    return min(100, max(0, s * 100))
                 except: pass
        return 0.0
    
    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        [Hybrid] FMP Fundamentals -> YF Info Fallback.
        """
        roe = 0.0
        peg = 0.0
        fcf_pos = False
        data_found = False

        # 1. FMP (Tier A)
        # 1. FMP (Tier A) - STABLE API
        if self.api_key:
            # Use Direct URL for Stable Endpoint
            try:
                # Ratios
                url_r = f"https://financialmodelingprep.com/stable/ratios-ttm?symbol={ticker}&apikey={self.api_key}"
                ratios = requests.get(url_r, timeout=10).json()
                
                # Metrics
                url_m = f"https://financialmodelingprep.com/stable/key-metrics-ttm?symbol={ticker}&apikey={self.api_key}"
                metrics = requests.get(url_m, timeout=10).json()

                if ratios and isinstance(ratios, list):
                    roe = ratios[0].get('returnOnEquityTTM', 0.0) or 0.0
                    peg = ratios[0].get('pegRatioTTM', 0.0) or 0.0
                    data_found = True
                    
                if metrics and isinstance(metrics, list):
                    fcf = metrics[0].get('freeCashFlowTTM', 0.0) or 0.0
                    fcf_pos = fcf > 0
                    data_found = True
            except Exception as e:
                print(f"[DATA] FMP Fundamentals failed: {e}")
        
        # 2. YFinance (Tier B) if FMP failed
        if not data_found:
            try:
                import yfinance as yf
                info = yf.Ticker(ticker).info
                if info:
                    roe = info.get('returnOnEquity', 0.0) or 0.0
                    peg = info.get('pegRatio', 0.0) or 0.0
                    fcf = info.get('freeCashFlow', 0) or 0
                    fcf_pos = fcf > 0
                    data_found = True
            except: pass
            
        if not data_found:
            return None # Trigger Dynamic Skip

        return {
            "roe": roe,
            "peg_ratio": peg,
            "free_cash_flow_positive": fcf_pos
        }
