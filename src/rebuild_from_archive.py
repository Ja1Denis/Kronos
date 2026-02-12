import json
import os
import sys
import sqlite3
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from src.modules.librarian import Librarian
from src.modules.oracle import Oracle
from src.utils.stemmer import stem_text

console = Console()

def rebuild():
    lib = Librarian()
    oracle = Oracle()
    
    archive_path = os.path.join("data", "archive.jsonl")
    if not os.path.exists(archive_path):
        console.print(f"[bold red]❌ Arhiva ne postoji na: {archive_path}[/]")
        return

    console.print("[bold cyan]🔄 Započinjem rekonstrukciju baze iz arhive...[/]")
    
    # 1. Resetiraj baze (ali sačuvaj arhivu)
    lib.wipe_all(keep_archive=True)
    console.print("[dim]💨 Baza resetirana (metadata.db & vector store).[/]")

    # 2. Brojanje linija za progress bar
    total_lines = 0
    with open(archive_path, 'r', encoding='utf-8') as f:
        for _ in f:
            total_lines += 1

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        
        task = progress.add_task("[cyan]Replay events...", total=total_lines)
        
        legacy_batch = []
        batch_size = 50
        
        with open(archive_path, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    
                    if "event" in record:
                        # Prije procesiranja eventa, isprazni legacy batch
                        if legacy_batch:
                            _replay_legacy_batch(lib, oracle, legacy_batch)
                            legacy_batch = []
                            
                        event_type = record["event"]
                        data = record["data"]
                        
                        if event_type == "file_processed":
                            _replay_file_processed(lib, oracle, data)
                        elif event_type == "decision_ratified":
                            lib.ratify_decision(data["decision_id"], **data["updates"])
                    else:
                        # STARI FORMAT (Legacy) - Dodaj u batch
                        legacy_batch.append(record)
                        if len(legacy_batch) >= batch_size:
                            _replay_legacy_batch(lib, oracle, legacy_batch)
                            legacy_batch = []
                except Exception as e:
                    console.print(f"[red]Greška u liniji: {e}[/]")
                
                progress.advance(task)
        
        # Zadnji batch
        if legacy_batch:
            _replay_legacy_batch(lib, oracle, legacy_batch)

    console.print(f"\n[bold success]✅ Rekonstrukcija završena![/]")
    # Prikaži statse
    stats = lib.get_stats()
    console.print(f"Indeksirano datoteka: {stats.get('total_files')}")
    console.print(f"Ukupno chunkova: {stats.get('total_chunks')}")

def _replay_file_processed(lib, oracle, data):
    chunks = data["chunks"]
    meta = data["metadata"]
    entities = data.get("entities")
    file_path = meta["source"]
    project = meta.get("project", "default")

    # FTS
    for chunk in chunks:
        stemmed = stem_text(chunk, mode="aggressive")
        lib.store_fts(file_path, chunk, stemmed, project=project)

    # Entiteti
    if entities:
        lib.store_extracted_data(file_path, entities, project=project)

    # Vektori
    ids = [f"{os.path.basename(file_path)}_{i}_{hash(chunk)}" for i in range(len(chunks))]
    oracle.safe_upsert(
        documents=chunks,
        metadatas=[meta for _ in chunks],
        ids=ids
    )
    
    # Mark as processed (pokušavamo simulirati mtime ako možemo, inače 0)
    # U replayu mtime nije toliko bitan jer želimo samo napuniti bazu
    lib.mark_as_processed(file_path, project=project)

def _replay_legacy_batch(lib, oracle, records):
    docs = []
    metas = []
    ids = []
    
    conn = sqlite3.connect(lib.meta_path)
    cursor = conn.cursor()
    
    seen_batch_ids = set()
    
    try:
        for record in records:
            content = record["content"]
            meta = record["metadata"]
            file_path = meta["source"]
            project = meta.get("project", "default")
            doc_id = f"{os.path.basename(file_path)}_{hash(content)}"
            
            # FTS (Directly using cursor for speed)
            stemmed = stem_text(content, mode="aggressive")
            cursor.execute('''
                INSERT INTO knowledge_fts (path, content, stemmed_content, project)
                VALUES (?, ?, ?, ?)
            ''', (file_path, content, stemmed, project))
            
            # Mark processed
            cursor.execute('''
                INSERT OR REPLACE INTO files (path, project, last_modified, processed_at)
                VALUES (?, ?, ?, ?)
            ''', (file_path, project, 0, datetime.now().isoformat()))
            
            # Collect for Chroma (if not duplicate in this batch)
            if doc_id not in seen_batch_ids:
                docs.append(content)
                metas.append(meta)
                ids.append(doc_id)
                seen_batch_ids.add(doc_id)
        
        conn.commit()
    except Exception as e:
        print(f"Error in batch: {e}")
        conn.rollback()
    finally:
        conn.close()

    # Batch upsert to Chroma
    oracle.safe_upsert(
        documents=docs,
        metadatas=metas,
        ids=ids
    )

if __name__ == "__main__":
    rebuild()
