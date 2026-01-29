"""Test Queue DB Integration"""
import time
from ai_signal_engine import AISignalEngine
from ai_queue_worker import main as run_worker
import sys
from unittest.mock import patch, MagicMock

print("="*60)
print("TESTING QUEUE DB INTEGRATION")
print("="*60)

engine = AISignalEngine()

# 1. Queue a job
print("\n1. Queueing TEST_TICKER...")
success = engine.queue_stock('TEST', priority=100)
if success:
    print("   ✅ Queued successfully")
else:
    print("   ❌ Queue failed")
    sys.exit(1)

# 2. Check DB
print("\n2. Checking DB for pending job...")
res = engine.supabase.table('ai_job_queue').select('*').eq('ticker', 'TEST').eq('status', 'pending').execute()
if res.data:
    print(f"   ✅ Job found: {res.data[0]['id']}")
    job_id = res.data[0]['id']
else:
    print("   ❌ Job not found in DB")
    sys.exit(1)

# 3. Running Worker (Single Run)
print("\n3. Running Queue Worker (Processing 1 Job)...")
# Mock the actual AI scoring to avoid rate limits/cost
with patch.object(engine, 'score_stock') as mock_score:
    mock_score.return_value = {
        'ticker': 'TEST', 
        'hunter': 50, 'hunter_reason': 'Mocked',
        'quant': 60, 'quant_reason': 'Mocked',
        'oracle': 70, 'oracle_reason': 'Mocked',
        'success': True
    }
    
    # We need to use the engine instance we hacked
    # But run_worker creates its own engine.
    # So we call process_queue directly on OUR engine.
    engine.process_queue(max_jobs=1)

# 4. Check DB for completion
print("\n4. Verifying Completion...")
res = engine.supabase.table('ai_job_queue').select('*').eq('id', job_id).execute()
if res.data and res.data[0]['status'] == 'completed':
    print("   ✅ Job marked 'completed'")
    print(f"   Result: {res.data[0]['result']}")
else:
    print(f"   ❌ Job status: {res.data[0]['status'] if res.data else 'Missing'}")
    sys.exit(1)

# Cleanup
print("\n5. Cleaning up...")
engine.supabase.table('ai_job_queue').delete().eq('ticker', 'TEST').execute()
print("   ✅ Cleanup done")
