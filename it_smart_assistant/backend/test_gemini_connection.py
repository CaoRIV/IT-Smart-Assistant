
import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load env vars
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"Testing with API Key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")

if not api_key:
    print("Error: GOOGLE_API_KEY not found.")
    exit(1)

genai.configure(api_key=api_key)

print("Listing available models...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(m.name)
except Exception as e:
    print(f"Error listing models: {e}")

print("\nTrying legacy gemini-pro...")
try:
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content("Hello")
    print(f"Success with gemini-pro: {response.text}")
except Exception as e:
    print(f"Error with gemini-pro: {e}")
