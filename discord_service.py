import os
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

def send_scan_report(signals):
    """
    Sends a rich formatted report to Discord via Webhook.
    """
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        print("[DISCORD] No Webhook URL found in .env. Skipping.")
        return

    if not signals:
        print("[DISCORD] No signals to report.")
        return

    # Sort by score
    signals.sort(key=lambda x: x.get('confidence_score', 0), reverse=True)
    top_picks = signals[:10]

    # Build Embed
    embed = {
        "title": f"🚀 Sniper Report: {datetime.now().strftime('%Y-%m-%d')}",
        "description": f"Scan complete. Found **{len(signals)}** potential setups.",
        "color": 5763719, # Greenish
        "fields": []
    }

    for s in top_picks:
        ticker = s.get('ticker')
        score = s.get('confidence_score', 0)
        price = s.get('entry_price', 0)
        
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
