import sqlite3
from src.modules.librarian import Librarian
from rich.console import Console
from rich.progress import track

console = Console()

def reindex_entities():
    """
    Učitava sve entitete iz SQLite baze i šalje ih u ChromaDB (vektorsku bazu).
    Ovo je potrebno jer smo upravo dodali 'Entity-First' pretragu, a stari entiteti
    nisu bili automatski vektorizirani.
    """
    librarian = Librarian()
    
    console.print("[bold cyan]🔄 Re-indeksiranje entiteta: SQLite -> ChromaDB[/]")
    
    # 1. Dohvati sve entitete
    conn = sqlite3.connect(librarian.meta_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, content, project, file_path FROM entities")
    rows = cursor.fetchall()
    conn.close()
    
    total = len(rows)
    console.print(f"Pronađeno [bold]{total}[/] entiteta u bazi.")
    
    # 2. Inicijaliziraj Chroma klijenta
    collection = librarian._get_collection()
    
    # 3. Batch processing
    success_count = 0
    
    for row in track(rows, description="Indeksiranje..."):
        eid, etype, content, project, file_path = row
        
        # Ignoriraj 'code' jer to nisu semantički entiteti za pretragu
        if etype == 'code':
            continue
            
        try:
            # Koristimo internu metodu za indeksiranje
            librarian._index_entity(eid, etype, content, project=project, source=file_path)
            success_count += 1
        except Exception as e:
            console.print(f"[red]Greška na ID {eid}: {e}[/]")
            
    console.print(f"\n[bold green]✅ Završeno! Uspješno indeksirano {success_count}/{total} entiteta.[/]")
    console.print("[dim]Sada 'audit' i 'chat' mogu pronaći sve stare odluke.[/]")

if __name__ == "__main__":
    reindex_entities()
