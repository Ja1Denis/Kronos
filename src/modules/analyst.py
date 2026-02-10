import asyncio
import os
import json
from typing import List, Dict, Any
from src.modules.historian import Historian
from src.modules.librarian import Librarian
from src.modules.notification_manager import notification_manager
from src.utils.logger import logger

class ProactiveAnalyst:
    """
    Analizira svježe indeksirane podatke i šalje proaktivne obavijesti
    (upozorenja o kontradikcijama, preporuke, povezani zadaci).
    """
    def __init__(self):
        self.historian = Historian()
        self.librarian = Librarian()
        # Proaktivnost se može isključiti preko varijable okruženja KRONOS_PROACTIVE=false
        self.enabled = os.environ.get("KRONOS_PROACTIVE", "true").lower() == "true"

    async def analyze_ingest(self, file_paths: List[str], project: str = "default"):
        """
        Pokreće se nakon ingestije jednog ili više fajlova.
        """
        if not self.enabled:
            return
            
        logger.info(f"🧠 ProactiveAnalyst analizira {len(file_paths)} novih datoteka...")
        
        for file_path in file_paths:
            try:
                # 1. Pročitaj sadržaj (za potrebe analize Historian-u)
                if not os.path.exists(file_path):
                    continue
                    
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                if not content.strip():
                    continue

                # 2. Provjera kontradikcija (Historian)
                # Limitiramo analizu na prvih 5000 znakova radi brzine ako je file velik
                brief_content = content[:5000]
                print(f"🧐 Historian razmišlja o {os.path.basename(file_path)}...")
                analysis = self.historian.find_contradictions(brief_content, project=project)
                print(f"🔍 Rezultat analize: {json.dumps(analysis, indent=2)}")
                
                if analysis.get("contradiction_found"):
                    logger.warning(f"⚠️ Detektirana kontradikcija u {os.path.basename(file_path)}!")
                    await notification_manager.broadcast("suggestion", {
                        "type": "contradiction",
                        "file": os.path.basename(file_path),
                        "file_path": file_path,
                        "explanation": analysis.get("explanation"),
                        "suggestion": analysis.get("suggestion"),
                        "conflicting_ids": analysis.get("conflicting_entity_ids", [])
                    })
                
                # 3. TODO: Provjera povezanih taskova (Task Discovery)
                # Ovdje možemo dodati logiku: "Vidio sam da pišeš o X, imamo otvoren task Y."
                
            except Exception as e:
                logger.error(f"❌ Greška pri proaktivnoj analizi datoteke {file_path}: {e}")

    async def analyze_query(self, query: str, results: Dict[str, Any]):
        """
        Može se pokrenuti nakon Oracle.ask() da ponudi 'usputne' savjete.
        """
        pass

# Globalna instanca
proactive_analyst = ProactiveAnalyst()
