import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

def get_schema_sql():
    return """
    -- (EXISTING TABLES PRESERVED)
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
        raw_features JSONB,
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

    -- Create ai_multipliers table
    CREATE TABLE IF NOT EXISTS ai_multipliers (
        feature_name TEXT PRIMARY KEY,
        multiplier FLOAT DEFAULT 1.0,
        last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- Insert default multipliers if table is empty
    INSERT INTO ai_multipliers (feature_name, multiplier)
    VALUES 
        ('trend', 1.0),
        ('volume', 1.0),
        ('cash_rich', 1.0),
        ('sector_strength', 1.0),
        ('earnings_growth', 1.0)
    ON CONFLICT (feature_name) DO NOTHING;

    -- === NEW SENTIENT SNIPER TABLES ===

    -- 1. Lens Weights (The Brain's Configuration)
    CREATE TABLE IF NOT EXISTS lens_weights (
        id SERIAL PRIMARY KEY,
        regime TEXT NOT NULL, -- 'BULL', 'BEAR', 'CHOP'
        w_quant FLOAT NOT NULL DEFAULT 1.0,
        w_oracle FLOAT NOT NULL DEFAULT 1.0,
        w_hunter FLOAT NOT NULL DEFAULT 1.0,
        w_chartist FLOAT NOT NULL DEFAULT 1.0,
        last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        UNIQUE(regime)
    );

    -- Insert Defaults for Bull/Bear
    INSERT INTO lens_weights (regime, w_quant, w_oracle, w_hunter, w_chartist)
    VALUES 
        ('BULL', 1.0, 1.0, 1.2, 1.0), -- Hunter favored in Bull
        ('BEAR', 1.2, 1.0, 0.8, 1.0), -- Quant favored in Bear
        ('CHOP', 0.8, 0.8, 0.8, 1.5)  -- Chartist favored in Chop
    ON CONFLICT (regime) DO NOTHING;

    -- 2. Sentient Memory (Outcome Log)
    CREATE TABLE IF NOT EXISTS sentient_memory (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        ticker TEXT NOT NULL,
        entry_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        
        -- Scores at Entry
        score_quant FLOAT,
        score_oracle FLOAT,
        score_hunter FLOAT,
        score_chartist FLOAT,
        final_score FLOAT,
        
        -- Outcome Data (Updated later)
        roi_20d FLOAT,
        roi_90d FLOAT,
        outcome_label TEXT, -- 'WIN', 'LOSS', 'STAGNANT'
        
        -- Metadata
        regime_at_entry TEXT,
        features_snapshot JSONB
    );

    -- 3. System Status (For Dashboard)
    CREATE TABLE IF NOT EXISTS system_status (
        key TEXT PRIMARY KEY,
        value TEXT,
        last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );

    -- Insert default
    INSERT INTO system_status (key, value) VALUES ('scan_status', 'IDLE')
    ON CONFLICT (key) DO NOTHING;

    -- 4. Scan Summaries (Daily Log)
    CREATE TABLE IF NOT EXISTS scan_summaries (
        date DATE PRIMARY KEY DEFAULT CURRENT_DATE,
        scanned_count INT DEFAULT 0,
        candidates_count INT DEFAULT 0,
        saved_count INT DEFAULT 0,
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
