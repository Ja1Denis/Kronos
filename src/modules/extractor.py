import re
from typing import List, Dict, Any

class Extractor:
    def __init__(self):
        # Regex obrasci za ekstrakciju
        self.patterns = {
            "problem": re.compile(r"(?:^|\n)(?:[-*]\s+)?\**Problem[:?]?\**\s*(.*?)(?=\n|$)", re.IGNORECASE),
            "solution": re.compile(r"(?:^|\n)(?:[-*]\s+)?\**Rješenje[:?]?\**\s*(.*?)(?=\n|$)", re.IGNORECASE),
            "decision": re.compile(r"(?:^|\n)(?:[-*]\s+)?\**Odluka[:?]?\**\s*(.*?)(?=\n|$)", re.IGNORECASE),
            "task": re.compile(r"(?:^|\n)(?:[-*]\s+)?\[([ xX])\]\s*(.*?)(?=\n|$)", re.IGNORECASE),
            "code_block": re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
        }

    def extract(self, text: str) -> Dict[str, Any]:
        """
        Izvlači strukturirane podatke iz teksta.
        """
        extracted_data = {
            "problems": [],
            "solutions": [],
            "decisions": [],
            "tasks": [],
            "code_snippets": []
        }

        # 1. Problemi (Regex)
        for match in self.patterns["problem"].finditer(text):
            extracted_data["problems"].append(match.group(1).strip())

        # 2. Rješenja (Regex)
        for match in self.patterns["solution"].finditer(text):
            extracted_data["solutions"].append(match.group(1).strip())

        # 3. Zadaci (Regex)
        for match in self.patterns["task"].finditer(text):
            status = "done" if match.group(1).lower() == "x" else "todo"
            content = match.group(2).strip()
            if content and not content.startswith("<!--"):
                extracted_data["tasks"].append({"status": status, "content": content})

        # 4. Kodni blokovi (Regex)
        for match in self.patterns["code_block"].finditer(text):
            lang = match.group(1) or "text"
            snippet = match.group(2).strip()
            extracted_data["code_snippets"].append({
                "language": lang,
                "preview": snippet[:50] + "..." if len(snippet) > 50 else snippet
            })

        # 5. Odluke (Smart Parsing)
        # Iteriramo kroz linije da uhvatimo kontekst i metapodatke
        lines = text.split('\n')
        current_decision = None
        
        for line in lines:
            stripped = line.strip()
            
            # Detekcija početka odluke
            # Traži: "* Odluka:" ili "Odluka:"
            if not current_decision:
                match = re.search(r"(?:^|\s)\**Odluka[:?]?\**\s*(.*)", stripped, re.IGNORECASE)
                if match and not stripped.startswith("<!--"): # Ignoriraj HTML komentare
                    content = match.group(1).strip()
                    
                    # Parsiranje inline datuma [YYYY-MM-DD -> YYYY-MM-DD]
                    v_from, v_to = None, None
                    date_match = re.search(r"\[(\d{4}-\d{2}-\d{2})\s*->\s*(\d{4}-\d{2}-\d{2})\]", content)
                    if date_match:
                        v_from, v_to = date_match.groups()
                        content = content.replace(date_match.group(0), "").strip()

                    current_decision = {
                        "content": content,
                        "valid_from": v_from,
                        "valid_to": v_to,
                        "superseded_by": None
                    }
                continue
            
            # Ako smo u kontekstu odluke, tražimo metapodatke u idućim linijama
            if current_decision:
                lower = stripped.lower()
                
                # Metapodaci
                if lower.startswith("valid from:"):
                    current_decision['valid_from'] = stripped.split(":", 1)[1].strip()
                elif lower.startswith("valid to:"):
                    current_decision['valid_to'] = stripped.split(":", 1)[1].strip()
                elif lower.startswith("superseded by:"):
                    current_decision['superseded_by'] = stripped.split(":", 1)[1].strip()
                
                # Uvjeti za prekid konteksta:
                # 1. Prazna linija (često znači kraj bloka)
                # 2. Novi bullet point istog ili višeg nivoa (ovo je teško detektirati bez brojanja razmaka, 
                #    pa ćemo pretpostaviti da svaki novi bullet * ! - ili # prekida ako nije metadata)
                elif stripped == "" or (
                    (stripped.startswith("*") or stripped.startswith("-") or stripped.startswith("#")) 
                    and not any(x in lower for x in ["valid", "superseded"])
                ):
                    extracted_data["decisions"].append(current_decision)
                    current_decision = None
                    # Ako je ova linija možda nova odluka, trebali bi je re-procesirati, 
                    # ali za jednostavnost pretpostavljamo da odluke nisu jedna za drugom bez razmaka.
                    
        # Ako je zadnja linija bila dio odluke
        if current_decision:
            extracted_data["decisions"].append(current_decision)

        return extracted_data

    def summarize_extraction(self, data: Dict[str, Any]) -> str:
        """Kreira kratki sažetak ekstrahiranih podataka za ispis."""
        summary = []
        if data["problems"]: summary.append(f"🛑 {len(data['problems'])} Problema")
        if data["solutions"]: summary.append(f"✅ {len(data['solutions'])} Rješenja")
        if data["decisions"]: summary.append(f"⚖️ {len(data['decisions'])} Odluka")
        if data["tasks"]: summary.append(f"📋 {len(data['tasks'])} Zadataka")
        if data["code_snippets"]: summary.append(f"💻 {len(data['code_snippets'])} Kodnih blokova")
        
        return ", ".join(summary) if summary else "Nema strukturiranih podataka."
