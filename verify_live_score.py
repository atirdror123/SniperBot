"""Verify LIVE Scoring (No Mocks)"""
import time
import json
from ai_signal_engine import AISignalEngine
import sys

print("="*60)
print("VERIFYING LIVE SCORE (NVDA)")
print("="*60)

engine = AISignalEngine()

# 1. Cleanup old
engine.supabase.table('ai_job_queue').delete().eq('ticker', 'NVDA').execute()

# 2. Queue NVDA
print("\n1. Queueing NVDA...")
engine.queue_stock('NVDA', priority=999)

# 3. Process (Real API Call)
print("\n2. RUnning Worker (Requesting Gemini)...")
print("   (This might take >60s if rate limits active)")
engine.process_queue(max_jobs=1)

# 4. Check Result
print("\n3. Checking Results in DB...")
res = engine.supabase.table('ai_job_queue').select('*').eq('ticker', 'NVDA').order('created_at', desc=True).limit(1).execute()

if res.data:
    job = res.data[0]
    print(f"   Status: {job['status']}")
    if job['status'] == 'completed':
        result = job['result'] # extracted from JSONB
        print(f"   HUNTER: {result.get('hunter')} ({result.get('hunter_reason')})")
        print(f"   QUANT:  {result.get('quant')}  ({result.get('quant_reason')})")
        print(f"   ORACLE: {result.get('oracle')} ({result.get('oracle_reason')})")
        
        if result.get('hunter') != 0 or result.get('quant') != 50:
            print("\n✅ SUCCESS: Received Real AI Scores!")
        else:
            print("\n⚠️ WARNING: Scores are default (0/50). Check reasons.")
    else:
        print(f"   ❌ Job failed/pending: {job}")
else:
    print("   ❌ Job not found")
