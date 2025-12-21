from discord_service import send_scan_report
import os
from dotenv import load_dotenv

# Ensure env is loaded (in case user added it but script needs reload)
load_dotenv()

# Mock Signal
dummy_signals = [
    {
        "ticker": "TEST-BOT",
        "confidence_score": 99.9,
        "entry_price": 123.45,
        "lens_scores": {}
    },
    {
        "ticker": "NVDA",
        "confidence_score": 88.5,
        "entry_price": 450.00,
        "lens_scores": {}
    }
]

print("Sending Test Report to Discord...")
send_scan_report(dummy_signals)
