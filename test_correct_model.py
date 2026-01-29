"""Test with correct model name"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

# Try the model that was listed as available
model = genai.GenerativeModel('models/gemini-2.5-flash-preview-04-17')

print("Testing gemini-2.5-flash...")
try:
    r = model.generate_content("Reply with: OK")
    print(f"SUCCESS: {r.text}")
except Exception as e:
    print(f"FAILED: {e}")
