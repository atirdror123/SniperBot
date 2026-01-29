import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
# Valid model from list?
model = "models/gemini-2.0-flash-lite-preview-02-05" 

url = f"https://generativelanguage.googleapis.com/v1/{model}:generateContent?key={api_key}"
print(f"Testing {model}...")

try:
    response = requests.post(url, json={"contents": [{"parts": [{"text": "Hello"}]}]})
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
