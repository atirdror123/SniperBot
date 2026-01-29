"""Quick Integration Test - Verify AI Signal Engine Works"""
import sys
sys.path.insert(0, '.')

print("=" * 50)
print("AI SIGNAL ENGINE INTEGRATION TEST")
print("=" * 50)

# Test 1: Import
print("\n1. Testing Imports...")
try:
    from ai_signal_engine import AISignalEngine
    print("   ✓ ai_signal_engine imported")
except Exception as e:
    print(f"   ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Instantiation
print("\n2. Testing Instantiation...")
try:
    engine = AISignalEngine()
    print("   ✓ AISignalEngine created")
except Exception as e:
    print(f"   ✗ Instantiation failed: {e}")
    sys.exit(1)

# Test 3: Data Fetching
print("\n3. Testing Yahoo Data Fetch...")
try:
    data = engine._fetch_yahoo_data('NVDA')
    print(f"   ✓ Data fetched: has_data={data['has_data']}")
    print(f"     Insider: {len(data['insider'])} chars")
    print(f"     Institutional: {len(data['institutional'])} chars")
except Exception as e:
    print(f"   ✗ Fetch failed: {e}")

# Test 4: Scanner Import
print("\n4. Testing Scanner Import...")
try:
    from sniper_scanner import get_ai_engine
    eng = get_ai_engine()
    print("   ✓ Scanner can access AI engine")
except Exception as e:
    print(f"   ✗ Scanner import failed: {e}")

print("\n" + "=" * 50)
print("INTEGRATION TEST COMPLETE")
print("=" * 50)

print("\n📝 Next Steps:")
print("   1. Run the Supabase migration (migrations/create_ai_job_queue.sql)")
print("   2. Start the queue worker: python ai_queue_worker.py --loop")
print("   3. Run a test scan: python sniper_scanner.py")
