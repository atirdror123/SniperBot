"""
Paper Trading Engine - Position Manager

Manages paper trading positions with:
- Stop Loss: -5% hard stop (gives trades room to breathe)
- Trailing Stop: Once up +5%, trails 3% below peak (lets winners run)
- Time Stop: 5 trading days with negative return → exit stale losers
- NO hard take profit ceiling — winners ride with trailing stop
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

    Exit priority:
    1. Hard stop loss (-5%) — protect capital
    2. Trailing stop (once activated) — lock in gains
    3. Time stop (5 trading days, still losing) — cut stale losers
    """
    logger.info("=" * 60)
    logger.info("POSITION MANAGER: Checking Exit Conditions")
    logger.info("=" * 60)

    supabase = get_supabase()

    # Get all open SNIPER trades from the V2 table
    response = supabase.table('sniper_trades').select('*').eq('status', 'OPEN').execute()
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

        # Track peak price for trailing stop (stored in DB or default to entry)
        peak_price = pos.get('peak_price', entry_price) or entry_price

        # Get current price
        current_price = get_current_price(ticker)
        if current_price is None:
            logger.warning(f"  {ticker}: Could not get price")
            continue

        # Update peak price if we have a new high
        if current_price > peak_price:
            peak_price = current_price
            try:
                supabase.table('sniper_trades').update({
                    'peak_price': peak_price
                }).eq('id', pos_id).execute()
            except Exception:
                pass  # peak_price column may not exist yet — non-fatal

        # Calculate returns
        pct_change = ((current_price - entry_price) / entry_price) * 100
        pct_from_peak = ((current_price - peak_price) / peak_price) * 100 if peak_price > 0 else 0

        # Check exit conditions (in priority order)
        exit_reason = None
        exit_qty = 0

        # 1. HARD STOP LOSS: -5%
        if pct_change <= EXIT_CONFIG['stop_loss_pct']:
            exit_reason = 'STOP_LOSS'
            exit_qty = quantity
            logger.info(f"  🔴 {ticker}: STOP LOSS triggered ({pct_change:.1f}%)")

        # 2. TRAILING STOP: Once up +5%, trail 3% below peak
        elif pct_change >= EXIT_CONFIG.get('trailing_stop_activation', 5.0):
            trailing_threshold = -EXIT_CONFIG.get('trailing_stop_pct', 3.0)
            if pct_from_peak <= trailing_threshold:
                exit_reason = 'TRAILING_STOP'
                exit_qty = quantity
                logger.info(f"  🟡 {ticker}: TRAILING STOP triggered (peak ${peak_price:.2f} → now ${current_price:.2f}, {pct_from_peak:.1f}% from peak)")

        # 3. TIME STOP: 5 trading days and still losing
        if not exit_reason and entry_date:
            try:
                entry_dt = datetime.fromisoformat(entry_date.replace('Z', '+00:00'))
                hours_held = (datetime.now(entry_dt.tzinfo) - entry_dt).total_seconds() / 3600

                if hours_held >= EXIT_CONFIG['time_stop_hours']:
                    # Only exit if the position is negative (stale loser)
                    if pct_change <= EXIT_CONFIG['time_stop_min_move']:
                        exit_reason = 'TIME_STOP'
                        exit_qty = quantity
                        logger.info(f"  ⏱️ {ticker}: TIME STOP triggered ({hours_held:.0f}h held, {pct_change:+.1f}% — stale loser)")
                    else:
                        logger.info(f"  ⏸️ {ticker}: Time limit reached but position is positive ({pct_change:+.1f}%) — holding")
            except:
                pass

        # Execute exit if triggered
        if exit_reason and exit_qty > 0:
            execute_exit(supabase, pos, current_price, exit_reason, exit_qty)
        else:
            trail_status = ""
            if pct_change >= EXIT_CONFIG.get('trailing_stop_activation', 5.0):
                trail_status = f" | Trailing active (peak ${peak_price:.2f})"
            logger.info(f"  ⏸️ {ticker}: HOLD | Entry ${entry_price:.2f} | Now ${current_price:.2f} | {pct_change:+.1f}%{trail_status}")


def execute_exit(supabase, position: dict, exit_price: float, reason: str, qty: int):
    """Execute an exit order."""
    pos_id = position['id']
    ticker = position['ticker']
    entry_price = position['entry_price']
    total_qty = position['quantity']

    pnl = (exit_price - entry_price) * qty

    if qty >= total_qty:
        # Full exit - close position
        supabase.table('sniper_trades').update({
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

        supabase.table('sniper_trades').update({
            'quantity': remaining_qty,
            'cost_basis': remaining_qty * entry_price
        }).eq('id', pos_id).execute()

        # Log the partial sale as a separate closed position
        supabase.table('sniper_trades').insert({
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

    # Calculate realized PnL (closed trades in sniper_trades)
    closed = supabase.table('sniper_trades').select('pnl').eq('status', 'CLOSED').execute()
    realized_pnl = sum(pos.get('pnl', 0) or 0 for pos in closed.data)

    # Calculate unrealized PnL (open trades in sniper_trades)
    open_positions = supabase.table('sniper_trades').select('*').eq('status', 'OPEN').execute()

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
