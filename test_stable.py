"""Test gemini-1.5-flash (stable)"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

print("Testing gemini-1.5-flash...")
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    r = model.generate_content("Reply with only: OK")
    print(f"SUCCESS: {r.text}")
except Exception as e:
    print(f"FAILED: {e}")

print("\nTesting gemini-1.5-flash-latest...")
try:
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    r = model.generate_content("Reply with only: OK")
    print(f"SUCCESS: {r.text}")
except Exception as e:
    print(f"FAILED: {e}")
