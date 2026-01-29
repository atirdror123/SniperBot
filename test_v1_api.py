"""Test v1 endpoint with available model"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')

print("Testing v1 endpoint with gemini-2.0-flash-lite...")

# Use v1 endpoint instead of v1beta
url = f"https://generativelanguage.googleapis.com/v1/models/gemini-2.0-flash-lite:generateContent?key={api_key}"

payload = {
    "contents": [{
        "parts": [{"text": "Reply with: OK"}]
    }]
}

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        text = data.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
        print(f"SUCCESS! Response: {text}")
    else:
        print(f"Error: {response.text[:300]}")
except Exception as e:
    print(f"Error: {e}")
