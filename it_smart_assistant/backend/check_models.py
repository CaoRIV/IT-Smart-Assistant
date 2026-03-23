
import sys
import os
try:
    import google.generativeai as genai
except ImportError:
    print("google-generativeai not installed")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GOOGLE_API_KEY")
print(f"Checking key ending in: ...{api_key[-5:] if api_key else 'None'}")

if not api_key:
    print("No API key found in .env")
    sys.exit(1)

try:
    genai.configure(api_key=api_key)
    print("Listing available models:")
    count = 0
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"- {m.name}")
            count += 1
    if count == 0:
        print("No models found with generateContent capability.")
except Exception as e:
    print(f"CRITICAL ERROR: {e}")
