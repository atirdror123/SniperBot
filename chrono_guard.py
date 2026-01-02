"""
Layer 0: Chrono-Guard (Pre-Flight Market Status Check)

This module runs BEFORE any database connection or data fetching.
It checks if the market is open and terminates gracefully if not,
saving compute resources on weekends, holidays, and outside trading hours.
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

# NYSE Holiday Calendar (Updated Annually)
# Source: https://www.nyse.com/markets/hours-calendars
NYSE_HOLIDAYS = [
    # 2024
    "2024-01-01",  # New Year's Day
    "2024-01-15",  # MLK Day
    "2024-02-19",  # Presidents Day
    "2024-03-29",  # Good Friday
    "2024-05-27",  # Memorial Day
    "2024-06-19",  # Juneteenth
    "2024-07-04",  # Independence Day
    "2024-09-02",  # Labor Day
    "2024-11-28",  # Thanksgiving
    "2024-12-25",  # Christmas
    # 2025
    "2025-01-01",  # New Year's Day
    "2025-01-20",  # MLK Day
    "2025-02-17",  # Presidents Day
    "2025-04-18",  # Good Friday
    "2025-05-26",  # Memorial Day
    "2025-06-19",  # Juneteenth
    "2025-07-04",  # Independence Day
    "2025-09-01",  # Labor Day
    "2025-11-27",  # Thanksgiving
    "2025-12-25",  # Christmas
    # 2026
    "2026-01-01",  # New Year's Day
    "2026-01-19",  # MLK Day
    "2026-02-16",  # Presidents Day
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-06-19",  # Juneteenth
    "2026-07-03",  # Independence Day (observed)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving
    "2026-12-25",  # Christmas
]


class ChronoGuard:
    """
    Pre-flight check to determine if the market is open.
    Terminates the process gracefully if the market is closed.
    """
    
    def __init__(self, research_mode: bool = False):
        """
        Args:
            research_mode: If True, bypasses time-of-day check (for backtesting/research).
                           Still respects weekends and holidays.
        """
        self.research_mode = research_mode
        self.now_est = datetime.now(EST)
    
    def is_weekend(self) -> bool:
        """Returns True if today is Saturday (5) or Sunday (6)."""
        return self.now_est.weekday() >= 5
    
    def is_holiday(self) -> bool:
        """Returns True if today is an NYSE holiday."""
        today_str = self.now_est.strftime("%Y-%m-%d")
        return today_str in NYSE_HOLIDAYS
    
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
        
        # Check 1: Weekend
        if self.is_weekend():
            day_name = self.now_est.strftime("%A")
            logger.info(f"Market CLOSED: Weekend ({day_name}). Saving resources.")
            return False
        
        # Check 2: Holiday
        if self.is_holiday():
            logger.info(f"Market CLOSED: NYSE Holiday. Saving resources.")
            return False
        
        # Check 3: Trading Hours (bypassed in research mode)
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
