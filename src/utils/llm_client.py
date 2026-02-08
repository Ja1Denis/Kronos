import os
import google.generativeai as genai
from typing import Optional
from dotenv import load_dotenv

# Učitaj varijable iz .agent/.env datoteke
# Putanja: kronos/src/utils/llm_client.py -> kronos -> workspace
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
workspace_root = os.path.dirname(project_root)
env_path = os.path.join(workspace_root, '.agent', '.env')

# print(f"DEBUG: Loading env from {env_path}")
load_dotenv(env_path)

class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            # Pokušaj naći u .env fileu ako postoji
            # Ovdje bi se mogla dodati dotenv logika, ali za sad se oslanjamo na environment varijable
            pass
        else:
            genai.configure(api_key=self.api_key)
            
    def complete(self, prompt: str, model_name: str = "gemini-2.5-flash") -> str:
        """
        Generira tekstualni odgovor na temelju prompta using gemini-2.5-flash.
        """
        if not self.api_key:
             return "MOCK ODGOVOR: Nema API ključa, vraćam dummy tekst. Molim postavite GEMINI_API_KEY."
        
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            # Osnovna provjera validnosti odgovora
            if not response.parts:
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    return f"BLOCKED: {response.prompt_feedback.block_reason}"
                return "ERROR: Prazan odgovor od modela."
                
            return response.text
        except Exception as e:
            return f"ERROR: {str(e)}"

if __name__ == "__main__":
    # Brzi test kad se pokrene skripta direktno
    client = LLMClient()
    print("Testiram LLM klijent (Gemini)...")
    odgovor = client.complete("Napiši jednu rečenicu o tome što je Kronos u grčkoj mitologiji.")
    print("-" * 20)
    print(odgovor)
    print("-" * 20)
