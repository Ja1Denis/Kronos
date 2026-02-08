import google.generativeai as genai
import os
from dotenv import load_dotenv

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
workspace_root = os.path.dirname(project_root)
env_path = os.path.join(workspace_root, '.agent', '.env')

load_dotenv(env_path)
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("Nema API ključa.")
else:
    genai.configure(api_key=api_key)
    print("Dostupni modeli:")
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
    except Exception as e:
        print(f"Greška pri listanju modela: {e}")
