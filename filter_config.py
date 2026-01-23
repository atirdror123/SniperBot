"""
Pressure Cooker Filter Configuration

SCIENTIFICALLY TUNED from Phase 0 Data Mining:
- 175 picks analyzed
- 67.4% win rate
- Top Winners: BIOA +47%, BW +44%, MBX +34%

Winner Profile (from data):
- HUNTER = 90 (ALL winners had max HUNTER score)
- CHARTIST = 80
- QUANT = 69
- ORACLE = 62
"""

# WINNER PROFILE - Tuned from actual performance data
WINNER_PROFILE = {
    # RSI: Winners were in healthy momentum zone
    'rsi_min': 50,
    'rsi_max': 75,
    
    # Volume: At least 1.5x average (explosion signal)
    'rvol_min': 1.5,
    
    # Blue Sky: Within 5% of 52-week high (all winners were near highs)
    'pct_from_52w_high_min': 95,
    
    # Daily momentum: Moving but not overextended
    'daily_change_min': 2.0,
    'daily_change_max': 10.0,
    
    # Bollinger squeeze: Tight bands (compression before explosion)
    'bb_width_max': 0.15,
    
    # EMA alignment required
    'require_ema_alignment': True,  # Price > EMA20 > EMA50
}

# LENS WEIGHTS - Updated from winner analysis
LENS_WEIGHTS = {
    # HUNTER was 90 for ALL top 10 winners (most important!)
    'HUNTER': 1.5,    # Boost weight
    
    # CHARTIST was consistently 80
    'CHARTIST': 1.2,  # Strong weight
    
    # QUANT averaged 69 
    'QUANT': 1.0,     # Normal weight
    
    # ORACLE averaged 62
    'ORACLE': 0.8,    # Lower weight
}

# Position Sizing (Paper Trading)
POSITION_CONFIG = {
    'fixed_position_size': 2000,  # $2,000 per trade
    'max_positions': 3,           # Max 3 new positions per day
    'starting_capital': 100000,   # $100,000 virtual capital
}

# Exit Rules
EXIT_CONFIG = {
    'stop_loss_pct': -3.0,        # Hard stop at -3%
    'take_profit_1_pct': 5.0,     # First target: +5% (sell 50%)
    'take_profit_2_pct': 10.0,    # Second target: +10% (sell remaining)
    'time_stop_hours': 48,        # Exit if < 1% move in 48 hours
    'time_stop_min_move': 1.0,    # Minimum required move %
}

# Minimum lens score to be considered (based on winner profile)
MIN_LENS_SCORES = {
    'HUNTER': 85,     # Only consider if HUNTER >= 85
    'CHARTIST': 70,   # Only consider if CHARTIST >= 70
}
