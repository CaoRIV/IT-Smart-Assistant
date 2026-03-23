
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
print(f"Testing with Key: {api_key}")

# Try gemini-pro (legacy but stable)
print("--- Testing gemini-pro ---")
try:
    llm = ChatGoogleGenerativeAI(model="gemini-pro", google_api_key=api_key)
    res = llm.invoke("Hi")
    print("Success gemini-pro:", res.content)
except Exception as e:
    print("Failed gemini-pro:", e)

# Try gemini-1.5-pro
print("\n--- Testing gemini-1.5-pro ---")
try:
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro", google_api_key=api_key)
    res = llm.invoke("Hi")
    print("Success gemini-1.5-pro:", res.content)
except Exception as e:
    print("Failed gemini-1.5-pro:", e)
