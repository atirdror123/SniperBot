"""Test alternative models"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

models_to_try = ['gemini-1.5-flash', 'gemini-1.5-pro', 'gemini-pro']

for name in models_to_try:
    print(f"Testing {name}...")
    try:
        m = genai.GenerativeModel(name)
        r = m.generate_content("Say OK")
        print(f"  SUCCESS: {r.text[:30]}")
        break
    except Exception as e:
        err = str(e)[:80]
        print(f"  FAILED: {err}")
