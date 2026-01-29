import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data.get('models', []))} models:")
        for m in data.get('models', []):
            print(f"  {m['name']}")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Error: {e}")
