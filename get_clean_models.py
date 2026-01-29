import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GOOGLE_API_KEY')
url = f"https://generativelanguage.googleapis.com/v1/models?key={api_key}"

try:
    response = requests.get(url)
    if response.status_code == 200:
        with open('clean_models.json', 'w') as f:
            json.dump(response.json(), f, indent=2)
        print("Models saved to clean_models.json")
    else:
        print(f"Error: {response.status_code} {response.text}")
except Exception as e:
    print(f"Error: {e}")
