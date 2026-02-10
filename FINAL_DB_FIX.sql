-- ============================================================================
-- 🎯 SNIPER BOT: FINAL DATABASE REPAIR SCRIPT
-- Run this in Supabase SQL Editor to fix EVERYTHING in one go.
-- ============================================================================

-- 1. ADD MISSING COLUMNS (Safe to run multiple times)
ALTER TABLE sniper_trades ADD COLUMN IF NOT EXISTS quantity INTEGER DEFAULT 1;
ALTER TABLE sniper_trades ADD COLUMN IF NOT EXISTS invested_amount FLOAT DEFAULT 0;
ALTER TABLE sniper_trades ADD COLUMN IF NOT EXISTS ai_score FLOAT; -- Ensure text/float type

-- 2. CREATE LOGGING TABLE
CREATE TABLE IF NOT EXISTS system_activity_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    ticker TEXT NOT NULL,
    action TEXT NOT NULL CHECK (action IN ('CHECK', 'HOLD', 'SELL', 'BUY')),
    message TEXT
);
CREATE INDEX IF NOT EXISTS idx_activity_logs_timestamp ON system_activity_logs(timestamp DESC);

-- 3. REMOVE DUPLICATES (Keep newest only)
DELETE FROM sniper_trades
WHERE id NOT IN (
  SELECT id FROM (
    SELECT DISTINCT ON (ticker) id
    FROM sniper_trades
    WHERE status = 'OPEN'
    ORDER BY ticker, created_at DESC
  ) as keep_rows
) AND status = 'OPEN';

-- 4. REPAIR DATA (GPRK, TSM, VIST)
-- GPRK: Fix values
UPDATE sniper_trades 
SET quantity = 235, invested_amount = 1995.15, ai_score = 81.5 
WHERE ticker = 'GPRK' AND status = 'OPEN';

-- TSM: Insert if missing
INSERT INTO sniper_trades (ticker, entry_price, quantity, invested_amount, status, ai_score, stop_loss_price, take_profit_price, notes)
SELECT 'TSM', 203.50, 9, 1831.50, 'OPEN', 76.5, 197.40, 223.85, 'Restored via Final Fix Script'
WHERE NOT EXISTS (SELECT 1 FROM sniper_trades WHERE ticker = 'TSM' AND status = 'OPEN');

-- VIST: Insert if missing
INSERT INTO sniper_trades (ticker, entry_price, quantity, invested_amount, status, ai_score, stop_loss_price, take_profit_price, notes)
SELECT 'VIST', 58.75, 34, 1997.50, 'OPEN', 76.5, 56.99, 64.63, 'Restored via Final Fix Script'
WHERE NOT EXISTS (SELECT 1 FROM sniper_trades WHERE ticker = 'VIST' AND status = 'OPEN');

-- 5. VERIFY
SELECT ticker, quantity, invested_amount, ai_score, status FROM sniper_trades WHERE status = 'OPEN';
