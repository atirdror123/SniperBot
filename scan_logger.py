"""
Structured Logging Module for SniperBot.
Provides consistent, traceable logging across all modules.
"""
import logging
import sys
from datetime import datetime

# Create formatter with timestamp, level, module, and message
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-15s | %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger for the specified module.
    Usage: logger = get_logger(__name__)
    """
    logger = logging.getLogger(name)
    
    # Avoid duplicate handlers if get_logger called multiple times
    if not logger.handlers:
        logger.setLevel(logging.DEBUG)
        
        # Console Handler (stdout)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
        logger.addHandler(console_handler)
    
    return logger


class ScanMetrics:
    """
    Tracks metrics for a single scan run.
    Provides summary statistics for debugging and monitoring.
    """
    def __init__(self):
        self.start_time = datetime.now()
        self.universe_size = 0
        self.batches_attempted = 0
        self.batches_succeeded = 0
        self.batches_failed = 0
        self.stocks_scanned = 0
        self.candidates_found = 0
        self.stocks_saved = 0
        self.errors = []  # List of (ticker, error_msg)
    
    def log_error(self, ticker: str, error: str):
        """Record an error for later analysis."""
        self.errors.append((ticker, error[:100]))  # Truncate long errors
    
    def get_summary(self) -> dict:
        """Returns a summary dict for logging/storage."""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return {
            "duration_seconds": round(elapsed, 1),
            "universe_size": self.universe_size,
            "batches_attempted": self.batches_attempted,
            "batches_succeeded": self.batches_succeeded,
            "batches_failed": self.batches_failed,
            "batch_success_rate": round(self.batches_succeeded / max(1, self.batches_attempted) * 100, 1),
            "stocks_scanned": self.stocks_scanned,
            "candidates_found": self.candidates_found,
            "stocks_saved": self.stocks_saved,
            "error_count": len(self.errors)
        }
    
    def __str__(self):
        s = self.get_summary()
        return (
            f"Duration: {s['duration_seconds']}s | "
            f"Batches: {s['batches_succeeded']}/{s['batches_attempted']} ({s['batch_success_rate']}%) | "
            f"Scanned: {s['stocks_scanned']} | Saved: {s['stocks_saved']}"
        )
