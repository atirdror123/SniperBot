"""
Integration Test - Verify AI Scoring System
============================================
Tests that all components are properly wired together.
"""
import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

load_dotenv()

def test_integration():
    """Test all integration points."""
    print("="*60)
    print("INTEGRATION TEST - AI SCORING SYSTEM")
    print("="*60)
    
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
    
    # Test 1: AI Engine Weight Loading
    print("\n[1/5] Testing AI Engine Weight Loading...")
    try:
        from ai_signal_engine import AISignalEngine
        engine = AISignalEngine()
        print(f"  [OK] AI Engine initialized")
        print(f"  [OK] Weights loaded: {engine.weights}")
    except Exception as e:
        print(f"  [FAIL] Failed: {e}")
        return False
    
    # Test 2: Database Schema
    print("\n[2/5] Testing Database Schema...")
    try:
        # Check lens_weights table exists
        response = supabase.table('lens_weights').select('*').limit(1).execute()
        print(f"  [OK] lens_weights table exists")
        print(f"  [OK] Found {len(response.data)} regime(s)")
        
        # Check sniper_signals table
        response = supabase.table('sniper_signals').select('*').limit(1).execute()
        print(f"  [OK] sniper_signals table exists")
        
        if response.data:
            # Check if raw_features has ai_scores
            raw_features = response.data[0].get('raw_features', {})
            if isinstance(raw_features, dict) and 'ai_scores' in raw_features:
                print(f"  [OK] AI scores found in database")
            else:
                print(f"  [WARN] No AI scores in database yet (run scanner first)")
    except Exception as e:
        print(f"  [FAIL] Failed: {e}")
        return False
    
    # Test 3: Tournament System
    print("\n[3/5] Testing Tournament System...")
    try:
        from tournament_ai import run_tournament
        test_candidates = [
            {'ticker': 'TEST1', 'ai_score': 90, 'tech_score': 75, 'price': 100},
            {'ticker': 'TEST2', 'ai_score': 85, 'tech_score': 72, 'price': 50},
            {'ticker': 'TEST3', 'ai_score': 80, 'tech_score': 70, 'price': 25}
        ]
        result = run_tournament(test_candidates)
        print(f"  [OK] Tournament system functional")
        print(f"  [OK] Selected {len(result.get('top_3', []))} winners")
    except Exception as e:
        print(f"  [FAIL] Failed: {e}")
        return False
    
    # Test 4: Self-Learning System
    print("\n[4/5] Testing Self-Learning System...")
    try:
        from reinforcement_learner import SentientBrain
        brain = SentientBrain()
        print(f"  [OK] SentientBrain initialized")
        print(f"  [OK] Period weights accessible: {brain.PERIOD_WEIGHTS}")
    except Exception as e:
        print(f"  [FAIL] Failed: {e}")
        return False
    
    # Test 5: Scanner Integration
    print("\n[5/5] Testing Scanner Integration...")
    try:
        from scanner_logic import SniperScorer
        scorer = SniperScorer()
        print(f"  [OK] Technical scorer initialized")
        
        # Check if run_scanner has AI engine import
        with open('run_scanner.py', 'r') as f:
            content = f.read()
            if 'AISignalEngine' in content and 'run_tournament' in content:
                print(f"  [OK] Scanner has AI engine integration")
            else:
                print(f"  [FAIL] Scanner missing AI integration")
                return False
    except Exception as e:
        print(f"  [FAIL] Failed: {e}")
        return False
    
    print("\n" + "="*60)
    print("[SUCCESS] ALL INTEGRATION TESTS PASSED")
    print("="*60)
    print("\nNext Steps:")
    print("1. Run scanner: python run_scanner.py")
    print("2. View dashboard: streamlit run dashboard.py")
    print("3. Schedule nightly review: python nightly_ai_review.py")
    
    return True

if __name__ == '__main__':
    test_integration()
