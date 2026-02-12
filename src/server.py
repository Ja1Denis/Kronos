from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import sys
import time

from sse_starlette.sse import EventSourceResponse
from src.modules.ingestor import Ingestor
from src.modules.oracle import Oracle
from src.modules.librarian import Librarian
from src.modules.notification_manager import notification_manager

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

class FetchExactRequest(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    content_hash: Optional[str] = None
    context_keys: Optional[List[str]] = None

class IngestRequest(BaseModel):
    path: str
    recursive: Optional[bool] = False

@app.get("/")
def read_root():
    return {"name": "Kronos API", "status": "online", "version": "0.2.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}

@app.get("/stream")
async def stream_notifications():
    """SSE endpoint za real-time notifikacije."""
    return EventSourceResponse(notification_manager.subscribe())

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
        start_time = time.time()
        retrieval_results = oracle.ask(request.text, limit=current_limit, silent=True)
        end_time = time.time()
        total_latency = (end_time - start_time) * 1000 # ms
             
        
        # Audit Log (Server Side)
        method = retrieval_results.get("method", "StandardHybrid")
        print(f"[{request.mode}] Query: '{request.text}' | Latency: {total_latency:.2f}ms | Method: {method}")
        
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
            "type": retrieval_results.get("type", "unknown"),
            "pointers": retrieval_results.get("pointers", []),
            "chunks": retrieval_results.get("chunks", []),
            "message": retrieval_results.get("message", ""),
            "total_found": retrieval_results.get("total_found", 0),
            "audit": audit_log,
            "parsed_trace": bool(request.stack_trace),
            "stats": {
                "used_tokens": composer.current_tokens,
                "global_limit": composer.config.global_limit,
                "items_count": len(composer.items),
                "used_latency_ms": round(total_latency, 2),
                "search_method": method
            }
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/fetch_exact")
def fetch_exact(request: FetchExactRequest):
    """
    Kritično: Čita točan raspon linija iz datoteke uz sigurne provjere.
    """
    from src.utils.file_helper import read_file_safe, verify_content_hash
    
    # 1. Čitanje datoteke
    result = read_file_safe(request.file_path, request.start_line, request.end_line)
    
    if "error" in result:
        # Pretvori naše internal errore u FastAPI exceptions
        status_code = 400
        if result["error"] in ["permission_denied", "invalid_path"]: status_code = 403
        if result["error"] == "file_not_found": status_code = 404
        
        raise HTTPException(status_code=status_code, detail=result["message"])
    
    content = result["content"]
    warning = None
    
    # 2. Hash Verifikacija (Graceful Degradation)
    if request.content_hash:
        is_fresh, msg = verify_content_hash(content, request.content_hash)
        if not is_fresh:
            warning = "stale_pointer"
            
    return {
        "content": content,
        "file": request.file_path,
        "range": [request.start_line, request.end_line],
        "warning": warning,
        "status": "success"
    }

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

# ==================== JOB QUEUE API ====================

from src.modules.job_manager import JobManager

class JobSubmitRequest(BaseModel):
    type: str
    params: Dict[str, Any]
    priority: Optional[int] = 5

@app.post("/jobs")
def submit_job(request: JobSubmitRequest):
    """
    Kreira novi asinkroni posao (npr. 'ingest', 'prune').
    """
    try:
        manager = JobManager()
        job_id = manager.submit_job(request.type, request.params, request.priority)
        return {"id": job_id, "status": "pending"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    """
    Provjerava status posla.
    """
    try:
        manager = JobManager()
        job = manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/jobs/{job_id}")
def cancel_job(job_id: str):
    """
    Otkazuje posao ako je još u 'pending' ili 'running' stanju.
    """
    try:
        manager = JobManager()
        success = manager.cancel_job(job_id)
        if not success:
            raise HTTPException(status_code=404, detail="Job not found or cannot be cancelled")
        return {"status": "cancelled"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from src.modules.worker import Worker

# Global Worker Instance
_worker_instance = None

@app.on_event("startup")
def startup_event():
    """Pokreće pozadinske servise (Watcher, Worker)."""
    global _worker_instance
    import threading
    from src.modules.watcher import Watcher
    
    # 1. Warmup Singleton Oracle
    try:
        get_oracle()
    except Exception as e:
        print(f"❌ Failed to init Oracle: {e}")
    
    # 2. Start Watcher (Daemon Thread)
    def run_watcher():
        watcher = Watcher(path=".") # Prati cijeli projektni root
        watcher.run()
        
    watcher_thread = threading.Thread(target=run_watcher, daemon=True, name="KronosWatcher")
    watcher_thread.start()
    print("🚀 Background Watcher pokrenut na '.' folderu.")

    # 3. Start Job Worker (Daemon Thread)
    # Worker runs in its own thread loop and handles jobs from SQLite queue
    try:
        _worker_instance = Worker(poll_interval=2.0)
        _worker_instance.start()
        print("🚀 Background Job Worker pokrenut.")
    except Exception as e:
        print(f"❌ Failed to start Worker: {e}")

@app.on_event("shutdown")
def shutdown_event():
    """Graceful shutdown za servise."""
    global _worker_instance
    if _worker_instance:
        print("🛑 Zaustavljam Worker...")
        _worker_instance.stop()

def kill_port_8000():
    """Kill any process using port 8000 (Windows) balance)."""
    import subprocess
    try:
        # Pronađi PID na portu 8000
        result = subprocess.run(
            ['netstat', '-ano'],
            capture_output=True,
            text=True,
            shell=True
        )
        
        found = False
        for line in result.stdout.split('\n'):
            if ':8000' in line and 'LISTENING' in line:
                # Extract PID (zadnji broj u liniji)
                pid = line.strip().split()[-1]
                print(f"🔫 Killing process {pid} on port 8000")
                subprocess.run(['taskkill', '/F', '/PID', pid], 
                             capture_output=True, shell=True)
                found = True
        
        if found:
            print("✅ Port 8000 cleared")
            time.sleep(1) # Mali delay da OS oslobodi socket
        
    except Exception as e:
        print(f"⚠️ Could not clear port: {e}")

if __name__ == "__main__":
    import uvicorn
    # 1. Prvo oslobodi port ako je zauzet
    kill_port_8000()
    # 2. Pokreni server (Workers=1 to avoid multiple instances of Singletons)
    uvicorn.run(app, host="127.0.0.1", port=8000, workers=1)
