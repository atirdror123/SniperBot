-- ============================================================================
-- HARD SEPARATION: Database Schema
-- Run this in Supabase SQL Editor
-- ============================================================================

-- 1. Create legacy_portfolio table (for old positions)
CREATE TABLE IF NOT EXISTS legacy_portfolio (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker TEXT NOT NULL,
    entry_price FLOAT8,
    quantity INT4 DEFAULT 1,
    cost_basis FLOAT8,
    status TEXT DEFAULT 'OPEN',
    entry_date TIMESTAMPTZ DEFAULT NOW(),
    exit_price FLOAT8,
    exit_date TIMESTAMPTZ,
    exit_reason TEXT,
    pnl FLOAT8,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Create sniper_trades table (fresh V2 logic)
CREATE TABLE IF NOT EXISTS sniper_trades (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker TEXT NOT NULL,
    entry_price FLOAT8 NOT NULL,
    current_price FLOAT8,
    quantity INT4 DEFAULT 1,
    cost_basis FLOAT8,
    status TEXT DEFAULT 'OPEN',
    entry_date TIMESTAMPTZ DEFAULT NOW(),
    exit_date TIMESTAMPTZ,
    exit_price FLOAT8,
    exit_reason TEXT,
    stop_loss_price FLOAT8,
    take_profit_price FLOAT8,
    ai_score FLOAT8,
    pnl FLOAT8,
    notes TEXT,
    raw_features JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_legacy_status ON legacy_portfolio(status);
CREATE INDEX IF NOT EXISTS idx_sniper_status ON sniper_trades(status);
CREATE INDEX IF NOT EXISTS idx_sniper_ticker ON sniper_trades(ticker);

-- 4. Enable RLS (Row Level Security) - Optional but recommended
ALTER TABLE legacy_portfolio ENABLE ROW LEVEL SECURITY;
ALTER TABLE sniper_trades ENABLE ROW LEVEL SECURITY;

-- 5. Create policies for service role access
CREATE POLICY "Service role full access legacy" ON legacy_portfolio
    FOR ALL USING (true);

CREATE POLICY "Service role full access sniper" ON sniper_trades
    FOR ALL USING (true);

-- Done!
SELECT 'Tables created successfully!' as message;
