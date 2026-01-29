"""
Nightly AI Review - Self-Learning Feedback Loop
================================================
Reviews AI-scored stocks and updates lens weights based on outcomes.
Run this via cron/scheduler after market close.

Connects:
- AI Signal Engine (scoring) → Database (outcomes) → Reinforcement Learner (weight updates)
"""
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
from reinforcement_learner import SentientBrain
import yfinance as yf

load_dotenv()

def get_current_price(ticker: str) -> float:
    """Get current price for a ticker."""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period='1d')
        if not hist.empty:
            return hist['Close'].iloc[-1]
    except:
        pass
    return 0.0

def review_ai_stocks():
    """Review stocks scored by AI and update weights based on outcomes."""
    supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
    brain = SentientBrain()
    
    print("="*60)
    print("NIGHTLY AI REVIEW - SELF-LEARNING FEEDBACK LOOP")
    print("="*60)
    
    # Review periods: 10, 20, 30, 40, 50, 60 days
    REVIEW_PERIODS = [10, 20, 30, 40, 50, 60]
    
    total_reviews = 0
    
    for period in REVIEW_PERIODS:
        target_date = datetime.now() - timedelta(days=period)
        target_date_str = target_date.date().isoformat()
        next_date_str = (target_date + timedelta(days=1)).date().isoformat()
        
        print(f"\n--- Reviewing {period}-Day Outcomes (Entry: {target_date_str}) ---")
        
        # Find stocks entered on that date with AI scores
        try:
            response = supabase.table('sniper_signals')\
                .select('*')\
                .gte('created_at', target_date_str)\
                .lt('created_at', next_date_str)\
                .execute()
            
            stocks = response.data or []
            
            if not stocks:
                print(f"  No stocks found for {target_date_str}")
                continue
            
            print(f"  Found {len(stocks)} stocks to review")
            
            for stock in stocks:
                ticker = stock['ticker']
                entry_price = stock['entry_price']
                
                # Extract AI scores from raw_features
                raw_features = stock.get('raw_features', {})
                ai_scores = raw_features.get('ai_scores', {})
                
                if not ai_scores:
                    print(f"  ⚠️ {ticker}: No AI scores found, skipping")
                    continue
                
                # Calculate outcome
                current_price = get_current_price(ticker)
                if current_price == 0:
                    print(f"  ⚠️ {ticker}: Could not fetch current price, skipping")
                    continue
                
                outcome_pct = (current_price - entry_price) / entry_price
                
                # Prepare lens scores for learning
                lens_scores = {
                    'HUNTER': ai_scores.get('hunter', 0),
                    'QUANT': ai_scores.get('quant', 0),
                    'ORACLE': ai_scores.get('oracle', 0)
                }
                
                # Log outcome and adjust weights
                print(f"  📊 {ticker}: Entry ${entry_price:.2f} → Current ${current_price:.2f} ({outcome_pct*100:+.1f}%)")
                
                # Note: We don't have memory_id in sniper_signals, so we use stock ID
                # The reinforcement_learner expects memory_id from sentient_memory table
                # For now, we'll just update weights without logging to sentient_memory
                
                # Determine regime (simplified - should be stored at entry)
                regime = 'BULL'  # TODO: Store regime at entry time
                
                # Classify outcome
                if outcome_pct >= 0.10:
                    outcome_label = "WIN"
                    direction = 1
                elif outcome_pct <= -0.05:
                    outcome_label = "LOSS"
                    direction = -1
                else:
                    outcome_label = "HOLD"
                    direction = 0
                
                if direction != 0:
                    # Adjust weights directly
                    brain._adjust_weights(
                        regime=regime,
                        lens_scores=lens_scores,
                        direction=direction,
                        period_weight=brain.PERIOD_WEIGHTS.get(period, 0.15),
                        outcome_pct=outcome_pct,
                        period=period
                    )
                    total_reviews += 1
                    print(f"       → {outcome_label}: Weights adjusted")
                else:
                    print(f"       → {outcome_label}: No adjustment")
                    
        except Exception as e:
            print(f"  ❌ Error reviewing {period}d period: {e}")
            continue
    
    print("\n" + "="*60)
    print(f"REVIEW COMPLETE: {total_reviews} weight adjustments made")
    print("="*60)

if __name__ == '__main__':
    review_ai_stocks()
