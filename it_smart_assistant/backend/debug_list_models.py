
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

print(f"Testing Key: ...{api_key[-5:] if api_key else 'None'}")

if not api_key:
    print("No API key found!")
    exit(1)

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"

try:
    print(f"GET {url.split('?')[0]}...")
    response = requests.get(url)
    
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        models = response.json().get('models', [])
        print(f"Found {len(models)} models:")
        for m in models:
            if 'generateContent' in m.get('supportedGenerationMethods', []):
                print(f"- {m['name']}")
    else:
        print("Error Response:")
        print(response.text)
        
except Exception as e:
    print(f"Request failed: {e}")
