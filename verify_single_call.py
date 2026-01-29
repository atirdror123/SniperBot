"""Verify Single API Call (Minimal)"""
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
print(f"API Key found: {bool(api_key)}")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

print("Sending 1 simple request...")
try:
    response = model.generate_content("Reply with number 1.")
    print(f"✅ Success! Response: {response.text}")
except Exception as e:
    print(f"❌ Failed: {e}")
