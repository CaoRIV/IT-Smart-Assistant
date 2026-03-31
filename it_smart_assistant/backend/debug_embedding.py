import os
import httpx
import asyncio
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

print(f"Testing Key: ...{api_key[-5:] if api_key else 'None'}")

if not api_key:
    print("No API key found!")
    exit(1)

base_url = "https://generativelanguage.googleapis.com/v1"

async def list_models():
    url = f"{base_url}/models?key={api_key}"
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        print(f"List Models Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            print(f"\nFound {len(models)} models:\n")
            
            for m in models:
                name = m.get('name', '')
                methods = m.get('supportedGenerationMethods', [])
                print(f"- {name}")
                print(f"  Methods: {methods}")
                
                # Check for embedContent support
                if 'embedContent' in methods or 'batchEmbedContents' in methods:
                    print(f"  *** SUPPORTS EMBEDDING ***")
                print()
        else:
            print(f"Error: {response.text}")

async def test_embedding_models():
    """Test various embedding models"""
    models_to_test = [
        "embedding-001",
        "text-embedding-004", 
        "models/text-embedding-004",
        "models/embedding-001"
    ]
    
    print("\n=== Testing Embedding Models ===\n")
    
    async with httpx.AsyncClient() as client:
        for model in models_to_test:
            # Try without 'models/' prefix
            clean_model = model.replace("models/", "")
            url = f"{base_url}/models/{clean_model}:embedContent?key={api_key}"
            
            payload = {
                "content": {
                    "parts": [{"text": "Hello world"}]
                }
            }
            
            try:
                response = await client.post(url, json=payload)
                print(f"{model}: {response.status_code}")
                if response.status_code == 200:
                    print(f"  SUCCESS! Embedding dimension: {len(response.json().get('embedding', {}).get('values', []))}")
                else:
                    print(f"  Error: {response.text[:100]}")
            except Exception as e:
                print(f"{model}: ERROR - {e}")

async def main():
    await list_models()
    await test_embedding_models()

if __name__ == "__main__":
    asyncio.run(main())
