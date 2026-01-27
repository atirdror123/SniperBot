-- AI Job Queue Table
-- Run this in Supabase SQL Editor

CREATE TABLE IF NOT EXISTS ai_job_queue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    ticker VARCHAR(10) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    priority INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    result JSONB,
    error_message TEXT
);

-- Index for efficient queue processing
CREATE INDEX IF NOT EXISTS idx_ai_job_queue_status ON ai_job_queue(status, priority DESC, created_at);

-- Index for ticker lookup
CREATE INDEX IF NOT EXISTS idx_ai_job_queue_ticker ON ai_job_queue(ticker);

-- Auto-cleanup: Delete completed jobs older than 7 days
-- (Optional: Run as a scheduled function)
-- DELETE FROM ai_job_queue WHERE status = 'completed' AND completed_at < NOW() - INTERVAL '7 days';

COMMENT ON TABLE ai_job_queue IS 'Queue for AI-powered stock analysis jobs. Processed by ai_signal_engine.py';
