"""
Paper Trading Engine - Position Manager

Manages paper trading positions with:
- Stop Loss: -3% hard stop
- Take Profit 1: +5% (sell 50%, move SL to breakeven)
- Take Profit 2: +10% (sell remaining)
- Time Stop: <1% move in 48 hours -> sell
"""
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv
import yfinance as yf
import pandas as pd

load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client
from filter_config import EXIT_CONFIG, POSITION_CONFIG
from scan_logger import get_logger

logger = get_logger("POSITION_MANAGER")


def get_supabase():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)


def get_current_price(ticker: str) -> float:
    """Get current price for a ticker."""
    try:
        data = yf.download(ticker, period="1d", progress=False)
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except:
        pass
    return None


def check_positions():
    """
    Check all open positions and apply exit rules.
    Run this periodically (every hour or so).
    """
    logger.info("=" * 60)
    logger.info("POSITION MANAGER: Checking Exit Conditions")
    logger.info("=" * 60)
    
    supabase = get_supabase()
    
    # Get all open SNIPER positions
    response = supabase.table('paper_positions').select('*').eq('status', 'OPEN').eq('portfolio', 'SNIPER').execute()
    positions = response.data
    
    if not positions:
        logger.info("No open positions to check.")
        return
    
    logger.info(f"Checking {len(positions)} open positions...")
    
    for pos in positions:
        ticker = pos['ticker']
        entry_price = pos['entry_price']
        entry_date = pos.get('entry_date', '')
        quantity = pos['quantity']
        pos_id = pos['id']
        
        # Get current price
        current_price = get_current_price(ticker)
        if current_price is None:
            logger.warning(f"  {ticker}: Could not get price")
            continue
        
        # Calculate returns
        pct_change = ((current_price - entry_price) / entry_price) * 100
        
        # Check exit conditions
        exit_reason = None
        exit_qty = 0
        
        # 1. STOP LOSS: -3%
        if pct_change <= EXIT_CONFIG['stop_loss_pct']:
            exit_reason = 'STOP_LOSS'
            exit_qty = quantity
            logger.info(f"  🔴 {ticker}: STOP LOSS triggered ({pct_change:.1f}%)")
        
        # 2. TAKE PROFIT 2: +10% (sell all remaining)
        elif pct_change >= EXIT_CONFIG['take_profit_2_pct']:
            exit_reason = 'TAKE_PROFIT_2'
            exit_qty = quantity
            logger.info(f"  🟢 {ticker}: TAKE PROFIT 2 triggered ({pct_change:.1f}%)")
        
        # 3. TAKE PROFIT 1: +5% (sell 50%)
        elif pct_change >= EXIT_CONFIG['take_profit_1_pct']:
            # Only trigger TP1 once (check if we already sold half)
            original_cost = pos.get('cost_basis', 0)
            current_value = quantity * entry_price
            
            # If current position is roughly original size, we haven't taken TP1 yet
            if abs(current_value - original_cost) < 100:  # Allow $100 tolerance
                exit_reason = 'TAKE_PROFIT_1'
                exit_qty = quantity // 2  # Sell half
                logger.info(f"  🟡 {ticker}: TAKE PROFIT 1 triggered ({pct_change:.1f}%) - selling 50%")
        
        # 4. TIME STOP: <1% move in 48 hours
        elif entry_date:
            try:
                entry_dt = datetime.fromisoformat(entry_date.replace('Z', '+00:00'))
                hours_held = (datetime.now(entry_dt.tzinfo) - entry_dt).total_seconds() / 3600
                
                if hours_held >= EXIT_CONFIG['time_stop_hours']:
                    if abs(pct_change) < EXIT_CONFIG['time_stop_min_move']:
                        exit_reason = 'TIME_STOP'
                        exit_qty = quantity
                        logger.info(f"  ⏱️ {ticker}: TIME STOP triggered ({hours_held:.0f}h, only {pct_change:.1f}% move)")
            except:
                pass
        
        # Execute exit if triggered
        if exit_reason and exit_qty > 0:
            execute_exit(supabase, pos, current_price, exit_reason, exit_qty)
        else:
            logger.info(f"  ⏸️ {ticker}: HOLD | Entry ${entry_price:.2f} | Now ${current_price:.2f} | {pct_change:+.1f}%")


def execute_exit(supabase, position: dict, exit_price: float, reason: str, qty: int):
    """Execute an exit order."""
    pos_id = position['id']
    ticker = position['ticker']
    entry_price = position['entry_price']
    total_qty = position['quantity']
    
    pnl = (exit_price - entry_price) * qty
    
    if qty >= total_qty:
        # Full exit - close position
        supabase.table('paper_positions').update({
            'status': 'CLOSED',
            'exit_price': exit_price,
            'exit_date': datetime.now().isoformat(),
            'exit_reason': reason,
            'pnl': pnl
        }).eq('id', pos_id).execute()
        
        logger.info(f"  💰 CLOSED {ticker}: {reason} | PnL: ${pnl:.2f}")
        
    else:
        # Partial exit - reduce position
        remaining_qty = total_qty - qty
        
        supabase.table('paper_positions').update({
            'quantity': remaining_qty,
            'cost_basis': remaining_qty * entry_price
        }).eq('id', pos_id).execute()
        
        # Log the partial sale as a separate closed position
        supabase.table('paper_positions').insert({
            'portfolio': 'SNIPER',
            'ticker': ticker,
            'entry_price': entry_price,
            'quantity': qty,
            'cost_basis': qty * entry_price,
            'status': 'CLOSED',
            'exit_price': exit_price,
            'exit_date': datetime.now().isoformat(),
            'exit_reason': reason,
            'pnl': pnl
        }).execute()
        
        logger.info(f"  💰 PARTIAL CLOSE {ticker}: {reason} | Sold {qty} @ ${exit_price:.2f} | PnL: ${pnl:.2f}")


def update_equity():
    """Calculate and save current portfolio equity."""
    logger.info("\n📊 Updating Equity...")
    
    supabase = get_supabase()
    
    # Get portfolio config
    config = supabase.table('portfolio_config').select('*').eq('id', 'SNIPER').execute()
    if not config.data:
        logger.warning("SNIPER portfolio not found")
        return
    
    starting_capital = config.data[0]['starting_capital']
    
    # Calculate realized PnL (closed positions)
    closed = supabase.table('paper_positions').select('pnl').eq('portfolio', 'SNIPER').eq('status', 'CLOSED').execute()
    realized_pnl = sum(pos.get('pnl', 0) or 0 for pos in closed.data)
    
    # Calculate unrealized PnL (open positions)
    open_positions = supabase.table('paper_positions').select('*').eq('portfolio', 'SNIPER').eq('status', 'OPEN').execute()
    
    unrealized_pnl = 0
    for pos in open_positions.data:
        ticker = pos['ticker']
        entry_price = pos['entry_price']
        quantity = pos['quantity']
        
        current_price = get_current_price(ticker)
        if current_price:
            unrealized_pnl += (current_price - entry_price) * quantity
    
    # Total equity
    total_equity = starting_capital + realized_pnl + unrealized_pnl
    
    # Update portfolio config
    supabase.table('portfolio_config').update({
        'current_equity': total_equity
    }).eq('id', 'SNIPER').execute()
    
    # Save to history
    supabase.table('equity_history').insert({
        'portfolio': 'SNIPER',
        'equity': total_equity
    }).execute()
    
    logger.info(f"  Starting Capital: ${starting_capital:,.2f}")
    logger.info(f"  Realized PnL:     ${realized_pnl:+,.2f}")
    logger.info(f"  Unrealized PnL:   ${unrealized_pnl:+,.2f}")
    logger.info(f"  Total Equity:     ${total_equity:,.2f}")


def run_position_check():
    """Full position management cycle."""
    check_positions()
    update_equity()
    logger.info("\n✅ Position check complete")


if __name__ == "__main__":
    run_position_check()
