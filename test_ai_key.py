import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"Loaded Key: {api_key[:10]}...{api_key[-5:] if api_key else 'None'}")

try:
    genai.configure(api_key=api_key)
    print("Listing Models:")
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error: {e}")
