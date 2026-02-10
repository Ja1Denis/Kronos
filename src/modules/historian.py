import json
from src.modules.librarian import Librarian
from src.modules.oracle import Oracle
from src.utils.llm_client import LLMClient
from colorama import Fore, Style

class Historian:
    def __init__(self):
        self.librarian = Librarian()
        self.oracle = Oracle()
        self.llm = LLMClient()

    def find_contradictions(self, new_content: str, project: str = None):
        """
        Analizira novi sadržaj i traži kontradikcije s postojećim znanjem.
        """
        print(f"📜 Historian analizira konzistentnost za project={project}...")

        # 1. Pronađi relevantno postojeće znanje
        # Tražimo odluke i činjenice koje su semantički slične
        results = self.oracle.ask(new_content, project=project, limit=5, silent=True)
        
        existing_entities = results.get('entities', [])
        
        # Filtriraj samo Decisions i Facts (case-insensitive)
        relevant_knowledge = [
            e for e in existing_entities 
            if e['type'].lower() in ['decision', 'fact']
        ]
        
        if not relevant_knowledge:
            return {
                "contradiction_found": False,
                "reasoning": "Nema relevantnog postojećeg znanja za usporedbu."
            }

        # 2. Pripremi prompt za LLM
        knowledge_context = "\n".join([
            f"- [{e['type'].upper()} #{e['id']}] {e['content']}" 
            for e in relevant_knowledge
        ])

        prompt = f"""Ti si Historian, AI agent zadužen za očuvanje konzistentnosti baze znanja.
Tvoj zadatak je detektirati kontradikcije između NOVOG unosa i POSTOJEĆEG znanja.

NOVI UNOS:
"{new_content}"

POSTOJEĆE ZNANJE (iz baze):
{knowledge_context}

ANALIZA:
1. Da li novi unos direktno ili indirektno proturječi nekoj od navedenih postojećih informacija?
2. Ako da, koja točno informacija je u konfliktu (navedi ID)?
3. Koja je priroda konflikta (npr. promjena odluke, netočna činjenica, obratna logika)?

ODGOVOR (JSON format):
{{
    "contradiction_found": true/false,
    "conflicting_entity_ids": [id1, id2],
    "explanation": "Kratko objašnjenje konflikta...",
    "suggestion": "Sugestija što učiniti (npr. 'Ažuriraj odluku #5' ili 'Odbaci novi unos')"
}}
Vrati SAMO JSON.
"""

        # 3. Pozovi LLM (korištenje stabilnog modela)
        response = self.llm.complete(prompt, model_name="gemini-2.0-flash")
        
        # 4. Parsiraj odgovor
        try:
            # Thinking modeli često vraćaju puno teksta prije/poslije JSON-a
            clean_resp = response.strip()
            
            # Traži prvi '{' i zadnji '}'
            start = clean_resp.find('{')
            end = clean_resp.rfind('}')
            
            if start != -1 and end != -1:
                json_str = clean_resp[start:end+1]
                analysis = json.loads(json_str)
                return analysis
            else:
                raise ValueError("Nije pronađen validan JSON blok u odgovoru.")
            
        except Exception as e:
            print(f"❌ Greška pri parsiranju Historian analize: {e}")
            print(f"📄 Raw response preview: {response[:200]}...")
            return {
                "contradiction_found": False,
                "error": str(e)
            }

    def visualize_timeline(self, decision_id: int):
        """
        Vraća strukturirane podatke za vizualizaciju timeline-a odluke.
        """
        history = self.librarian.get_decision_history(decision_id)
        if not history:
            return None
            
        # Ovdje možemo dodati dodatnu analizu ako treba
        return history
