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

        # 1. Problemi
        for match in self.patterns["problem"].finditer(text):
            extracted_data["problems"].append(match.group(1).strip())

        # 2. Rješenja
        for match in self.patterns["solution"].finditer(text):
            extracted_data["solutions"].append(match.group(1).strip())

        # 3. Odluke
        for match in self.patterns["decision"].finditer(text):
            extracted_data["decisions"].append(match.group(1).strip())

        # 4. Zadaci (TODOs)
        for match in self.patterns["task"].finditer(text):
            status = "done" if match.group(1).lower() == "x" else "todo"
            content = match.group(2).strip()
            # Ignoriraj prazne ili metapodatke
            if content and not content.startswith("<!--"):
                extracted_data["tasks"].append({"status": status, "content": content})

        # 5. Kodni blokovi (samo analitika, ne sadržaj)
        for match in self.patterns["code_block"].finditer(text):
            lang = match.group(1) or "text"
            snippet = match.group(2).strip()
            # Spremi samo prvih 50 znakova kao preview
            extracted_data["code_snippets"].append({
                "language": lang,
                "preview": snippet[:50] + "..." if len(snippet) > 50 else snippet
            })

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
