import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def get_schema_sql():
    return """
    -- Create model_weights table
    CREATE TABLE IF NOT EXISTS model_weights (
        id SERIAL PRIMARY KEY,
        technical_weight FLOAT NOT NULL,
        social_weight FLOAT NOT NULL,
        fundamental_weight FLOAT NOT NULL,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- Insert default weights if table is empty
    INSERT INTO model_weights (technical_weight, social_weight, fundamental_weight)
    SELECT 0.4, 0.3, 0.3
    WHERE NOT EXISTS (SELECT 1 FROM model_weights);

    -- Create sniper_signals table
    CREATE TABLE IF NOT EXISTS sniper_signals (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ticker TEXT NOT NULL,
        entry_price FLOAT NOT NULL,
        confidence_score FLOAT NOT NULL,
        reasons TEXT,
        status TEXT CHECK (status IN ('OPEN', 'CLOSED')) NOT NULL,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- Create paper_portfolio table
    CREATE TABLE IF NOT EXISTS paper_portfolio (
        ticker TEXT PRIMARY KEY,
        quantity INTEGER NOT NULL,
        avg_price FLOAT NOT NULL,
        current_value FLOAT NOT NULL,
        last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """

def setup_database():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if not url or not key:
        print("Error: SUPABASE_URL or SUPABASE_KEY not found in .env")
        return

    supabase: Client = create_client(url, key)
    
    sql = get_schema_sql()
    
    print("Attempting to run SQL via RPC 'exec_sql'...")
    try:
        # Try to execute SQL via a hypothetical 'exec_sql' RPC function
        # This is a common pattern for Supabase projects to allow DDL from client
        response = supabase.rpc('exec_sql', {'sql_query': sql}).execute()
        print("Database Schema Built Successfully (via RPC)")
    except Exception as e:
        print("\nCould not execute SQL directly via RPC (this is expected if 'exec_sql' function is not set up).")
        print("Please run the following SQL manually in your Supabase SQL Editor:\n")
        print("="*50)
        print(sql)
        print("="*50)
        print(f"\nError details: {e}")

if __name__ == "__main__":
    setup_database()
