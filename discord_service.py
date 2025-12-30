import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def send_scan_report(signals):
    """
    Sends a rich formatted report to Discord via Webhook.
    Handles both StockSetup objects and dictionaries.
    """
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[DISCORD] No Webhook URL found in .env. Skipping.")
        return

    if not signals:
        print("[DISCORD] No signals to report.")
        return

    # Helper to get value from either object or dict
    def get_val(item, key, default=0):
        if hasattr(item, key):
            return getattr(item, key, default)
        elif isinstance(item, dict):
            return item.get(key, default)
        return default

    # Sort by score (handle both attribute and dict access)
    signals_list = list(signals)
    signals_list.sort(key=lambda x: get_val(x, 'final_score', 0) or get_val(x, 'confidence_score', 0), reverse=True)
    top_picks = signals_list[:10]

    # Build Embed
    embed = {
        "title": f"🚀 Sniper Report: {datetime.now().strftime('%Y-%m-%d')}",
        "description": f"Scan complete. Found **{len(signals_list)}** potential setups.",
        "color": 5763719, # Greenish
        "fields": []
    }

    for s in top_picks:
        ticker = get_val(s, 'ticker', 'N/A')
        score = get_val(s, 'final_score', 0) or get_val(s, 'confidence_score', 0)
        price = get_val(s, 'price', 0) or get_val(s, 'entry_price', 0)
        
        field_value = f"**{score:.1f}** | ${price:.2f}"
        embed["fields"].append({
            "name": f"${ticker}",
            "value": field_value,
            "inline": True
        })

    payload = {
        "username": "Sentient Sniper",
        "embeds": [embed]
    }

    try:
        response = requests.post(webhook_url, json=payload)
        if response.status_code == 204:
            print("[DISCORD] Report sent successfully!")
        else:
            print(f"[DISCORD] Failed to send: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[DISCORD] Error sending webhook: {e}")

def send_message(content, username="Sniper Alert"):
    """
    Sends a simple text message to Discord.
    """
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url: return

    payload = {
        "username": username,
        "content": content
    }
    
    try:
        requests.post(webhook_url, json=payload)
    except: pass
