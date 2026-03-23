
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
model_name = os.getenv("AI_MODEL", "gemini-1.5-flash")

print(f"Testing Model: {model_name}")
print(f"API Key Ends With: ...{api_key[-5:] if api_key else 'None'}")

if not api_key:
    print("Error: GOOGLE_API_KEY missing.")
    exit(1)

try:
    llm = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
    print(f"Sending request to {model_name}...")
    response = llm.invoke("Hello, simple response please.")
    print("--- SUCCESS ---")
    print(response.content)
    print("--- END ---")
except Exception as e:
    print("--- FAILED ---")
    print(f"Error: {e}")
