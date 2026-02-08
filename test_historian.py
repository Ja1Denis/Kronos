from src.modules.librarian import Librarian
from src.modules.historian import Historian
from src.modules.oracle import Oracle
import time

def test_historian():
    print("--- Testiranje Historian Modula v2 ---")
    
    librarian = Librarian()
    historian = Historian()
    
    # 1. Pripremi testne podatke
    # Odluka: "Koristimo PostgreSQL za bazu podataka."
    timestamp = int(time.time())
    original_decision = f"Koristimo isključivo PostgreSQL v17 (Build {timestamp})."
    print(f"Spremam odluku: '{original_decision}'")
    
    original_id = librarian.save_entity("decision", original_decision, project="test_proj")
    
    if not original_id:
        print("Upozorenje: Odluka možda već postoji. Nastavljam s postojećom.")
        # Pokušaj naći postojeću
        oracle = Oracle()
        res = oracle.ask(original_decision, project="test_proj", limit=1)
        if res['entities']:
            original_id = res['entities'][0]['id']
        else:
            print("Greška: Ne mogu naći niti spremiti odluku.")
            return

    print(f"ID Odluke: {original_id}")
    
    # Daj ChromaDB vremena da indeksira (iako Librarian to radi odmah u SQLite, Oracle čita iz ChromaDB/SQLite)
    # Zapravo Oracle čita vectors iz ChromaDB. Librarian save_entity sprema u SQLite ali NE nužno u ChromaDB odmah?
    # Librarian.save_entity -> log_event -> ... tko prebacuje u ChromaDB?
    # Aaa, Librarian.save_entity samo sprema u SQLite entities tablicu.
    # Ali Oracle.ask pretražuje vectors. Entities se NE vektoriziraju automatski kod save_entity?
    # Trebam provjeriti Librarian.save_entity.
    
    # Provjera koda Librarian.save_entity:
    # "INSERT INTO entities ..." -> Gotovo.
    # Nema ChromaDB update-a.
    # Oracle.ask radi: embedding -> query ChromaDB -> return chunks.
    # Ali Oracle.ask također radi: search_entities (SQLite LIKE) ili search_fts.
    
    # Oracle.ask implementacija:
    # 1. Generiraj query embedding.
    # 2. Query ChromaDB (za chunkove).
    # 3. Rerank.
    # 4. Search entities (SQL LIKE based on keyword match? Ne, Oracle ima svoju logiku).
    
    # Moram provjeriti src/modules/oracle.py da vidim kako dohvaća entitete.
    # Ako Oracle.ask koristi samo ChromaDB za "chunks", a SQLite za "entities", onda je OK.
    
    # 2. Testiraj kontradikciju
    # Nova tvrdnja: "Prebacujemo se na MongoDB."
    new_claim = "Od sada koristimo MongoDB kao primarnu bazu."
    print(f"\nProvjeravam kontradikciju za: '{new_claim}'")
    
    # DEBUG: Direct Chroma Check
    try:
        debug_client = librarian._get_collection()
        print(f"DEBUG: Chroma count: {debug_client.count()}")
        debug_res = debug_client.get(ids=[f"entity_{original_id}"])
        print(f"DEBUG: Entity in Chroma: {debug_res['ids']}")
        
        # Test query
        q_debug = debug_client.query(query_texts=[new_claim], n_results=5)
        print(f"DEBUG: Query results IDs: {q_debug['ids']}")
    except Exception as e:
        print(f"DEBUG: Error checking Chroma: {e}")

    result = historian.find_contradictions(new_claim, project="test_proj")
    
    print("\nRezultat analize:")
    print(result)
    
    # Očekujemo: conflict found = True, conflicting_id = original_id
    if result.get('contradiction_found'):
        print("\n✅ TEST PROŠAO: Kontradikcija uspješno detektirana!")
    else:
        print("\n❌ TEST PAO: Kontradikcija NIJE detektirana.")

if __name__ == "__main__":
    test_historian()
