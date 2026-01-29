"""List models via raw API"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')

print("Listing available models via raw API...")

# Try v1beta
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
try:
    response = requests.get(url, timeout=30)
    print(f"v1beta Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        models = data.get('models', [])
        print(f"Found {len(models)} models:")
        for m in models[:10]:
            print(f"  - {m.get('name')}")
    else:
        print(f"Error: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")

# Try v1
print("\nTrying v1 endpoint...")
url2 = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"
try:
    response = requests.get(url2, timeout=30)
    print(f"v1 Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        models = data.get('models', [])
        print(f"Found {len(models)} models")
    else:
        print(f"Error: {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")
