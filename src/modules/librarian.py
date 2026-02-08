import os
import sqlite3
import json
import hashlib
from datetime import datetime
from colorama import Fore, Style
import chromadb

class Librarian:
    def __init__(self, data_path="data"):
        self.data_path = data_path
        self.store_path = os.path.join(data_path, "store")  # ChromaDB
        self.meta_path = os.path.join(data_path, "metadata.db") # SQLite
        self.archive_path = os.path.join(data_path, "archive.jsonl") # JSONL

        # Inicijalizacija
        self._init_sqlite()
        # Chroma se inicijalizira lazy (na prvi poziv)

    def _init_sqlite(self):
        """Kreira tablice za praćenje datoteka i FTS pretragu."""
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        
        # 1. Tabela za praćenje promjena datoteka
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                last_modified REAL,
                hash TEXT,
                processed_at TEXT
            )
        ''')

        # 2. Virtualna tabela za Full-Text Search (FTS5)
        # Sadrži originalni tekst i stemiranu verziju za bolju pretragu
        try:
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    path,           -- Putanja do datoteke
                    content,        -- Originalni sadržaj chunka
                    stemmed_content -- Stemirani sadržaj (za keyword search)
                )
            ''')
        except sqlite3.OperationalError:
            print(f"{Fore.YELLOW}⚠️ Upozorenje: Tvoj SQLite možda ne podržava FTS5. Hybrid search neće raditi punim kapacitetom.{Style.RESET_ALL}")

        # 3. Tabela za ekstrahirane entitete
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS entities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_path TEXT,
                type TEXT, -- 'problem', 'solution', 'decision', 'task'
                content TEXT,
                context_preview TEXT,
                created_at TEXT
            )
        ''')
            
        conn.commit()
        conn.close()

    def search_fts(self, query_stemmed, limit=5):
        """
        Izvodi keyword search koristeći FTS5 na stemiranom sadržaju.
        Vraća listu (path, content, rank).
        """
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        
        # FTS5 pretraga po stemiranom sadržaju
        # ORDER BY rank sortira po relevantnosti (BM25 ugrađen u FTS5)
        try:
            cursor.execute('''
                SELECT path, content 
                FROM knowledge_fts 
                WHERE knowledge_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?
            ''', (query_stemmed, limit))
            results = cursor.fetchall()
        except Exception as e:
            print(f"{Fore.RED}Greška pri FTS pretrazi: {e}{Style.RESET_ALL}")
            results = []
            
        conn.close()
        return results

    def store_fts(self, path, content, stemmed_content):
        """Sprema chunk u FTS indeks."""
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO knowledge_fts (path, content, stemmed_content)
                VALUES (?, ?, ?)
            ''', (path, content, stemmed_content))
            conn.commit()
        except Exception as e:
            print(f"{Fore.RED}Greška pri FTS insertu: {e}{Style.RESET_ALL}")
            
        conn.close()

    def delete_fts(self, path):
        """Briše sve FTS unose za danu datoteku."""
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM knowledge_fts WHERE path = ?', (path,))
            conn.commit()
        except Exception as e:
            print(f"{Fore.RED}Greška pri brisanju iz FTS-a: {e}{Style.RESET_ALL}")
        conn.close()

    def store_extracted_data(self, file_path, data):
        """Sprema ekstrahirane podatke u entities tablicu."""
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        
        try:
            # Prvo obriši stare entitete za vaj file
            cursor.execute('DELETE FROM entities WHERE file_path = ?', (file_path,))
            
            timestamp = datetime.now().isoformat()
            
            # Helper za insert
            def insert_entity(etype, content, preview=""):
                cursor.execute('''
                    INSERT INTO entities (file_path, type, content, context_preview, created_at)
                    VALUES (?, ?, ?, ?, ?)
                ''', (file_path, etype, content, preview, timestamp))

            # Spremi probleme
            for item in data.get('problems', []):
                insert_entity('problem', item)
                
            # Spremi rješenja
            for item in data.get('solutions', []):
                insert_entity('solution', item)
                
            # Spremi odluke
            for item in data.get('decisions', []):
                insert_entity('decision', item)
                
            # Spremi zadatke
            for item in data.get('tasks', []):
                status_icon = "✅" if item['status'] == 'done' else "todo"
                insert_entity('task', f"[{status_icon}] {item['content']}")

            # Spremi kodne blokove (samo meta)
            for item in data.get('code_snippets', []):
                insert_entity('code', item['language'], item['preview'])

            conn.commit()
            
        except Exception as e:
            print(f"{Fore.RED}Greška pri spremanju entiteta: {e}{Style.RESET_ALL}")
            
        conn.close()

    def is_file_processed(self, file_path):
        """Provjerava je li datoteka već obrađena i nepromijenjena."""
        if not os.path.exists(file_path):
            return False
            
        current_mtime = os.path.getmtime(file_path)
        
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        cursor.execute('SELECT last_modified FROM files WHERE path = ?', (file_path,))
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0] == current_mtime:
            return True # Već obrađeno i nije mijenjano
        return False

    def mark_as_processed(self, file_path):
        """Zabilježi da je datoteka obrađena."""
        current_mtime = os.path.getmtime(file_path)
        # Izračunaj hash sadržaja za dodatnu sigurnost (opcionalno)
        
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO files (path, last_modified, processed_at)
            VALUES (?, ?, ?)
        ''', (file_path, current_mtime, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def store_archive(self, chunks, file_metadata):
        """Sprema chunkove u JSONL arhivu (append mode)."""
        try:
            with open(self.archive_path, 'a', encoding='utf-8') as f:
                for chunk in chunks:
                    record = {
                        "content": chunk,
                        "metadata": file_metadata,
                        "timestamp": datetime.now().isoformat()
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            print(f"{Fore.BLUE}💾 Arhivirano {len(chunks)} chunkova u JSONL.{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.RED}❌ Greška pri arhiviranju: {e}{Style.RESET_ALL}")

    def get_chroma_client(self):
        """Vraća klijenta za vektorsku bazu."""
        return chromadb.PersistentClient(path=self.store_path)

    def get_stats(self):
        """Dohvaća statistiku baze podataka."""
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        
        stats = {}
        try:
            cursor.execute("SELECT count(*) FROM files")
            stats['total_files'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT count(*) FROM knowledge_fts")
            stats['total_chunks'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT type, count(*) FROM entities GROUP BY type")
            stats['entities'] = dict(cursor.fetchall())
            
            # DB size
            if os.path.exists(self.meta_path):
                stats['db_size_kb'] = os.path.getsize(self.meta_path) / 1024
            else:
                stats['db_size_kb'] = 0
                
            # ChromaDB size (procjena)
            if os.path.exists(self.store_path):
                total_size = 0
                for dirpath, dirnames, filenames in os.walk(self.store_path):
                    for f in filenames:
                        fp = os.path.join(dirpath, f)
                        total_size += os.path.getsize(fp)
                stats['chroma_size_kb'] = total_size / 1024
            else:
                stats['chroma_size_kb'] = 0
                
        except Exception as e:
            print(f"Greška pri dohvaćanju statistike: {e}")
            
        conn.close()
        return stats

    def wipe_all(self):
        """Briše sve lokalne podatke."""
        # 1. Obriši SQLite podatke
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM files")
            cursor.execute("DELETE FROM knowledge_fts")
            cursor.execute("DELETE FROM entities")
            conn.commit()
        except Exception as e:
            print(f"Greška pri brisanju SQLite podataka: {e}")
        finally:
            conn.close()
        
        # 2. Obriši JSONL
        if os.path.exists(self.archive_path):
            try:
                os.remove(self.archive_path)
            except Exception as e:
                print(f"Greška pri brisanju arhive: {e}")
            
        # 3. ChromaDB se briše tako da pobrišemo direktorij store
        # NAPOMENA: Ovo može raditi probleme ako je Oracle objekt aktivan
        import shutil
        if os.path.exists(self.store_path):
            try:
                shutil.rmtree(self.store_path)
            except Exception as e:
                print(f"Greška pri brisanju ChromaDB pohrane: {e}")
