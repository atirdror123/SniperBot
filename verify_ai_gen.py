import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"Testing Key: {api_key[:10]}...{api_key[-5:] if api_key else 'None'}")

# Try 2 common models
models_to_test = ['gemini-1.5-flash', 'gemini-flash-latest', 'gemini-pro']

for m_name in models_to_test:
    print(f"\n--- Testing Model: {m_name} ---")
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(m_name)
        response = model.generate_content("Say OK")
        print(f"SUCCESS: {response.text}")
        break # Stop if one works
    except Exception as e:
        print(f"FAILED: {e}")
