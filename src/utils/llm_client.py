import os
from google import genai
from typing import Optional
from dotenv import load_dotenv

# Učitaj varijable iz .agent/.env datoteke
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
workspace_root = os.path.dirname(project_root)
env_path = os.path.join(workspace_root, '.agent', '.env')

load_dotenv(env_path)

class LLMClient:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
            
    def complete(self, prompt: str, model_name: str = "gemini-2.0-flash") -> str:
        """
        Generira tekstualni odgovor na temelju prompta using gemini-2.0-flash.
        """
        if not self.api_key or not self.client:
             return "MOCK ODGOVOR: Nema API ključa, vraćam dummy tekst. Molim postavite GEMINI_API_KEY."
        
        try:
            response = self.client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            
            # Osnovna provjera validnosti odgovora
            if not response.text:
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
