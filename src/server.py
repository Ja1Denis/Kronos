from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import sys
import time

from src.modules.ingestor import Ingestor
from src.modules.oracle import Oracle
from src.modules.librarian import Librarian

app = FastAPI(title="Kronos API", description="Semantička Memorija za AI Agente", version="0.2.0")

# Model upita
class QueryRequest(BaseModel):
    text: str
    limit: Optional[int] = 5
    # New Context Budgeter params
    cursor_context: Optional[str] = None
    current_file_path: Optional[str] = None
    budget_tokens: Optional[int] = 4000
    mode: Optional[str] = "budget" # auto, budget, debug
    stack_trace: Optional[str] = None

class IngestRequest(BaseModel):
    path: str
    recursive: Optional[bool] = False

@app.get("/")
def read_root():
    return {"name": "Kronos API", "status": "online", "version": "0.2.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.post("/ingest")
def ingest_data(request: IngestRequest):
    """Pokreće ingestiju podataka s dane putanje."""
    try:
        ingestor = Ingestor()
        # Ingestor trenutno ne vraća detaljne podatke kroz .run(), 
        # ali možemo dohvatiti statse prije i poslije.
        stats_before = Librarian().get_stats()
        ingestor.run(request.path, recursive=request.recursive, silent=True)
        stats_after = Librarian().get_stats()
        
        new_chunks = stats_after['total_chunks'] - stats_before['total_chunks']
        return {
            "status": "success",
            "path": request.path,
            "new_chunks_indexed": new_chunks,
            "total_chunks": stats_after['total_chunks']
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# SINGLETON ORACLE INSTANCE
# To prevent database locking and overhead of reloading models
_oracle_instance = None

def get_oracle():
    global _oracle_instance
    if _oracle_instance is None:
        print("🔧 Initializing Singleton Oracle...")
        _oracle_instance = Oracle()
    return _oracle_instance

@app.post("/query")
def query_memory(request: QueryRequest):
    """Pretražuje semantičku memoriju i vraća optimizirani kontekst (Context Budgeter)."""
    try:
        from src.modules.context_budgeter import ContextComposer, ContextItem, BudgetConfig
        oracle = get_oracle() # Use singleton
        
        # Profile Selection based on mode
        config = None
        current_limit = request.limit or 30 # Default increased to 30 for better context utilization
        
        if request.mode == "auto":
            # Heuristic: If trace exists -> extra, if query is short -> light, else default
            if request.stack_trace:
                config = BudgetConfig.from_profile("extra")
                current_limit = 60
            elif len(request.text.split()) < 5:
                config = BudgetConfig.from_profile("light")
                current_limit = 15
            else:
                config = BudgetConfig()
                current_limit = 30
        elif request.mode == "light":
             config = BudgetConfig.from_profile("light")
             current_limit = 15
        elif request.mode == "extra":
             config = BudgetConfig.from_profile("extra")
             current_limit = 60
        else:
             # Custom budget tokens or default
             config = BudgetConfig(global_limit=request.budget_tokens or 4000)
             
        
        # 1. Retrieve candidates
        # Note: Oracle.ask returns dict {'entities': [...], 'chunks': [...]}
        retrieval_results = oracle.ask(request.text, limit=current_limit, silent=True)
             
        
        # Audit Log (Server Side)
        print(f"[{request.mode}] Query: '{request.text}' | Budget: {config.global_limit} | Cursor: {bool(request.cursor_context)} | File: {request.current_file_path}")
        
        composer = ContextComposer(config)
        
        # 3. Add Cursor Context (Priority 1)
        if request.cursor_context:
            composer.add_item(ContextItem(
                content=request.cursor_context,
                kind="cursor",
                source=request.current_file_path or "ACTIVE_EDITOR",
                utility_score=1.0
            ))
            
        # 3b. Debug Mode: Process Stack Trace (High Priority)
        # Ako imamo stack trace, parsiramo ga i dodajemo pronađene fajlove kao High Priority Chunks/Evidence
        if request.stack_trace:
            from src.utils.stack_parser import StackTraceParser
            trace_locations = StackTraceParser.parse(request.stack_trace)
            
            # Dodaj sam stack trace kao context
            composer.add_item(ContextItem(
                content=request.stack_trace,
                kind="evidence",
                source="StackTrace",
                utility_score=1.0 # Critical
            ))
            
            for loc in trace_locations:
                # Ovdje bi idealno trebali pročitati stvarni sadržaj datoteke
                # Za sada samo logiramo da smo našli lokaciju
                # TODO: Implementirati 'SnippetReader' koji čita +/- 10 linija oko loc['line']
                
                # Pokušajmo pročitati snippet ako fajl postoji
                fpath = loc.get('file')
                lineno = loc.get('line', 1)
                
                if fpath and os.path.exists(fpath):
                    try:
                        # Diff Corpse: Check if modified recently (last 1h)
                        mtime = os.path.getmtime(fpath)
                        is_recent = (time.time() - mtime) < 3600
                        recent_tag = " [RECENTLY MODIFIED]" if is_recent else ""
                        
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            lines = f.readlines()
                            start = max(0, lineno - 5)
                            end = min(len(lines), lineno + 5)
                            snippet = "".join(lines[start:end])
                            
                            composer.add_item(ContextItem(
                                content=f"--- SNIPPET FROM TRACE{recent_tag} ---\nLine {lineno}:\n{snippet}",
                                kind="evidence",
                                source=f"{os.path.basename(fpath)}:{lineno}",
                                utility_score=0.95 + (0.05 if is_recent else 0) # Boost if recent
                            ))
                    except Exception as e:
                        print(f"Error reading trace file {fpath}: {e}")
            
            # 3c. Log Corpse: Fetch recent system logs
            try:
                log_dir = "logs"
                if os.path.exists(log_dir):
                    log_files = sorted([f for f in os.listdir(log_dir) if f.endswith(".log")], reverse=True)
                    if log_files:
                        latest_log = os.path.join(log_dir, log_files[0])
                        with open(latest_log, 'rb') as f:
                            # Seek towards the end of file for efficiency
                            try:
                                f.seek(0, 2)
                                size = f.tell()
                                # Read last 4KB - usually enough for 30 lines
                                offset = min(size, 4096)
                                f.seek(-offset, 2)
                                raw_logs = f.read().decode('utf-8', errors='ignore')
                                # Take last 30 lines
                                recent_logs = "\n".join(raw_logs.splitlines()[-30:])
                                
                                composer.add_item(ContextItem(
                                    content=f"--- RECENT SYSTEM LOGS ---\n{recent_logs}",
                                    kind="evidence",
                                    source=f"logs/{log_files[0]}",
                                    utility_score=0.85 
                                ))
                            except Exception:
                                # Fallback if seek fails
                                f.seek(0)
                                content = f.read().decode('utf-8', errors='ignore')
                                recent_logs = "\n".join(content.splitlines()[-30:])
                                composer.add_item(ContextItem(content=recent_logs, kind="evidence", source=latest_log))
            except Exception as e:
                print(f"Error fetching logs: {e}")
            
        # 4. Add Entities & Chunks...
        for ent in retrieval_results.get("entities", []):
            composer.add_item(ContextItem(
                content=ent["content"],
                kind="entity",
                source=ent["metadata"].get("source", "unknown"),
                utility_score=0.9
            ))
            
        for chunk in retrieval_results.get("chunks", []):
            composer.add_item(ContextItem(
                content=chunk["content"],
                kind="chunk",
                source=chunk["metadata"].get("source", "unknown"),
                utility_score=chunk.get("score", 0.5)
            ))
            
        # 6. Compose Final Context
        final_context = composer.compose()
        audit_log = composer.get_audit_report()
        
        return {
            "query": request.text,
            "context": final_context,
            "audit": audit_log,
            "parsed_trace": bool(request.stack_trace),
            "stats": {
                "used_tokens": composer.current_tokens,
                "global_limit": composer.config.global_limit,
                "items_count": len(composer.items)
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
def get_stats():
    """Vraća statistiku memorije."""
    try:
        return Librarian().get_stats()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/entities")
def get_entities(type: Optional[str] = None):
    """Vraća ekstrahirane entitete."""
    import sqlite3
    lib = Librarian()
    conn = sqlite3.connect(lib.meta_path)
    cursor = conn.cursor()
    
    try:
        if type:
            cursor.execute("SELECT file_path, type, content, context_preview FROM entities WHERE type = ?", (type,))
        else:
            cursor.execute("SELECT file_path, type, content, context_preview FROM entities")
        
        rows = cursor.fetchall()
        entities = []
        for row in rows:
            entities.append({
                "file": os.path.basename(row[0]),
                "type": row[1],
                "content": row[2],
                "preview": row[3]
            })
        return {"entities": entities}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

@app.delete("/wipe")
def wipe_memory():
    """Briše svu memoriju."""
    try:
        Librarian().wipe_all()
        return {"status": "success", "message": "Memorija je obrisana."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== DECISION API ====================

class RatifyRequest(BaseModel):
    valid_from: Optional[str] = None
    valid_to: Optional[str] = None
    superseded_by: Optional[str] = None

class SupersedeRequest(BaseModel):
    old_decision_id: int
    new_decision_text: str
    valid_from: Optional[str] = None


@app.get("/decisions")
def get_decisions(
    project: Optional[str] = None,
    include_superseded: bool = False
):
    """
    Vraća sve odluke iz baze podataka.
    
    - **project**: Filtriraj po imenu projekta
    - **include_superseded**: Uključi i zamijenjene odluke (default: False)
    """
    try:
        lib = Librarian()
        decisions = lib.get_decisions(project=project, include_superseded=include_superseded)
        return {"decisions": decisions, "count": len(decisions)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/decisions/active")
def get_active_decisions(
    project: Optional[str] = None,
    date: Optional[str] = None
):
    """
    Vraća odluke aktivne na određeni datum.
    
    - **project**: Filtriraj po imenu projekta
    - **date**: Datum u formatu YYYY-MM-DD (default: danas)
    """
    try:
        lib = Librarian()
        decisions = lib.get_active_decisions(project=project, date=date)
        return {"decisions": decisions, "count": len(decisions), "active_on": date or "today"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/decisions/{decision_id}")
def get_decision(decision_id: int):
    """Vraća određenu odluku po ID-u."""
    try:
        lib = Librarian()
        decision = lib.get_decision_by_id(decision_id)
        if not decision:
            raise HTTPException(status_code=404, detail=f"Odluka s ID-om {decision_id} nije pronađena.")
        return decision
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/decisions/{decision_id}/ratify")
def ratify_decision(decision_id: int, request: RatifyRequest):
    """
    Ratificira odluku - ažurira njene temporalne parametre.
    
    Primjer:
    ```json
    {
        "valid_from": "2026-01-01",
        "valid_to": "2026-12-31"
    }
    ```
    """
    try:
        lib = Librarian()
        success = lib.ratify_decision(
            decision_id,
            valid_from=request.valid_from,
            valid_to=request.valid_to,
            superseded_by=request.superseded_by
        )
        if not success:
            raise HTTPException(status_code=404, detail=f"Odluka s ID-om {decision_id} nije pronađena.")
        
        # Vrati ažuriranu odluku
        updated = lib.get_decision_by_id(decision_id)
        return {"status": "success", "message": "Odluka ratificirana.", "decision": updated}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/decisions/supersede")
def supersede_decision(request: SupersedeRequest):
    """
    Zamjenjuje staru odluku novom.
    
    1. Stara odluka dobiva `valid_to = danas` i `superseded_by = nova odluka`
    2. Kreira se nova odluka s `valid_from = danas` (ili zadani datum)
    
    Primjer:
    ```json
    {
        "old_decision_id": 1,
        "new_decision_text": "Koristit ćemo PostgreSQL umjesto SQLite",
        "valid_from": "2026-02-08"
    }
    ```
    """
    try:
        lib = Librarian()
        new_id = lib.supersede_decision(
            old_decision_id=request.old_decision_id,
            new_decision_text=request.new_decision_text,
            valid_from=request.valid_from
        )
        if new_id is None:
            raise HTTPException(status_code=404, detail=f"Stara odluka s ID-om {request.old_decision_id} nije pronađena.")
        
        new_decision = lib.get_decision_by_id(new_id)
        old_decision = lib.get_decision_by_id(request.old_decision_id)
        
        return {
            "status": "success",
            "message": f"Odluka #{request.old_decision_id} je zamijenjena novom odlukom #{new_id}.",
            "old_decision": old_decision,
            "new_decision": new_decision
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.on_event("startup")
def startup_event():
    """Pokreće watcher u pozadini pri startu servera."""
    import threading
    from src.modules.watcher import Watcher
    
    # Warmup Singleton Oracle
    try:
        get_oracle()
    except Exception as e:
        print(f"❌ Failed to init Oracle: {e}")
    
    def run_watcher():
        watcher = Watcher(path=".") # Prati cijeli projektni root
        watcher.run()
        
    thread = threading.Thread(target=run_watcher, daemon=True)
    thread.start()
    print("🚀 Background Watcher pokrenut na 'docs' folderu.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
