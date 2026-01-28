"""
AI Signal Engine with Smart Queue
==================================
Handles Gemini API calls with rate-limit-aware processing.

Architecture:
1. Queue System: Jobs are queued in Supabase table
2. Rate Limiter: Processes 1 job per 60 seconds
3. Lens Scorers: HUNTER, QUANT, ORACLE prompts

Usage:
    from ai_signal_engine import AISignalEngine
    engine = AISignalEngine()
    scores = engine.score_stock('NVDA')  # Immediate (may fail if rate limited)
    engine.queue_stock('NVDA')           # Queue for background processing
"""
import os
import json
import time
import warnings
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from dotenv import load_dotenv
import pandas as pd
import yfinance as yf

warnings.filterwarnings('ignore')
load_dotenv()

# Gemini Setup - Use v1 REST API instead of SDK (SDK uses v1beta which returns 404)
import requests
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
# Use verified available model: gemini-2.0-flash
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash:generateContent"

# Supabase Setup
from supabase import create_client
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')


class AISignalEngine:
    """AI-powered signal engine with Smart Queue for rate limit management."""
    
    MIN_DELAY_SECONDS = 4  # Reduced - Tier 1 has higher limits
    DAILY_REQUEST_LIMIT = 500  # BUDGET PROTECTION: Max ~$10/month
    
    def __init__(self):
        self.api_key = GOOGLE_API_KEY
        self.api_url = f"{GEMINI_API_URL}?key={self.api_key}"
        self.supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        self.last_call_time = None
        
        # Budget protection: Track daily requests
        self.daily_requests = 0
        self.request_date = datetime.now().date()
        
    # =========================================================================
    # DATA FETCHING
    # =========================================================================
    
    def _fetch_yahoo_data(self, ticker: str) -> Dict:
        """Fetch insider and institutional data from Yahoo Finance."""
        print(f"DEBUG: Fetching Yahoo data for {ticker}...", flush=True)
        try:
            stock = yf.Ticker(ticker)
            
            # Insider Transactions
            insider_text = ""
            try:
                print("DEBUG: Getting insider_transactions...", flush=True)
                df = stock.insider_transactions
                if df is not None and not df.empty:
                    cols = [c for c in ['Start Date', 'Transaction', 'Insider', 'Shares', 'Value', 'Text'] 
                            if c in df.columns]
                    insider_text = df[cols].head(25).to_string()
            except: pass
            
            # Institutional Holders
            inst_text = ""
            try:
                df = stock.institutional_holders
                if df is not None and not df.empty:
                    inst_text = df.head(15).to_string()
            except: pass
            
            # Major Holders
            holders_text = ""
            try:
                df = stock.major_holders
                if df is not None and not df.empty:
                    holders_text = df.to_string()
            except: pass
            
            return {
                'insider': insider_text,
                'institutional': inst_text,
                'holders': holders_text,
                'has_data': bool(insider_text or inst_text or holders_text)
            }
        except Exception as e:
            return {'insider': '', 'institutional': '', 'holders': '', 'has_data': False, 'error': str(e)}
    
    # =========================================================================
    # AI SCORING (Individual Lenses)
    # =========================================================================
    
    def _wait_for_rate_limit(self):
        """Ensure minimum delay between API calls."""
        if self.last_call_time:
            elapsed = (datetime.now() - self.last_call_time).total_seconds()
            if elapsed < self.MIN_DELAY_SECONDS:
                wait_time = self.MIN_DELAY_SECONDS - elapsed
                print(f"    [Rate Limit] Waiting {wait_time:.1f}s...", flush=True)
                time.sleep(wait_time)
        self.last_call_time = datetime.now()
    
    def _call_gemini(self, prompt: str) -> Tuple[int, str]:
        """Call Gemini API via v1 REST endpoint with rate limit handling. Returns (score, reason)."""
        
        # BUDGET PROTECTION: Reset counter if new day
        today = datetime.now().date()
        if today != self.request_date:
            self.request_date = today
            self.daily_requests = 0
        
        # BUDGET PROTECTION: Check daily limit
        if self.daily_requests >= self.DAILY_REQUEST_LIMIT:
            print(f"    [BUDGET] Daily limit reached ({self.DAILY_REQUEST_LIMIT} requests). Skipping.", flush=True)
            return 0, 'BUDGET_LIMIT_REACHED'
        
        self._wait_for_rate_limit()
        self.daily_requests += 1
        print(f"    [API] Calling Gemini... (Request #{self.daily_requests}/{self.DAILY_REQUEST_LIMIT})", flush=True)
        
        try:
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 500
                }
            }
            
            response = requests.post(self.api_url, json=payload, timeout=60)
            
            if response.status_code == 429:
                return 0, 'RATE_LIMITED'
            
            if response.status_code != 200:
                return 0, f'API Error: {response.status_code}'
            
            data = response.json()
            text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
            text = text.replace('```json', '').replace('```', '').strip()
            
            # Extract JSON
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                result = json.loads(text[start:end])
                return result.get('score', 0), result.get('reason', 'Parsed')
            return 0, 'No JSON found'
        except Exception as e:
            error_str = str(e)
            if '429' in error_str or 'quota' in error_str.lower():
                return 0, 'RATE_LIMITED'
            return 0, f'Error: {error_str[:50]}'
    
    def score_hunter(self, ticker: str, insider_text: str) -> Tuple[int, str]:
        """HUNTER Lens: Analyze insider trading sentiment."""
        if not insider_text:
            return 0, 'No insider data'
        
        prompt = f"""Analyze {ticker} INSIDER TRANSACTIONS and score sentiment.

SCALE:
-100 = Heavy Insider Selling (Panic)
-50 = Moderate Selling
0 = Neutral (Gifts, Options, Mixed)
+50 = Moderate Buying
+100 = Heavy Insider Buying (Confidence)

DATA:
{insider_text[:2500]}

Return JSON: {{ "score": <integer -100 to +100>, "reason": "<brief reasoning>" }}"""
        
        return self._call_gemini(prompt)
    
    def score_quant(self, ticker: str, inst_text: str, holders_text: str) -> Tuple[int, str]:
        """QUANT Lens: Analyze institutional ownership quality."""
        combined = f"INSTITUTIONAL:\n{inst_text}\n\nHOLDERS:\n{holders_text}"
        if not combined.strip():
            return 50, 'No institutional data'  # Default to neutral
        
        prompt = f"""Analyze {ticker} INSTITUTIONAL OWNERSHIP and score quality.

SCALE:
0 = Poor (Unknown funds, decreasing positions)
50 = Average
100 = Excellent (Top funds like Vanguard/Blackrock, increasing positions)

DATA:
{combined[:2500]}

Return JSON: {{ "score": <integer 0 to 100>, "reason": "<brief reasoning>" }}"""
        
        return self._call_gemini(prompt)
    
    def score_oracle(self, ticker: str, insider_text: str, inst_text: str) -> Tuple[int, str]:
        """ORACLE Lens: Synthesize overall prediction."""
        prompt = f"""Synthesize a FORECAST for {ticker} based on insider and institutional data.

SCALE:
-100 = Strong Bearish (Expect decline)
0 = Neutral
+100 = Strong Bullish (Expect growth)

INSIDER DATA:
{insider_text[:1500]}

INSTITUTIONAL DATA:
{inst_text[:1500]}

Return JSON: {{ "score": <integer -100 to +100>, "reason": "<brief reasoning>" }}"""
        
        return self._call_gemini(prompt)
    
    # =========================================================================
    # SCORING (Combined)
    # =========================================================================
    
    def score_stock(self, ticker: str) -> Dict:
        """Score a single stock across all lenses. Blocking, may hit rate limits."""
        data = self._fetch_yahoo_data(ticker)
        
        if not data['has_data']:
            return {
                'ticker': ticker,
                'hunter': 0, 'hunter_reason': 'No data',
                'quant': 50, 'quant_reason': 'No data',
                'oracle': 0, 'oracle_reason': 'No data',
                'success': False
            }
        
        hunter, h_reason = self.score_hunter(ticker, data['insider'])
        quant, q_reason = self.score_quant(ticker, data['institutional'], data['holders'])
        oracle, o_reason = self.score_oracle(ticker, data['insider'], data['institutional'])
        
        return {
            'ticker': ticker,
            'hunter': hunter, 'hunter_reason': h_reason,
            'quant': quant, 'quant_reason': q_reason,
            'oracle': oracle, 'oracle_reason': o_reason,
            'success': 'RATE_LIMITED' not in [h_reason, q_reason, o_reason]
        }
    
    # =========================================================================
    # SMART QUEUE (Background Processing)
    # =========================================================================
    
    def queue_stock(self, ticker: str, priority: int = 0) -> bool:
        """Add a stock to the AI processing queue."""
        try:
            self.supabase.table('ai_job_queue').insert({
                'ticker': ticker,
                'status': 'pending',
                'priority': priority,
                'created_at': datetime.now().isoformat()
            }).execute()
            return True
        except Exception as e:
            print(f"Queue error: {e}")
            return False
    
    def process_queue(self, max_jobs: int = 10):
        """Process pending jobs from the queue (run as background task)."""
        try:
            # Get pending jobs ordered by priority
            response = self.supabase.table('ai_job_queue')\
                .select('*')\
                .eq('status', 'pending')\
                .order('priority', desc=True)\
                .order('created_at')\
                .limit(max_jobs)\
                .execute()
            
            jobs = response.data or []
            print(f"Processing {len(jobs)} queued jobs...")
            
            for job in jobs:
                ticker = job['ticker']
                job_id = job['id']
                
                print(f"  Processing {ticker}...")
                
                # Mark as processing
                self.supabase.table('ai_job_queue').update({
                    'status': 'processing',
                    'started_at': datetime.now().isoformat()
                }).eq('id', job_id).execute()
                
                # Score
                result = self.score_stock(ticker)
                
                # Update job with results
                self.supabase.table('ai_job_queue').update({
                    'status': 'completed' if result['success'] else 'failed',
                    'completed_at': datetime.now().isoformat(),
                    'result': json.dumps(result)
                }).eq('id', job_id).execute()
                
                print(f"    HUNTER={result['hunter']}, QUANT={result['quant']}, ORACLE={result['oracle']}")
                
        except Exception as e:
            print(f"Queue processing error: {e}")


# =============================================================================
# CLI for Testing
# =============================================================================
if __name__ == "__main__":
    import sys
    
    engine = AISignalEngine()
    
    if len(sys.argv) > 1:
        ticker = sys.argv[1].upper()
        print(f"Scoring {ticker}...")
        result = engine.score_stock(ticker)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python ai_signal_engine.py TICKER")
        print("Example: python ai_signal_engine.py NVDA")
