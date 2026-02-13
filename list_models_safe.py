import os
from google import genai
from dotenv import load_dotenv

# Učitaj iz .agent/.env
project_root = os.path.dirname(os.path.abspath(__file__))
workspace_root = os.path.dirname(project_root)
load_dotenv(os.path.join(workspace_root, '.agent', '.env'))

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("Greška: GEMINI_API_KEY nije postavljen!")
    exit(1)

client = genai.Client(api_key=api_key)
print("Svi dostupni modeli na tvojem API ključu:")
for m in client.models.list():
    print(f"- {m.name}")
