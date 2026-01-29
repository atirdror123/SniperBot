"""
Quick Pipeline Debugger
=======================
Tests each stage of the scan pipeline individually to find the failure point.
"""
import os
import sys
from dotenv import load_dotenv
load_dotenv()

def test_stage(name, func):
    """Run a test stage and report pass/fail."""
    print(f"\n{'='*60}")
    print(f"STAGE: {name}")
    print('='*60)
    try:
        result = func()
        print(f"✅ PASS: {result}")
        return True
    except Exception as e:
        print(f"❌ FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

# ===========================================================================
# STAGE 1: Environment Variables
# ===========================================================================
def stage_env_vars():
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = os.getenv("SUPABASE_KEY")
    google_key = os.getenv("GOOGLE_API_KEY")
    
    missing = []
    if not supabase_url: missing.append("SUPABASE_URL")
    if not supabase_key: missing.append("SUPABASE_KEY")
    if not google_key: missing.append("GOOGLE_API_KEY")
    
    if missing:
        raise Exception(f"Missing: {', '.join(missing)}")
    return f"All env vars present"

# ===========================================================================
# STAGE 2: Supabase Connection
# ===========================================================================
def stage_supabase():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    client = create_client(url, key)
    
    # Try to read sniper_signals table
    response = client.table('sniper_signals').select('ticker', count='exact').limit(5).execute()
    count = response.count if hasattr(response, 'count') else len(response.data)
    return f"Connected. Found {count} signals in DB. Sample: {[r['ticker'] for r in response.data]}"

# ===========================================================================
# STAGE 3: Ticker Fetching (NASDAQ API)
# ===========================================================================
def stage_tickers():
    import requests
    url = "https://api.nasdaq.com/api/screener/stocks?tableonly=true&limit=100&offset=0&download=true"
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers, timeout=15)
    data = response.json()
    
    if not data.get('data') or not data['data'].get('rows'):
        raise Exception(f"No rows returned. Status: {response.status_code}")
    
    sample = [r['symbol'] for r in data['data']['rows'][:5]]
    return f"Fetched {len(data['data']['rows'])} tickers. Sample: {sample}"

# ===========================================================================
# STAGE 4: YFinance Data Download
# ===========================================================================
def stage_yfinance():
    import yfinance as yf
    test_tickers = ['AAPL', 'NVDA', 'MSFT']
    data = yf.download(test_tickers, period="5d", interval="1d", progress=False)
    
    if data.empty:
        raise Exception("No data returned from yfinance")
    
    return f"Downloaded {len(data)} rows. Columns: {list(data.columns.levels[0])[:3]}"

# ===========================================================================
# STAGE 5: Technical Scorer (SniperScorer)
# ===========================================================================
def stage_tech_scorer():
    from scanner_logic import SniperScorer
    scorer = SniperScorer()
    result = scorer.analyze_stock('NVDA')
    score = result.get('final_score', 0)
    if score == 0:
        raise Exception(f"Score is 0. Result: {result}")
    return f"NVDA Tech Score = {score}. Details: {result.get('details', 'N/A')[:50]}..."

# ===========================================================================
# STAGE 6: AI Signal Engine  
# ===========================================================================
def stage_ai_engine():
    from ai_signal_engine import AISignalEngine
    engine = AISignalEngine()
    result = engine.score_stock('NVDA')
    
    if not result.get('success'):
        reasons = [result.get('hunter_reason', ''), result.get('quant_reason', ''), result.get('oracle_reason', '')]
        raise Exception(f"AI scoring failed. Reasons: {reasons}")
    
    return f"NVDA AI Score = {result['final_score']}. H={result['hunter']}, Q={result['quant']}, O={result['oracle']}"

# ===========================================================================
# STAGE 7: Database Write
# ===========================================================================
def stage_db_write():
    from supabase import create_client
    from datetime import datetime
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    client = create_client(url, key)
    
    # Try to insert a test signal
    test_data = {
        'ticker': 'TEST_DEBUG',
        'entry_price': 999.99,
        'confidence_score': 99,
        'reasons': 'DEBUG TEST - SHOULD BE DELETED',
        'status': 'CLOSED',  # Use CLOSED so it doesn't interfere
        'raw_features': {'test': True}
    }
    
    client.table('sniper_signals').insert(test_data).execute()
    
    # Clean up
    client.table('sniper_signals').delete().eq('ticker', 'TEST_DEBUG').execute()
    
    return "Write and delete successful"

# ===========================================================================
# STAGE 8: Dashboard Data Fetch
# ===========================================================================
def stage_dashboard_data():
    from supabase import create_client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    client = create_client(url, key)
    
    # Fetch OPEN signals (what dashboard shows)
    response = client.table('sniper_signals').select('*').eq('status', 'OPEN').order('created_at', desc=True).limit(10).execute()
    
    data = response.data
    if not data:
        return "⚠️ NO OPEN SIGNALS IN DATABASE - Dashboard will be empty!"
    
    tickers = [r['ticker'] for r in data]
    return f"Found {len(data)} OPEN signals: {tickers}"

# ===========================================================================
# MAIN
# ===========================================================================
if __name__ == "__main__":
    print("\n" + "🔍 PIPELINE DEBUGGER".center(60))
    print("="*60)
    
    stages = [
        ("1. Environment Variables", stage_env_vars),
        ("2. Supabase Connection", stage_supabase),
        ("3. NASDAQ Ticker API", stage_tickers),
        ("4. YFinance Download", stage_yfinance),
        ("5. Technical Scorer", stage_tech_scorer),
        ("6. AI Signal Engine", stage_ai_engine),
        ("7. Database Write", stage_db_write),
        ("8. Dashboard Data Fetch", stage_dashboard_data),
    ]
    
    results = {}
    for name, func in stages:
        results[name] = test_stage(name, func)
    
    # Summary
    print("\n" + "="*60)
    print("📊 SUMMARY")
    print("="*60)
    for name, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"  {status} {name}")
    
    failed = [n for n, p in results.items() if not p]
    if failed:
        print(f"\n🔴 ROOT CAUSE: First failure at '{failed[0]}'")
    else:
        print("\n🟢 ALL STAGES PASSED!")
