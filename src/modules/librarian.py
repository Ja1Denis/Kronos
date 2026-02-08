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
                project TEXT,
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
                    project,        -- Ime projekta
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
                project TEXT,
                type TEXT, -- 'problem', 'solution', 'decision', 'task'
                content TEXT,
                context_preview TEXT,
                valid_from TEXT,
                valid_to TEXT,
                superseded_by TEXT,
                created_at TEXT
            )
        ''')
        
        # PROVJERA: Ako tablice postoje ali nemaju nove stupce, dodaj ih (migracija)
        try:
            cursor.execute("ALTER TABLE files ADD COLUMN project TEXT")
        except sqlite3.OperationalError:
            pass
            
        try:
            cursor.execute("ALTER TABLE entities ADD COLUMN project TEXT")
        except sqlite3.OperationalError:
            pass

        # Migracija za temporalne stupce
        for col in ['valid_from', 'valid_to', 'superseded_by']:
            try:
                cursor.execute(f"ALTER TABLE entities ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass
            
        conn.commit()
        conn.close()

    def search_fts(self, query_stemmed, project=None, limit=5):
        """
        Izvodi keyword search koristeći FTS5 na stemiranom sadržaju.
        Vraća listu (path, content, rank).
        """
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        
        try:
            if project:
                cursor.execute('''
                    SELECT path, content 
                    FROM knowledge_fts 
                    WHERE knowledge_fts MATCH ? AND project = ?
                    ORDER BY rank 
                    LIMIT ?
                ''', (query_stemmed, project, limit))
            else:
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

    def store_fts(self, path, content, stemmed_content, project=None):
        """Sprema chunk u FTS indeks."""
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO knowledge_fts (path, content, stemmed_content, project)
                VALUES (?, ?, ?, ?)
            ''', (path, content, stemmed_content, project))
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

    def store_extracted_data(self, file_path, data, project=None):
        """Sprema ekstrahirane podatke u entities tablicu."""
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        
        try:
            # Prvo obriši stare entitete za ovaj file
            cursor.execute('DELETE FROM entities WHERE file_path = ?', (file_path,))
            
            timestamp = datetime.now().isoformat()
            
            # Helper za insert
            def insert_entity(etype, content, preview=""):
                cursor.execute('''
                    INSERT INTO entities (file_path, project, type, content, context_preview, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (file_path, project, etype, content, preview, timestamp))

            # Spremi probleme
            for item in data.get('problems', []):
                insert_entity('problem', item)
                
            # Spremi rješenja
            for item in data.get('solutions', []):
                insert_entity('solution', item)
                
            # Spremi odluke
            for item in data.get('decisions', []):
                # Provjera je li item string ili dict (kompatibilnost)
                if isinstance(item, dict):
                    content = item.get('content', '')
                    v_from = item.get('valid_from')
                    v_to = item.get('valid_to')
                    sup_by = item.get('superseded_by')
                    
                    cursor.execute('''
                        INSERT INTO entities (file_path, project, type, content, valid_from, valid_to, superseded_by, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (file_path, project, 'decision', content, v_from, v_to, sup_by, timestamp))
                else:
                    # Stari format (samo string)
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

    def mark_as_processed(self, file_path, project=None):
        """Zabilježi da je datoteka obrađena."""
        current_mtime = os.path.getmtime(file_path)
        
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO files (path, project, last_modified, processed_at)
            VALUES (?, ?, ?, ?)
        ''', (file_path, project, current_mtime, datetime.now().isoformat()))
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

    def get_active_decisions(self, project=None, date=None):
        """
        Vraća sve odluke aktivne na dani datum.
        Ako datum nije zadan, koristi se današnji.
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()

        query = '''
            SELECT id, content, valid_from, valid_to, superseded_by, file_path, project
            FROM entities
            WHERE type = 'decision'
            AND (valid_from IS NULL OR valid_from <= ?)
            AND (valid_to IS NULL OR valid_to >= ?)
        '''
        params = [date, date]

        if project:
            query += " AND project = ?"
            params.append(project)

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "content": r[1],
                "valid_from": r[2],
                "valid_to": r[3],
                "superseded_by": r[4],
                "file_path": r[5],
                "project": r[6]
            }
            for r in results
        ]

    def get_decisions(self, project=None, include_superseded=False):
        """
        Vraća sve odluke iz baze podataka.
        
        Args:
            project: Opcionalno filtriranje po projektu
            include_superseded: Ako True, uključuje i zamijenjene odluke
        """
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()

        query = '''
            SELECT id, content, valid_from, valid_to, superseded_by, file_path, project, created_at
            FROM entities
            WHERE type = 'decision'
        '''
        params = []

        if not include_superseded:
            query += " AND (superseded_by IS NULL OR superseded_by = '')"

        if project:
            query += " AND project = ?"
            params.append(project)

        query += " ORDER BY created_at DESC"

        cursor.execute(query, tuple(params))
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "content": r[1],
                "valid_from": r[2],
                "valid_to": r[3],
                "superseded_by": r[4],
                "file_path": r[5],
                "project": r[6],
                "created_at": r[7]
            }
            for r in results
        ]

    def get_decision_by_id(self, decision_id):
        """Vraća određenu odluku po ID-u."""
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT id, content, valid_from, valid_to, superseded_by, file_path, project, created_at
            FROM entities
            WHERE id = ? AND type = 'decision'
        ''', (decision_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return None
            
        return {
            "id": result[0],
            "content": result[1],
            "valid_from": result[2],
            "valid_to": result[3],
            "superseded_by": result[4],
            "file_path": result[5],
            "project": result[6],
            "created_at": result[7]
        }

    def ratify_decision(self, decision_id, valid_from=None, valid_to=None, superseded_by=None):
        """
        Ratificira odluku - ažurira njene temporalne parametre.
        
        Args:
            decision_id: ID odluke za ažuriranje
            valid_from: Datum od kada odluka vrijedi (YYYY-MM-DD)
            valid_to: Datum do kada odluka vrijedi (YYYY-MM-DD)
            superseded_by: Tekst ili ID odluke koja zamjenjuje ovu
        
        Returns:
            True ako je ažuriranje uspjelo, False inače
        """
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()

        # Prvo provjeri postoji li odluka
        cursor.execute("SELECT id FROM entities WHERE id = ? AND type = 'decision'", (decision_id,))
        if not cursor.fetchone():
            conn.close()
            return False

        # Izgradi UPDATE upit dinamički
        updates = []
        params = []
        
        if valid_from is not None:
            updates.append("valid_from = ?")
            params.append(valid_from)
        if valid_to is not None:
            updates.append("valid_to = ?")
            params.append(valid_to)
        if superseded_by is not None:
            updates.append("superseded_by = ?")
            params.append(superseded_by)

        if not updates:
            conn.close()
            return True  # Ništa za ažurirati

        params.append(decision_id)
        query = f"UPDATE entities SET {', '.join(updates)} WHERE id = ?"
        
        cursor.execute(query, tuple(params))
        conn.commit()
        conn.close()
        
        return True

    def supersede_decision(self, old_decision_id, new_decision_text, valid_from=None):
        """
        Zamjenjuje staru odluku novom.
        
        1. Označava staru odluku kao zamijenjenu (valid_to = danas, superseded_by = nova odluka)
        2. Kreira novu odluku (valid_from = danas ili zadani datum)
        
        Args:
            old_decision_id: ID stare odluke
            new_decision_text: Tekst nove odluke
            valid_from: Datum od kada nova odluka vrijedi (default: danas)
        
        Returns:
            ID nove odluke ako uspješno, None inače
        """
        today = datetime.now().strftime("%Y-%m-%d")
        if valid_from is None:
            valid_from = today

        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()

        # Dohvati staru odluku
        cursor.execute("""
            SELECT file_path, project FROM entities 
            WHERE id = ? AND type = 'decision'
        """, (old_decision_id,))
        old = cursor.fetchone()
        
        if not old:
            conn.close()
            return None

        old_file_path, old_project = old

        # Kreiraj novu odluku
        timestamp = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO entities (file_path, project, type, content, valid_from, created_at)
            VALUES (?, ?, 'decision', ?, ?, ?)
        ''', (old_file_path, old_project, new_decision_text, valid_from, timestamp))
        
        new_id = cursor.lastrowid

        # Ažuriraj staru odluku
        cursor.execute('''
            UPDATE entities 
            SET valid_to = ?, superseded_by = ?
            WHERE id = ?
        ''', (today, f"Decision #{new_id}: {new_decision_text[:50]}", old_decision_id))

        conn.commit()
        conn.close()
        
        return new_id
