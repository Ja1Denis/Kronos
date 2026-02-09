from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import sys

from src.modules.ingestor import Ingestor
from src.modules.oracle import Oracle
from src.modules.librarian import Librarian

app = FastAPI(title="Kronos API", description="Semantička Memorija za AI Agente", version="0.2.0")

# Model upita
class QueryRequest(BaseModel):
    text: str
    limit: Optional[int] = 5

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

@app.post("/query")
def query_memory(request: QueryRequest):
    """Pretražuje semantičku memoriju."""
    try:
        oracle = Oracle()
        results = oracle.ask(request.text, limit=request.limit, silent=True)
        return {
            "query": request.text,
            "results": results
        }
    except Exception as e:
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
    
    def run_watcher():
        watcher = Watcher(path=".") # Prati cijeli projektni root
        watcher.run()
        
    thread = threading.Thread(target=run_watcher, daemon=True)
    thread.start()
    print("🚀 Background Watcher pokrenut na 'docs' folderu.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
