"""Test exact tournament_ai.py configuration"""
import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))

print("Testing with exact tournament_ai.py config...")
try:
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(
        "Reply with: OK",
        generation_config={
            "temperature": 0.3,
            "max_output_tokens": 100
        }
    )
    print(f"SUCCESS: {response.text}")
except Exception as e:
    print(f"FAILED: {e}")
