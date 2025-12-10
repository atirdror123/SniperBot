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
        Fetches a filtered list of tickers from FMP Screener.
        Criteria:
        - Market Cap > 100M (Avoid penny stocks)
        - Price > $2.00
        - Volume > 50,000
        - Exchange: NASDAQ, NYSE, AMEX
        """
        if not self.api_key:
            # Fallback for testing/offline
            return ["AAPL", "NVDA", "AMD", "TSLA", "MSFT", "AMZN", "GOOGL", "META"] # Small list

        endpoint = "stock-screener"
        # FMP Screener allows params
        params = {
            "marketCapMoreThan": 100_000_000,
            "priceMoreThan": 2,
            "volumeMoreThan": 50_000,
            "exchange": "NASDAQ,NYSE,AMEX",
            "isEtf": "false",
            "limit": limit # Max limit to get all
        }
        
        data = self._get_json(endpoint, params=params)
        if data:
             # Extract symbols
             tickers = [x['symbol'] for x in data if 'symbol' in x]
             # Filter out dots/dashes just in case
             return [t for t in tickers if "." not in t and "-" not in t]
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
            return None
        except Exception as e:
            print(f"[DATA] API Error {endpoint}: {e}")
            return None

    def get_dark_pool_activity(self, ticker: str) -> Dict[str, Any]:
        """
        [PARTIAL MOCK] FMP doesn't give direct Dark Pool prints.
        We use 'Institutional Holders' as a proxy for Smart Money accumulation.
        """
        if not self.api_key:
             # Fallback to Random Mock
            return {
                "net_signature_volume": 0,
                "gamma_exposure": random.uniform(-5, 5),
                "institutions_buying": random.random() < 0.2
            }
            
        # Real Data: Check Institutional Ownership changes
        data = self._get_json(f"institutional-holder/{ticker}")
        inst_buying = False
        
        if data:
            # Simple heuristic: If top holder increased position recently
            # (FMP returns list of holders, but not always historical changes easily. 
            # We'll valid check if there's substantial holding)
            total_held = sum([x.get('shares', 0) for x in data[:5]])
            if total_held > 10_000_000: # Arbitrary "Big Money" threshold
                inst_buying = True
                
        return {
            "net_signature_volume": 0, # Not available
            "gamma_exposure": 0, # Needs Options API
            "institutions_buying": inst_buying
        }

    def get_insider_activity(self, ticker: str) -> Dict[str, Any]:
        """
        [REAL] Retrieves Insider Trading from FMP.
        """
        if not self.api_key:
             return {"net_insider_buys_90d": 0, "ceo_purchase": False}

        # Fetch last 100 insider trades
        data = self._get_json(f"insider-trading/{ticker}", params={"limit": 100})
        
        buys_90d = 0
        ceo_buy = False
        cutoff = datetime.now() - timedelta(days=90)
        
        if data:
            for trade in data:
                try:
                    date_str = trade.get('transactionDate', '')
                    if not date_str: continue
                    t_date = datetime.strptime(date_str, "%Y-%m-%d")
                    
                    if t_date < cutoff: continue
                    
                    t_type = trade.get('transactionType', '').lower()
                    
                    if 'purchase' in t_type or 'buy' in t_type:
                        buys_90d += 1
                        role = trade.get('typeOfOwner', '').lower()
                        if 'ceo' in role or 'chief executive' in role:
                            ceo_buy = True
                except: continue
                
        return {
            "net_insider_buys_90d": buys_90d,
            "ceo_purchase": ceo_buy
        }

    def get_earnings_sentiment(self, ticker: str) -> Dict[str, Any]:
        """
        [REAL] Fetches Earnings Transcript and performs simple sentiment/keyword scan.
        """
        if not self.api_key:
            return {"sentiment_score": 0.0, "key_verbs": []}

        # Get Transcript
        # Note: FMP 'earning_call_transcript' requires quarter/year. 
        # We try 'v4/earning_call_transcript?symbol=' to list available first or just most recent.
        # Easier: v3/earning_call_transcript/{ticker} returns list.
        data = self._get_json(f"earning_call_transcript/{ticker}")
        
        sentiment_score = 0.0
        keywords = []
        
        if data and isinstance(data, list):
            # Most recent call
            transcript = data[0].get('content', '')
            
            # Simple "Bag of Words" Analysis (Lens B - Oracle)
            # In production, we'd use NLTK or Gemini here to summary the text.
            # For speed/cost, we do a quick count.
            bull_words = ['delivered', 'record result', 'executing', 'momentum', 'strong demand']
            bear_words = ['headwinds', 'uncertainty', 'supply chain', 'softness', 'challenging']
            
            score = 0
            found_bull = [w for w in bull_words if w in transcript.lower()]
            found_bear = [w for w in bear_words if w in transcript.lower()]
            
            score += len(found_bull)
            score -= len(found_bear)
            
            # Normalize rough score (-5 to +5 range mapped to -1.0 to 1.0)
            sentiment_score = max(-1.0, min(1.0, score / 5.0))
            keywords = found_bull[:3] + found_bear[:3]
            
        return {
            "sentiment_score": sentiment_score,
            "key_verbs": keywords
        }

    def get_social_sentiment(self, ticker: str) -> float:
        """
        [REAL] FMP offers Social Sentiment Endpoint.
        """
        if not self.api_key:
             return 50.0

        # endpoint: v4/social-sentiment
        # This is a 'Premium' endpoint often. Fallback to Mock if FMP Basic doesn't have it.
        # We'll try.
        data = self._get_json(f"social-sentiment/stock", params={"symbol": ticker})
        if data and isinstance(data, list):
            # Average sentiment
            try:
                s = data[0].get('stocktwitsSentiment', 0)
                return min(100, max(0, s * 100)) # Assuming 0-1 scale? FMP varies.
            except: pass
            
        return 50.0 # Neutral fallback
    
    def get_fundamentals(self, ticker: str) -> Dict[str, Any]:
        """
        [REAL] FMP Key Metrics.
        """
        if not self.api_key:
            return {"roe": 0.0, "peg_ratio": 0.0, "free_cash_flow_positive": False}
            
        # 1. Ratios (PEG, ROE)
        ratios = self._get_json(f"ratios-ttm/{ticker}")
        # 2. Key Metrics (FCF)
        metrics = self._get_json(f"key-metrics-ttm/{ticker}")
        
        roe = 0.0
        peg = 0.0
        fcf_pos = False
        
        if ratios and isinstance(ratios, list):
            roe = ratios[0].get('returnOnEquityTTM', 0.0) or 0.0
            peg = ratios[0].get('pegRatioTTM', 0.0) or 0.0
            
        if metrics and isinstance(metrics, list):
            fcf = metrics[0].get('freeCashFlowTTM', 0.0) or 0.0
            fcf_pos = fcf > 0
            
        return {
            "roe": roe,
            "peg_ratio": peg,
            "free_cash_flow_positive": fcf_pos
        }
