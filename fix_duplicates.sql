-- FIX DUPLICATES: Keep only the latest OPEN trade for each ticker
DELETE FROM sniper_trades
WHERE id NOT IN (
  SELECT id FROM (
    SELECT DISTINCT ON (ticker) id
    FROM sniper_trades
    WHERE status = 'OPEN'
    ORDER BY ticker, created_at DESC
  ) as keep_rows
) AND status = 'OPEN';

-- Verify count
SELECT ticker, count(*) 
FROM sniper_trades 
WHERE status = 'OPEN' 
GROUP BY ticker;
