"""Raw API test using requests (bypassing SDK)"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')

print("Testing raw API call (no SDK)...")
print(f"API Key: {api_key[:15]}...{api_key[-5:]}")

# Direct REST API call
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"

payload = {
    "contents": [{
        "parts": [{"text": "Reply with: OK"}]
    }]
}

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text[:500]}")
except Exception as e:
    print(f"Error: {e}")
