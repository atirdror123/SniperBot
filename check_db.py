"""Quick check of what's in the paper_positions table."""
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

# Check what tables exist and their structure
print("Checking paper_positions table...")
try:
    response = supabase.table('paper_positions').select('*').limit(5).execute()
    print(f"Found {len(response.data)} rows")
    if response.data:
        print(f"Columns: {list(response.data[0].keys())}")
        for row in response.data:
            ticker = row.get('ticker', row.get('symbol', 'N/A'))
            print(f"  {ticker}")
    else:
        print("  (empty table)")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*50)
print("Checking stock_picks table...")
try:
    response = supabase.table('stock_picks').select('*').limit(5).execute()
    print(f"Found {len(response.data)} rows")
    if response.data:
        print(f"Columns: {list(response.data[0].keys())}")
        for row in response.data:
            ticker = row.get('ticker', row.get('symbol', 'N/A'))
            print(f"  {ticker}")
    else:
        print("  (empty table)")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*50)
print("Checking legacy_stocks table...")
try:
    response = supabase.table('legacy_stocks').select('*').limit(5).execute()
    print(f"Found {len(response.data)} rows")
    if response.data:
        print(f"Columns: {list(response.data[0].keys())}")
        for row in response.data:
            ticker = row.get('ticker', row.get('symbol', 'N/A'))
            print(f"  {ticker}")
    else:
        print("  (empty table)")
except Exception as e:
    print(f"Error: {e}")

# Write to file for complete output
with open('db_check_output.txt', 'w') as f:
    f.write("Database check complete - see console output")
