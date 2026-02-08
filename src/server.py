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

@app.on_event("startup")
def startup_event():
    """Pokreće watcher u pozadini pri startu servera."""
    import threading
    from src.modules.watcher import Watcher
    
    def run_watcher():
        watcher = Watcher(path="docs") # Defaultno prati docs folder
        watcher.run()
        
    thread = threading.Thread(target=run_watcher, daemon=True)
    thread.start()
    print("🚀 Background Watcher pokrenut na 'docs' folderu.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
