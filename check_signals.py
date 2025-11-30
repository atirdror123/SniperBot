import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def check_saved_signals():
    """Check what signals were saved to the database"""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
        return
    
    supabase: Client = create_client(url, key)
    
    try:
        # Fetch all signals with status='OPEN', ordered by confidence_score descending
        response = supabase.table('sniper_signals').select('*').eq('status', 'OPEN').order('confidence_score', desc=True).execute()
        
        signals = response.data
        
        print(f"Found {len(signals)} saved signals:\n")
        print("="*80)
        
        for signal in signals:
            print(f"\nTicker: {signal['ticker']}")
            print(f"Score: {signal['confidence_score']}")
            print(f"Entry Price: ${signal['entry_price']:.2f}")
            print(f"Created: {signal.get('created_at', 'N/A')}")
            print(f"Reasons:")
            for reason in signal['reasons'].split('; '):
                print(f"  - {reason}")
            print("-"*80)
            
    except Exception as e:
        print(f"Error fetching signals: {e}")

if __name__ == "__main__":
    check_saved_signals()
