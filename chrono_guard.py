"""
Layer 0: Chrono-Guard (Pre-Flight Market Status Check)

This module runs BEFORE any database connection or data fetching.
It checks if the market is open and terminates gracefully if not,
saving compute resources on weekends, holidays, and outside trading hours.

Uses exchange_calendars for dynamic NYSE calendar (no manual holiday updates needed).
"""
import sys
from datetime import datetime, time
from zoneinfo import ZoneInfo
from scan_logger import get_logger

logger = get_logger("CHRONO_GUARD")

# NYSE Trading Hours (Eastern Time)
MARKET_OPEN = time(9, 30)
MARKET_CLOSE = time(16, 0)
EST = ZoneInfo("America/New_York")


class ChronoGuard:
    """
    Pre-flight check to determine if the market is open.
    Uses exchange_calendars for accurate, dynamic holiday detection.
    """
    
    def __init__(self, research_mode: bool = False):
        """
        Args:
            research_mode: If True, bypasses time-of-day check (for backtesting/research).
                           Still respects weekends and holidays.
        """
        self.research_mode = research_mode
        self.now_est = datetime.now(EST)
        self._nyse_calendar = None
    
    def _get_nyse_calendar(self):
        """Lazy-load NYSE calendar to avoid import overhead if not needed."""
        if self._nyse_calendar is None:
            try:
                import exchange_calendars as xcals
                self._nyse_calendar = xcals.get_calendar("XNYS")  # NYSE
            except ImportError:
                logger.warning("exchange_calendars not installed. Using fallback.")
                self._nyse_calendar = None
        return self._nyse_calendar
    
    def is_weekend(self) -> bool:
        """Returns True if today is Saturday (5) or Sunday (6)."""
        return self.now_est.weekday() >= 5
    
    def is_trading_day(self) -> bool:
        """
        Returns True if today is a valid NYSE trading session.
        Uses exchange_calendars for accurate holiday detection.
        """
        calendar = self._get_nyse_calendar()
        
        if calendar is None:
            # Fallback: only check weekend if calendar unavailable
            return not self.is_weekend()
        
        try:
            import pandas as pd
            today = pd.Timestamp(self.now_est.date(), tz='UTC')
            return calendar.is_session(today)
        except Exception as e:
            logger.warning(f"Calendar check failed: {e}. Falling back to weekend check.")
            return not self.is_weekend()
    
    def is_market_hours(self) -> bool:
        """Returns True if current time is within trading hours (9:30 AM - 4:00 PM EST)."""
        current_time = self.now_est.time()
        return MARKET_OPEN <= current_time <= MARKET_CLOSE
    
    def check_and_gate(self) -> bool:
        """
        Main check method. Returns True if market is OPEN and scanning should proceed.
        Returns False and logs reason if market is CLOSED.
        
        Does NOT exit - caller decides what to do with the result.
        """
        logger.info(f"Chrono-Guard Check: {self.now_est.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Check 1: Is today a trading day? (Handles weekends AND holidays)
        if not self.is_trading_day():
            day_name = self.now_est.strftime("%A, %B %d")
            logger.info(f"Market CLOSED: {day_name} is not a trading day. Saving resources.")
            return False
        
        # Check 2: Trading Hours (bypassed in research mode)
        if not self.research_mode and not self.is_market_hours():
            current_time_str = self.now_est.strftime("%H:%M %Z")
            logger.info(f"Market CLOSED: Outside trading hours ({current_time_str}). Saving resources.")
            return False
        
        logger.info("Market OPEN. Proceeding with scan.")
        return True
    
    def enforce(self):
        """
        Performs check and exits the process if market is closed.
        This is the "hard gate" version.
        """
        if not self.check_and_gate():
            logger.info("Chrono-Guard: Terminating process (exit code 0).")
            sys.exit(0)


def pre_flight_check(research_mode: bool = False):
    """
    Convenience function to run the Chrono-Guard check.
    Call this at the VERY START of main_sentient.py, before any imports.
    
    Args:
        research_mode: If True, allows running outside market hours.
    """
    guard = ChronoGuard(research_mode=research_mode)
    guard.enforce()


# Allow direct execution for testing
if __name__ == "__main__":
    guard = ChronoGuard(research_mode=False)
    is_open = guard.check_and_gate()
    print(f"Market Open: {is_open}")
