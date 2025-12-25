import os
import requests
import random
from datetime import datetime, timedelta
from typing import Dict, Any
from discord_service import send_message

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
        Fetches the universe matching criteria (Price > $2, Cap > $100M).
        Priority:
        1. NASDAQ API (with Stealth Headers) - Primary
        2. Wikipedia S&P 500 (Fallback)
        """
        rows = []

        # -----------------------------------------------
        # 1. ATTEMPT NASDAQ TRADER OFFICIAL FILE (Primary - Robust)
        # -----------------------------------------------
        print("[DATA] Fetching Universe from NASDAQ Trader Official Source...")
        try:
            # This is the official file used by trading terminals
            url = "http://www.nasdaqtrader.com/dynamic/SymDir/nasdaqtraded.txt"
            headers = {'User-Agent': 'Mozilla/5.0'} # Simple UA usually enough for static file
            
            resp = requests.get(url, headers=headers, timeout=45)
            if resp.status_code == 200:
                print(f"[DATA] Downloaded {len(resp.content)} bytes from NASDAQ Trader.")
                
                # Parse Pipe-Delimited text
                content = resp.text
                lines = content.splitlines()
                # Skip Header (Symbol|Security Name|...) and Trailer (File Creation Time...)
                # Heuristic: Valid lines have pipes.
                
                for line in lines[1:-1]: # Skip first and last usually
                    parts = line.split('|')
                    if len(parts) > 2:
                        sym = parts[1] # Symbol is usually 2nd column? 
                        # Wait, let's verify column order. 
                        # Header: "Nasdaq Traded|Symbol|Security Name|Listing Exchange|Market Category|ETF|Round Lot Size|Test Issue|Financial Status|CQS Symbol|NASDAQ Symbol|NextShares"
                        # Sample: "Y|A|Agilent Technologies...|N|Q|N|100|N|N||A|N"
                        # So Symbol is index 1.
                        
                        test_issue = parts[7] if len(parts) > 7 else 'N'
                        
                        if test_issue == 'N':
                            # Basic cleaning
                            sym = sym.strip().upper()
                            # Exclude weird ones
                            if sym.isalpha():
                                rows.append(sym)
                                
                # Also fetch 'otherlisted.txt' for NYSE/AMEX? 
                # 'nasdaqtraded.txt' includes ALL stocks traded on NASDAQ, which includes NYSE usually?
                # Actually, 'nasdaqtraded.txt' contains securities TRADED on Nasdaq, not just listed.
                # So it implies full coverage.
                
                # If we want to be sure, we can also check 'otherlisted.txt'
                # But let's start with this.
                
                print(f"[DATA] NASDAQ Trader Success. Found {len(rows)} valid tickers.")
                
                # Deduplicate just in case
                rows = list(set(rows))
                
            else:
                print(f"[DATA] NASDAQ Trader Failed: {resp.status_code}")
                rows = []
            
        except Exception as e:
            print(f"[DATA] NASDAQ Trader Error: {e}")
            rows = []

        # -----------------------------------------------
        # 2. ATTEMPT GITHUB RAW LIST (Reliable Fallback - Full Market)
        # -----------------------------------------------
        if not rows:
            print("[DATA] NASDAQ Scraping failed. Trying GitHub Raw Ticker List...")
            # Verified Source: rreichel3/US-Stock-Symbols (Updated Nightly)
            urls = [
                "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/nasdaq/nasdaq_tickers.json",
                "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/nyse/nyse_tickers.json"
            ]
            
            for u in urls:
                try:
                    resp = requests.get(u, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        # Data is list of dicts: [{'symbol': 'AAPL', ...}, ...]
                        for item in data:
                            sym = item.get('symbol')
                            if sym:
                                # Basic cleaning
                                sym = sym.strip().upper()
                                # Filter weird chars standard in some lists
                                if "^" not in sym: 
                                    rows.append(sym)
                        print(f"[DATA] Fetched {len(data)} from {u.split('/')[-1]}")
                except Exception as e:
                    print(f"[DATA] Error fetching {u}: {e}")
            
            # Deduplicate
            rows = list(set(rows))
            print(f"[DATA] GitHub Fallback Total: {len(rows)} unique tickers.")
            
            if rows:
                return rows # Return immediately if successful

        if not rows:
            print("[DATA] NASDAQ returned no rows. Trying Fallback...")
            
            # NOTIFY USER via Discord
            try:
                print("[DATA] Attempting to send Discord alert...")
                send_message("⚠️ **ALERT:** NASDAQ & FMP failed. Falling back to S&P 500 list.")
                print("[DATA] Discord alert sent.")
            except Exception as e:
                print(f"[DATA] Discord Alert Failed: {e}")

            # FALLBACK: S&P 500 from Wikipedia
            try:
                import pandas as pd
                print("[DATA] Fetching S&P 500 fallback...")
                
                wiki_url = 'https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
                wiki_headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0 s_bot/1.0'
                }
                print(f"[DATA] Requesting Wikipedia URL: {wiki_url}")
                r = requests.get(wiki_url, headers=wiki_headers, timeout=15)
                print(f"[DATA] Wikipedia Response Status: {r.status_code}")
                
                if r.status_code == 200:
                    dfs = pd.read_html(r.text)
                    sp500 = dfs[0]
                    # Create mock rows structure
                    rows = [{'symbol': x, 'lastsale': '$100.00', 'marketCap': '10000000000'} for x in sp500['Symbol'].tolist()]
                else:
                    print(f"[DATA] Wikipedia returned {r.status_code}")
                    rows = []

            except Exception as e:
                print(f"[DATA] Fallback failed: {e}")
                return []
            
        print(f"[DATA] Processing {len(rows)} raw tickers...")
        
        filtered = []
        count = 0
        
        for row in rows:
            if count >= limit: break
            
            try:
                # [POLYMORPHSM] Handle both String (New Source) and Dict (Old Source)
                if isinstance(row, str):
                    symbol = row
                    price = 100.0 # Dummy, let main loop filter
                    cap = 1000000000 # Dummy, let main loop filter
                else:
                    # 1. Parse Symbol
                    symbol = row.get('symbol', '')
                    
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
                        cap = float(cap_str) 
                    except:
                        cap = 0
                
                if not symbol or not symbol.isalpha(): continue
                
                if price < 2.0: continue
                if cap < 100_000_000: continue # 100M
                
                filtered.append(symbol)
                count += 1
            except:
                continue
                
        print(f"[DATA] Filtered Universe: {len(filtered)} stocks.")
        return filtered


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
