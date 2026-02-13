"""
Kronos MCP Server - Model Context Protocol integracija.

Ovaj modul omogućuje korištenje Kronosa kao alata u Claude Desktop,
Gemini CLI i drugim MCP-kompatibilnim klijentima.

Alati:
- kronos_search: Semantička pretraga baze znanja
- kronos_stats: Statistika baze podataka
- kronos_decisions: Dohvaćanje aktivnih odluka
"""

import os
import sys
import builtins
import contextlib
import io
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

# --- AGRESIVNI MCP ŠTIT (Windows / Stdio) ---
# Spremamo originalne objekte i deskriptore
_real_stdout = sys.stdout
_real_stderr = sys.stderr
_real_print = builtins.print
_original_stdout_fd = os.dup(sys.stdout.fileno())

# Definicija sigurnog printa
def mcp_safe_print(*args, **kwargs):
    # Uvijek šalje na stderr, bez obzira na sve
    kwargs['file'] = _real_stderr
    _real_print(*args, **kwargs)

# Zamijenimo globalni print
builtins.print = mcp_safe_print

class OutputDetector:
    """Šalje sve na stderr i sprječava pisanje po stdoutu."""
    def write(self, text):
        if text.strip():
            _real_stderr.write(f"\n[STDOUT LEAK]: {repr(text)}\n")
            _real_stderr.flush()
        return len(text)
    def flush(self):
        _real_stderr.flush()
    def fileno(self):
        # Važno: fileno() mora vratiti nešto, ali mi ćemo dup2 raditi na FD razini
        return 1 

# 1. Odmah preusmjeravamo sistemski stdout FD na stderr (FD 2)
os.dup2(sys.stderr.fileno(), sys.stdout.fileno())

# 2. Python-level zaštita
sys.stdout = OutputDetector()
# --------------------------------------------

# Učitaj varijable iz .env datoteke u kronos rootu
load_dotenv()

# Dodaj root direktorij u path za importanje modula
# __file__ je src/mcp_server.py, pa ROOT_DIR je parent od src = kronos
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from mcp.server.fastmcp import FastMCP
import contextlib

# Lazy load Kronos modula (izbjegavamo circular import)
_oracle = None
_librarian = None
_job_manager = None
_oracle_ready = False
_oracle_error = None

import threading
_oracle_init_event = threading.Event()

def _init_oracle_background():
    """Pozadinska inicijalizacija Oracle-a da ne blokira MCP handshake."""
    global _oracle, _oracle_ready, _oracle_error
    try:
        from src.modules.oracle import Oracle
        _oracle = Oracle(os.path.join(ROOT_DIR, "data", "store"))
        _oracle_ready = True
    except Exception as e:
        _oracle_error = str(e)
    finally:
        _oracle_init_event.set()

# Pokreni inicijalizaciju u pozadini ODMAH
threading.Thread(target=_init_oracle_background, daemon=True).start()

def get_job_manager():
    """Dohvaća JobManager instancu."""
    global _job_manager
    if _job_manager is None:
        from src.modules.job_manager import JobManager
        _job_manager = JobManager(os.path.join(ROOT_DIR, "data", "jobs.db"))
    return _job_manager

def get_oracle():
    """Dohvaća Oracle instancu. Čeka da se pozadinska inicijalizacija završi."""
    global _oracle
    if not _oracle_ready:
        # Čekamo max 30 sekundi da se Oracle inicijalizira
        _oracle_init_event.wait(timeout=30)
    if _oracle_error:
        raise RuntimeError(f"Oracle init failed: {_oracle_error}")
    if _oracle is None:
        raise RuntimeError("Oracle init timeout (30s)")
    return _oracle

def get_librarian():
    """Dohvaća Librarian instancu (lazy loading)."""
    global _librarian
    if _librarian is None:
        from src.modules.librarian import Librarian
        _librarian = Librarian(os.path.join(ROOT_DIR, "data"))
    return _librarian


# Inicijaliziraj MCP server
mcp = FastMCP("kronos")


@mcp.tool()
def kronos_ping() -> str:
    """
    Test da li Kronos MCP server radi.
    
    Returns:
        Jednostavan 'pong' odgovor.
    """
    return "🏓 pong! Kronos MCP server is alive."


@mcp.tool()
def kronos_query(query: str, mode: str = "light") -> str:
    """
    Pitajte Kronos AI sustav o arhitekturi koda, specifičnim datotekama ili znanju o projektu.
    
    Args:
        query: Pitanje za Kronos (npr. "Kako radi Oracle klasa?")
        mode: Način upita: 'light' (1500 tokens), 'auto' (4000 tokens), 'extra' (8000 tokens).
    
    Returns:
        Odgovor baze znanja s relevantnim kontekstom.
    """
    try:
        from src.modules.context_budgeter import ContextComposer, ContextItem, BudgetConfig
        
        # Brza provjera - ako Oracle još nije spreman, javi korisniku
        if not _oracle_ready:
            remaining = 30
            _oracle_init_event.wait(timeout=remaining)
            if not _oracle_ready:
                return "⏳ Kronos se još zagrijava (ChromaDB inicijalizacija). Pokušaj ponovno za 5-10 sekundi."
        
        oracle = get_oracle()
        
        # Mapiranje moda na limite i budžete
        limit = 30
        config = None
        
        if mode == "light":
            limit = 15
            config = BudgetConfig.from_profile("light")
        elif mode == "extra":
            limit = 60
            config = BudgetConfig.from_profile("extra")
        else: # auto / default
            limit = 30
            config = BudgetConfig()

        # 1. Dohvat kandidata
        retrieval_results = oracle.ask(query, limit=limit, silent=True)
        
        if not retrieval_results or (not retrieval_results.get('entities') and not retrieval_results.get('chunks')):
            return f"Nažalost, Kronos nije pronašao relevantne informacije za: '{query}'"
            
        # 2. Sastavljanje konteksta pomoću Budgetera
        composer = ContextComposer(config=config)
        
        # Dodaj entitete
        for e in retrieval_results.get('entities', []):
            composer.add_item(ContextItem(
                kind="entity",
                content=e['content'],
                source=e.get('metadata', {}).get('source', 'Unknown'),
                utility_score=0.9
            ))
            
        # Dodaj chunkove
        for c in retrieval_results.get('chunks', []):
            composer.add_item(ContextItem(
                kind="chunk",
                content=c['content'],
                source=c.get('metadata', {}).get('source', 'Unknown'),
                utility_score=c.get('score', 0.5)
            ))
            
        # 3. Finalni formatirani odgovor
        return composer.compose()
    
    except Exception as e:
        return f"Greška u kronos_query: {str(e)}"


@mcp.tool()
def kronos_search(query: str, project: str = None, limit: int = 5) -> str:
    """
    Pretraži bazu znanja koristeći semantičku pretragu.
    
    Args:
        query: Tekst upita za pretragu (npr. "Kako radi hybrid search?")
        project: Opcionalno ime projekta za filtriranje rezultata
        limit: Maksimalni broj rezultata (default: 5)
    
    Returns:
        Formatiran tekst s relevantnim rezultatima iz baze znanja.
    """
    try:
        oracle = get_oracle()
        results = oracle.ask(query, project=project, limit=limit, silent=True)
        
        if not results:
            return f"Nema rezultata za upit: '{query}'"
        
        output = [f"## Rezultati pretrage: '{query}'\n"]
        
        entities = results.get('entities', [])
        chunks = results.get('chunks', [])
        
        all_res = entities + chunks
        
        for i, res in enumerate(all_res, 1):
            content = res.get('content', '')
            metadata = res.get('metadata', {})
            source = metadata.get('source', 'Nepoznato')
            proj = metadata.get('project', '-')
            score = res.get('score', 0)
            res_type = res.get('type', 'Chunk')
            
            relevance = round(score * 100, 1) if score else 0
            
            output.append(f"### Rezultat {i} [{res_type}] (Relevantnost: {relevance}%)")
            output.append(f"**Izvor:** `{os.path.basename(source)}` | **Projekt:** {proj}\n")
            output.append(f"```\n{content[:500]}{'...' if len(content) > 500 else ''}\n```\n")
        
        return "\n".join(output)
    
    except Exception as e:
        return f"Greška pri pretrazi: {str(e)}"


@mcp.tool()
def kronos_stats() -> str:
    """
    Dohvati statistiku Kronos baze podataka.
    
    Returns:
        Formatirani pregled statistike (broj datoteka, chunkova, entiteta, veličina baze).
    """
    try:
        librarian = get_librarian()
        stats = librarian.get_stats()
        
        output = ["## 📊 Kronos Statistika\n"]
        output.append(f"| Metrika | Vrijednost |")
        output.append(f"|---------|------------|")
        output.append(f"| **Datoteke** | {stats.get('total_files', 0):,} |")
        output.append(f"| **Chunkovi** | {stats.get('total_chunks', 0):,} |")
        output.append(f"| **SQLite veličina** | {stats.get('db_size_kb', 0):.1f} KB |")
        output.append(f"| **ChromaDB veličina** | {stats.get('chroma_size_kb', 0):.1f} KB |")
        
        entities = stats.get('entities', {})
        if entities:
            output.append(f"\n### 🏷️ Entiteti")
            output.append(f"| Tip | Broj |")
            output.append(f"|-----|------|")
            for etype, count in entities.items():
                emoji = {"problem": "🛑", "solution": "✅", "decision": "⚖️", "task": "📋", "code": "💻"}.get(etype, "📝")
                output.append(f"| {emoji} {etype.capitalize()} | {count:,} |")
        
        # Job Queue Stats
        try:
            jm = get_job_manager()
            jstats = jm.get_job_stats()
            output.append(f"\n### 🕒 Job Queue")
            output.append(f"| Status | Broj |")
            output.append(f"|--------|------|")
            for status, count in jstats.get('counts', {}).items():
                output.append(f"| {status.capitalize()} | {count} |")
            output.append(f"\n- **Ukupno poslova:** {jstats['total']}")
            output.append(f"- **Success Rate:** {jstats['success_rate']}")
            output.append(f"- **Prosječna latencija:** {jstats['avg_latency_sec']}")
        except Exception as e:
            output.append(f"\n*Greška pri dohvaćanju Job Queue stats: {e}*")
            
        return "\n".join(output)
        
    except Exception as e:
        return f"Greška pri dohvaćanju statistike: {str(e)}"


@mcp.tool()
def kronos_decisions(project: str = None, date: str = None) -> str:
    """
    Dohvati aktivne odluke iz baze znanja.
    
    Args:
        project: Opcionalno ime projekta za filtriranje
        date: Datum u formatu YYYY-MM-DD (default: danas)
    
    Returns:
        Lista aktivnih odluka s njihovim vremenskim okvirom.
    """
    try:
        librarian = get_librarian()
        decisions = librarian.get_active_decisions(project=project, date=date)
        
        if not decisions:
            filter_msg = f" za projekt '{project}'" if project else ""
            return f"Nema aktivnih odluka{filter_msg}."
        
        output = [f"## ⚖️ Aktivne Odluke ({len(decisions)})\n"]
        
        for i, dec in enumerate(decisions, 1):
            content = dec.get('content', 'Bez sadržaja')
            v_from = dec.get('valid_from') or 'Nedefinirano'
            v_to = dec.get('valid_to') or 'Nedefinirano'
            source = os.path.basename(dec.get('file_path', 'Nepoznato'))
            
            output.append(f"### {i}. {content[:100]}{'...' if len(content) > 100 else ''}")
            output.append(f"- **Vrijedi:** {v_from} → {v_to}")
            output.append(f"- **Izvor:** `{source}`\n")
        
        return "\n".join(output)
        
    except Exception as e:
        return f"Greška pri dohvaćanju odluka: {str(e)}"


@mcp.tool()
def kronos_ingest(path: str, recursive: bool = True) -> str:
    """
    Indeksira datoteke u Kronos bazu znanja.
    
    Args:
        path: Putanja do datoteke ili direktorija za indeksiranje
        recursive: Ako je True, rekurzivno indeksira poddirektorije (default: True)
    
    Returns:
        Poruka o statusu indeksiranja.
    """
    try:
        from src.modules.ingestor import Ingestor
        
        ingestor = Ingestor(db_path=os.path.join(ROOT_DIR, "data"))
        
        # Provjeri postoji li putanja
        full_path = os.path.abspath(path)
        if not os.path.exists(full_path):
            return f"Putanja ne postoji: {full_path}"
        
        ingestor.run(path=full_path, recursive=recursive, silent=True)
        
        return f"✅ Uspješno indeksirano: `{full_path}` (recursive={recursive})"
        
    except Exception as e:
        return f"Greška pri indeksiranju: {str(e)}"


@mcp.tool()
def kronos_submit_job(job_type: str, params: dict, priority: int = 5) -> str:
    """
    Pošalji novi asinkroni zadatak u Kronos red čekanja (Job Queue).
    Korisno za dugotrajne operacije poput 'ingest' ili 'rebuild'.
    
    Args:
        job_type: Tip zadatka (npr. 'ingest', 'ingest_batch', 'test_job')
        params: Parametri zadatka (npr. {"path": ".", "recursive": True})
        priority: Prioritet od 1 do 10 (default: 5)
        
    Returns:
        ID kreiranog posla koji se može pratiti.
    """
    try:
        jm = get_job_manager()
        job_id = jm.submit_job(job_type, params, priority)
        return f"🚀 Posao `{job_type}` uspješno poslan. ID: `{job_id}`. Koristi `kronos_job_status` za praćenje."
    except Exception as e:
        return f"Greška pri slanju posla: {str(e)}"


@mcp.tool()
def kronos_job_status(job_id: str) -> str:
    """
    Provjeri status i napredak određenog zadatka.
    
    Args:
        job_id: Jedinstveni ID posla dobiven pri slanju.
        
    Returns:
        Informacije o statusu, napretku, rezultatu ili grešci.
    """
    try:
        jm = get_job_manager()
        job = jm.get_job(job_id)
        
        if not job:
            return f"Posao s ID-om `{job_id}` nije pronađen."
            
        output = [f"### 📋 Status Posla: `{job_id}`"]
        output.append(f"- **Tip:** `{job['type']}`")
        output.append(f"- **Status:** `{job['status']}`")
        output.append(f"- **Napredak:** `{job['progress']}%`")
        output.append(f"- **Kreirano:** `{job['created_at']}`")
        
        if job.get('result'):
            output.append(f"\n**Rezultat:**\n```json\n{job['result']}\n```")
        if job.get('error'):
            output.append(f"\n**Greška:**\n```\n{job['error']}\n```")
            
        return "\n".join(output)
    except Exception as e:
        return f"Greška pri provjeri statusa: {str(e)}"


@mcp.tool()
def kronos_list_jobs(limit: int = 10) -> str:
    """
    Prikaži listu nedavnih zadataka iz reda čekanja.
    
    Args:
        limit: Broj zadataka za prikaz (default: 10)
        
    Returns:
        Tablica s nedavnim poslovima.
    """
    try:
        jm = get_job_manager()
        jobs = jm.list_jobs(limit=limit)
        
        if not jobs:
            return "Nema evidentiranih poslova."
            
        output = ["## 🕒 Nedavni Poslovi\n"]
        output.append("| ID | Tip | Status | Napredak | Kreirano |")
        output.append("|----|-----|--------|----------|----------|")
        
        for job in jobs:
            short_id = job['id'][:8]
            created = job['created_at'].split('T')[1][:5] if 'T' in job['created_at'] else job['created_at'][-8:-3]
            output.append(f"| `{short_id}` | `{job['type']}` | `{job['status']}` | `{job['progress']}%` | {created} |")
            
        return "\n".join(output)
    except Exception as e:
        return f"Greška pri listanju poslova: {str(e)}"


def main():
    """Pokreće MCP server u stdio modu s debugging outputom."""
    import logging
    
    # Logging ide na stderr (ne smeta stdio transportu)
    logging.basicConfig(
        level=logging.INFO,
        format='[MCP Server] %(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)]
    )
    
    mcp_logger = logging.getLogger("kronos_mcp")
    mcp_logger.info("🚀 Kronos MCP Server starting...")
    mcp_logger.info(f"📂 Root dir: {ROOT_DIR}")
    
    try:
        # --- UKLANJAMO SELF-TEST ZBOG TIMEOUTA ---
        # mcp_logger.info("🔍 Testing Oracle initialization...")
        # oracle = get_oracle()
        # mcp_logger.info("✅ Oracle ready")
        # -----------------------------------------
        
        mcp_logger.info("💬 Starting MCP stdio server...")
        
        # --- KRITIČNA RESTAURACIJA ZA KOMUNIKACIJU ---
        # Vraćamo sistemski FD 1 (stdout) na njegovu pravu metu
        os.dup2(_original_stdout_fd, 1) # 1 je uvijek FD za stdout
        
        # Vraćamo i Python-level objekt na pravi stdout
        sys.stdout = _real_stdout
        
        # Pokrećemo server (ovo blokira)
        mcp.run(transport="stdio")
        
    except KeyboardInterrupt:
        mcp_logger.info("⚠️ Server interrupted by user")
    except Exception as e:
        mcp_logger.error(f"❌ Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
