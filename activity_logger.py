"""
Activity Logger for Smart Cleaner
Logs all check/hold/sell actions to system_activity_logs table for dashboard transparency.
"""
import os
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

def get_supabase():
    """Get Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def log_activity(ticker: str, action: str, message: str):
    """
    Log an activity to the system_activity_logs table.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        action: One of 'CHECK', 'HOLD', 'SELL', 'BUY'
        message: Human-readable description (e.g., 'Price above stop loss')
    """
    supabase = get_supabase()
    if not supabase:
        print(f"[LOG] {action} {ticker}: {message}")
        return False
    
    try:
        supabase.table('system_activity_logs').insert({
            'ticker': ticker,
            'action': action,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }).execute()
        return True
    except Exception as e:
        # Table might not exist yet - log to console
        print(f"[LOG] {action} {ticker}: {message} (DB Error: {e})")
        return False


# Convenience functions
def log_check(ticker: str, condition: str):
    """Log a stock check with result."""
    log_activity(ticker, 'CHECK', f"Condition: {condition}")

def log_hold(ticker: str, reason: str):
    """Log a HOLD decision."""
    log_activity(ticker, 'HOLD', reason)

def log_sell(ticker: str, reason: str):
    """Log a SELL execution."""
    log_activity(ticker, 'SELL', reason)

def log_buy(ticker: str, details: str):
    """Log a BUY execution."""
    log_activity(ticker, 'BUY', details)


# SQL to create table (run in Supabase SQL Editor)
CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS system_activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ticker TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('CHECK', 'HOLD', 'SELL', 'BUY')),
    message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast timestamp queries
CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON system_activity_logs(timestamp DESC);
"""

if __name__ == "__main__":
    print("SQL to create system_activity_logs table:")
    print("="*50)
    print(CREATE_TABLE_SQL)
    print("="*50)
    print("\nTest logging...")
    log_activity("TEST", "CHECK", "System test log entry")
