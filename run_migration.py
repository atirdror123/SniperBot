"""Execute Supabase Migration"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Parse Supabase DB URL from env or connection string
# Standard Supabase connection string format: postgres://postgres:[YOUR-PASSWORD]@db.[YOUR-PROJECT-ID].supabase.co:5432/postgres
DB_URL = os.getenv('DATABASE_URL')
# Fallback to constructing from parts if needed, but usually DATABASE_URL is best.
# If unavailable, try to use the python client to run SQL? 
# The python supabase client generally doesn't support arbitrary DDL execution directly unless via RPC or Edge Functions.
# Python `psycopg2` is standard for direct Postgres connection.

if not DB_URL:
    print("DATABASE_URL not found in .env. Trying to construct from SUPABASE_URL...")
    # This is tricky without password.
    # Usually users have DATABASE_URL in .env if they do DB migrations.
    # If not, I can try to use the supabase client's `rpc` if there's an `exec_sql` function exposed (unlikely).
    # OR, I can ask the user to run it manually in the dashboard.
    
    # Let's check if there's a DATABASE_URL first.
    print("Please ensure DATABASE_URL is set in .env for direct SQL execution.")
    print("Format: postgres://postgres:[PASSWORD]@[HOST]:5432/postgres")
    
    # For now, I'll assume I can't run DDL via the REST API client.
    # I will try to use the `supabase-py` client's `.rpc()` if a helper exists? No.
    
    # I will print instructions if I can't connect.
    pass

def run_migration():
    if not DB_URL:
        print("❌ Error: DATABASE_URL not found.")
        print("Please run the SQL manually in Supabase SQL Editor:")
        with open('migrations/create_ai_job_queue.sql', 'r') as f:
            print(f.read())
        return

    try:
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        with open('migrations/create_ai_job_queue.sql', 'r') as f:
            sql = f.read()
            
        print("Executing migration...")
        cur.execute(sql)
        conn.commit()
        print("✅ Migration successful!")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    run_migration()
