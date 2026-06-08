import os
import sqlite3
import json
import hashlib
from datetime import datetime
from colorama import Fore, Style
from src.utils.logger import logger
import chromadb
from src.utils.metadata_helper import validate_metadata, enrich_metadata

class Librarian:
    def __init__(self, data_path="data"):
        # Ako je proslijeđen default "data", pokušaj ga naći relativno u odnosu na projekt
        if data_path == "data":
            # Librarian je u src/modules/librarian.py
            curr_dir = os.path.dirname(os.path.abspath(__file__)) # src/modules
            src_dir = os.path.dirname(curr_dir) # src
            root_dir = os.path.dirname(src_dir) # kronos
            self.data_path = os.path.join(root_dir, "data")
        else:
            self.data_path = data_path
            
        self.store_path = os.path.join(self.data_path, "store")  # ChromaDB (legacy)
        self.meta_path = os.path.join(self.data_path, "metadata.db") # SQLite
        self.archive_path = os.path.join(self.data_path, "archive.jsonl") # JSONL

        # Učitaj varijable za Gemini embeddings
        from dotenv import load_dotenv
        curr_dir = os.path.dirname(os.path.abspath(__file__))
        src_dir = os.path.dirname(curr_dir)
        root_dir = os.path.dirname(src_dir)
        workspace_root = os.path.dirname(root_dir)
        load_dotenv(os.path.join(workspace_root, '.agent', '.env'))
        
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.embedding_function = None
        if self.api_key:
            try:
                from chromadb.utils import embedding_functions
                self.embedding_function = embedding_functions.GoogleGenerativeAiEmbeddingFunction(
                    api_key=self.api_key,
                    model_name="models/gemini-embedding-001"
                )
            except Exception as e:
                logger.warning(f"⚠️ Librarian: Could not init Gemini embeddings: {e}")

        # Inicijalizacija
        self._init_sqlite()
        
    def _get_sqlite_conn(self):
        """Vraća SQLite konekciju s WAL modom, timeoutom i učitanom sqlite-vec ekstenzijom."""
        import sqlite_vec
        conn = sqlite3.connect(self.meta_path, timeout=30)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except:
            pass
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
        except Exception as e:
            logger.warning(f"⚠️ Librarian: Failed to load sqlite-vec: {e}")
        return conn

    def _index_entity(self, eid, etype, content, project=None, source=None):
        """Indeksira entitet u SQLite (sqlite-vec) za semantičku pretragu."""
        if not content or not content.strip():
            return
            
        try:
            meta = {
                "source": source or "manual",
                "project": project or "default",
                "type": "entity",
                "entity_type": etype,
                "entity_id": eid,
                "created_at": datetime.now().isoformat()
            }
            
            if not validate_metadata(meta):
                print(f"{Fore.RED}ERROR: Metadata Validation Failed for entity_{eid}. Skipping.{Style.RESET_ALL}")
                return
                
            # Enrich metadata
            final_meta = enrich_metadata(content, meta)
            
            # Generiranje embeddinga
            if not self.embedding_function:
                logger.warning("⚠️ No embedding function available for entity indexing!")
                return
                
            embeddings = self.embedding_function([content])
            if not embeddings:
                logger.warning("⚠️ Failed to generate embedding for entity!")
                return
            embedding = embeddings[0]
            
            # Spremanje u SQLite tablice
            import sqlite_vec
            conn = self._get_sqlite_conn()
            cursor = conn.cursor()
            try:
                # 1. Spasi u vec_metadata
                cursor.execute('''
                    INSERT OR REPLACE INTO vec_metadata (custom_id, document, metadata_json, project)
                    VALUES (?, ?, ?, ?)
                ''', (f"entity_{eid}", content, json.dumps(final_meta), project or "default"))
                
                rowid = cursor.lastrowid
                
                # 2. Spasi u vec_items
                cursor.execute('''
                    INSERT OR REPLACE INTO vec_items (rowid, embedding)
                    VALUES (?, ?)
                ''', (rowid, sqlite_vec.serialize_float32(embedding)))
                conn.commit()
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
        except Exception as e:
            print(f"{Fore.RED}Greška pri indeksiranju entiteta #{eid}: {e}{Style.RESET_ALL}")

    def _delete_entities_from_chroma(self, source_path):
        """Briše sve entitete vezane uz datoteku iz SQLite i sqlite-vec."""
        try:
            conn = self._get_sqlite_conn()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    SELECT rowid FROM vec_metadata 
                    WHERE json_extract(metadata_json, '$.source') = ? 
                      AND json_extract(metadata_json, '$.type') = 'entity'
                ''', (source_path,))
                rowids = [r[0] for r in cursor.fetchall()]
                if rowids:
                    placeholders = ','.join('?' for _ in rowids)
                    cursor.execute(f"DELETE FROM vec_items WHERE rowid IN ({placeholders})", rowids)
                    cursor.execute(f"DELETE FROM vec_metadata WHERE rowid IN ({placeholders})", rowids)
                    conn.commit()
            except Exception as e:
                conn.rollback()
                logger.error(f"Error deleting entities: {e}")
            finally:
                conn.close()
        except Exception as e:
            pass


    def _init_sqlite(self):
        """Kreira tablice za praćenje datoteka i FTS pretragu."""
        conn = self._get_sqlite_conn()
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
            # Provjera postoje li stupci start_line/end_line
            cursor.execute("PRAGMA table_info(knowledge_fts)")
            cols = [c[1] for c in cursor.fetchall()]
            
            if cols and "start_line" not in cols:
                logger.info("INFO: Migracija: Nadogradnja FTS tablice (start_line, end_line)...")
                cursor.execute("DROP TABLE knowledge_fts")
            
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                    path,           -- Putanja do datoteke
                    project,        -- Ime projekta
                    content,        -- Originalni sadržaj chunka
                    stemmed_content, -- Stemirani sadržaj (za keyword search)
                    start_line UNINDEXED,
                    end_line UNINDEXED
                )
            ''')
        except sqlite3.OperationalError:
            print(f"{Fore.YELLOW}WARNING: Tvoj SQLite mozda ne podrzava FTS5. Hybrid search nece raditi punim kapacitetom.{Style.RESET_ALL}")

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

        # 4. Tabela za metapodatke vektora
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vec_metadata (
                rowid INTEGER PRIMARY KEY AUTOINCREMENT,
                custom_id TEXT UNIQUE,
                document TEXT,
                metadata_json TEXT,
                project TEXT
            )
        ''')

        # 5. Virtualna tabela za sqlite-vec pretragu (dimenzija 3072 za Gemini-embedding-001)
        try:
            cursor.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_items USING vec0(
                    rowid INTEGER PRIMARY KEY,
                    embedding float[3072]
                )
            ''')
        except sqlite3.OperationalError as e:
            logger.warning(f"⚠️ Librarian: Failed to create vec_items virtual table: {e}")
            
        conn.commit()
        conn.close()

    def search_entities(self, query, etype=None, project=None, limit=5):
        """Pretražuje ekstrahirane entitete po sadržaju."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        sql = "SELECT id, file_path, project, type, content, created_at FROM entities WHERE content LIKE ?"
        params = [f"%{query}%"]
        
        if etype:
            sql += " AND type = ?"
            params.append(etype)
        
        if project:
            sql += " AND project = ?"
            params.append(project)
            
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        
        cursor.execute(sql, tuple(params))
        results = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "file_path": r[1],
                "project": r[2],
                "type": r[3],
                "content": r[4],
                "created_at": r[5]
            }
            for r in results
        ]

    def _escape_fts_token(self, token: str) -> str:
        """
        Escapes special characters for FTS5 queries to prevent syntax errors.
        """
        if not token: return ""
        # Remove quotes
        token = token.replace('"', '')
        # Handle trailing minus or stand-alone minus (not allowed as suffix)
        if token.endswith('-') or token == '-':
            token = token.replace('-', '')
        
        # If it contains special characters, wrap it in double quotes for FTS
        # FTS5 characters: + * : ^ " ( )
        special = set('+*:^"()')
        if any(c in special for c in token) or '-' in token:
            return f'"{token}"'
        return token

    def search_fts(self, query_stemmed, project=None, limit=5, mode="and"):
        """
        Hybrid FTS search.
        modes:
          - "phrase": exact sequence match (old behavior)
          - "and": all tokens must be present in any order (default)
          - "or": any token can be present
        """
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        tokens = [self._escape_fts_token(t) for t in query_stemmed.split() if t.strip()]
        if not tokens:
            conn.close()
            return []

        if mode == "phrase":
            fts_logic = f'"{query_stemmed}"'
        elif mode == "or":
            fts_logic = ' OR '.join(tokens)
        else: # "and" is default
            fts_logic = ' AND '.join(tokens)

        try:
            if project:
                fts_query = f'project:"{project}" AND stemmed_content:({fts_logic})'
            else:
                fts_query = f'stemmed_content:({fts_logic})'
            
            # DEBUG
            from src.utils.logger import logger
            logger.info(f"[LIBRARIAN DEBUG] FTS Query: {fts_query}")

            cursor.execute('''
                SELECT path, content, start_line, end_line 
                FROM knowledge_fts 
                WHERE knowledge_fts MATCH ? 
                ORDER BY rank 
                LIMIT ?
            ''', (fts_query, limit))
                
            results = cursor.fetchall()
            logger.info(f"[LIBRARIAN DEBUG] Results: {len(results)}")
            
            # Fallsafe: If AND returns 0 and we aren't in OR mode, try OR fallback
            if not results and mode == "and":
                conn.close()
                return self.search_fts(query_stemmed, project=project, limit=limit, mode="or")

        except Exception as e:
            from src.utils.metrics import metrics
            metrics.log_failure("fts")
            print(f"{Fore.RED}Greška pri FTS pretrazi [mode={mode}]: {e}{Style.RESET_ALL}")
            results = []
            
        conn.close()
        return results

    def store_fts(self, path, content, stemmed_content, project=None, start_line=1, end_line=1):
        """Sprema chunk u FTS indeks."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO knowledge_fts (path, content, stemmed_content, project, start_line, end_line)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (path, content, stemmed_content, project, start_line, end_line))
            conn.commit()
        except Exception as e:
            print(f"{Fore.RED}Greška pri FTS insertu: {e}{Style.RESET_ALL}")
            
        conn.close()

    def delete_fts(self, path):
        """Briše sve FTS unose za danu datoteku."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute('DELETE FROM knowledge_fts WHERE path = ?', (path,))
            conn.commit()
        except Exception as e:
            print(f"{Fore.RED}Greška pri brisanju iz FTS-a: {e}{Style.RESET_ALL}")
        conn.close()

    def store_extracted_data(self, file_path, data, project=None):
        """Sprema ekstrahirane podatke u entities tablicu."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        try:
            # Prvo obriši stare entitete za ovaj file (SQLite + Chroma)
            cursor.execute('DELETE FROM entities WHERE file_path = ?', (file_path,))
            self._delete_entities_from_chroma(file_path) # <--- NOVO
            
            timestamp = datetime.now().isoformat()
            
            # Helper za insert
            def insert_entity(etype, content, preview="", meta_extra=None):
                # 1. SQLite
                v_from = meta_extra.get('valid_from') if meta_extra else None
                v_to = meta_extra.get('valid_to') if meta_extra else None
                sup_by = meta_extra.get('superseded_by') if meta_extra else None
                
                cursor.execute('''
                    INSERT INTO entities (file_path, project, type, content, context_preview, valid_from, valid_to, superseded_by, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (file_path, project, etype, content, preview, v_from, v_to, sup_by, timestamp))
                
                # 2. ChromaDB
                new_id = cursor.lastrowid
                self._index_entity(new_id, etype, content, project, source=file_path)

            # Spremi probleme
            for item in data.get('problems', []):
                insert_entity('problem', item)
                
            # Spremi rješenja
            for item in data.get('solutions', []):
                insert_entity('solution', item)
                
            # Spremi odluke
            for item in data.get('decisions', []):
                if isinstance(item, dict):
                    content = item.get('content', '')
                    insert_entity('decision', content, meta_extra=item)
                else:
                    insert_entity('decision', item)
                
            # Spremi zadatke
            for item in data.get('tasks', []):
                status_icon = "✅" if item['status'] == 'done' else "todo"
                # Taskove možda ne želimo vektorizirati kao 'knowledge', ali neka budu za sad.
                insert_entity('task', f"[{status_icon}] {item['content']}")

            # Kodne blokove NE vektoriziramo kao entitete jer su već u chunkovima
            # (ili možemo ako želimo search po kodu)
            for item in data.get('code_snippets', []):
                # insert_entity('code', item['language'], item['preview'])
                # Samo SQLite za code snippet preview
                cursor.execute('''
                    INSERT INTO entities (file_path, project, type, content, context_preview, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (file_path, project, 'code', item['language'], item['preview'], timestamp))

            conn.commit()
            
        except Exception as e:
            print(f"{Fore.RED}Greška pri spremanju entiteta: {e}{Style.RESET_ALL}")
            
        conn.close()

    def save_entity(self, etype, content, project=None):
        """Ručno sprema entitet u bazu."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        # 0. Provjera duplikata
        cursor.execute("SELECT id FROM entities WHERE type = ? AND content = ? AND project = ?", (etype, content, project))
        if cursor.fetchone():
            conn.close()
            return None # Već postoji
            
        timestamp = datetime.now().isoformat()
        try:
            cursor.execute('''
                INSERT INTO entities (project, type, content, created_at)
                VALUES (?, ?, ?, ?)
            ''', (project, etype, content, timestamp))
            new_id = cursor.lastrowid
            conn.commit()
            
            # Log event
            self.log_event("entity_saved", {
                "id": new_id,
                "type": etype,
                "content": content,
                "project": project
            })
            
            # Index in ChromaDB
            self._index_entity(new_id, etype, content, project)

            
            return new_id
        except Exception as e:
            print(f"Greška pri ručnom spremanju entiteta: {e}")
            return None
        finally:
            conn.close()

    def is_file_processed(self, file_path):
        """Provjerava je li datoteka već obrađena i nepromijenjena."""
        if not os.path.exists(file_path):
            return False
            
        current_mtime = os.path.getmtime(file_path)
        
        conn = self._get_sqlite_conn()
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
        
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO files (path, project, last_modified, processed_at)
            VALUES (?, ?, ?, ?)
        ''', (file_path, project, current_mtime, datetime.now().isoformat()))
        conn.commit()
        conn.close()

    def log_event(self, event_type, data):
        """Sprema događaj u JSONL arhivu (Event Sourcing)."""
        try:
            record = {
                "event": event_type,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            with open(self.archive_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"{Fore.RED}ERROR: Greska pri logiranju dogadjaja: {e}{Style.RESET_ALL}")

    def store_archive(self, chunks, file_metadata, extracted_data=None):
        """Sprema chunkove i entitete u JSONL arhivu kao EVENT."""
        data = {
            "chunks": chunks,
            "metadata": file_metadata,
            "entities": extracted_data
        }
        self.log_event("file_processed", data)
        print(f"{Fore.BLUE}💾 Događaj 'file_processed' spremljen u arhivu.{Style.RESET_ALL}")

    def get_chroma_client(self):
        """Vraća klijenta za vektorsku bazu."""
        return chromadb.PersistentClient(path=self.store_path)

    def get_project_stats(self):
        """Dohvaća statistiku po projektima."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        projects = {}
        try:
            # Broj datoteka po projektu
            cursor.execute("SELECT project, count(*) FROM files GROUP BY project")
            for proj, count in cursor.fetchall():
                projects[proj] = {"files": count, "chunks": 0, "entities": {}}
            
            # Broj chunkova po projektu
            cursor.execute("SELECT project, count(*) FROM knowledge_fts GROUP BY project")
            for proj, count in cursor.fetchall():
                if proj in projects:
                    projects[proj]["chunks"] = count
                else:
                    projects[proj] = {"files": 0, "chunks": count, "entities": {}}
            
            # Broj entiteta po projektu i tipu
            cursor.execute("SELECT project, type, count(*) FROM entities GROUP BY project, type")
            for proj, etype, count in cursor.fetchall():
                if proj in projects:
                    projects[proj]["entities"][etype] = count
                
        except Exception as e:
            print(f"Greška pri dohvaćanju statistike projekata: {e}")
            
        conn.close()
        return projects

    def get_stats(self):
        """Dohvaća statistiku baze podataka."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        stats = {}
        try:
            cursor.execute("SELECT count(*) FROM files")
            stats['total_files'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT count(*) FROM knowledge_fts")
            stats['total_chunks'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT type, count(*) FROM entities GROUP BY type")
            stats['entities'] = dict(cursor.fetchall())
            
            # Broj vektora u sqlite-vec
            try:
                cursor.execute("SELECT count(*) FROM vec_items")
                stats['total_vectors'] = cursor.fetchone()[0]
            except:
                stats['total_vectors'] = 0
            
            # DB size
            if os.path.exists(self.meta_path):
                stats['db_size_kb'] = os.path.getsize(self.meta_path) / 1024
            else:
                stats['db_size_kb'] = 0
                
            # ChromaDB size (procjena) - ostavljamo za kompatibilnost
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

    def get_random_chunks(self, limit=50):
        """
        Dohvaća nasumične chunkove iz baze (za analizu tema).
        """
        try:
            with self._get_sqlite_conn() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT content FROM knowledge_fts ORDER BY RANDOM() LIMIT ?", (limit,))
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"Error fetching random chunks: {e}")
            return []

    def wipe_all(self, keep_archive=False):
        """Briše sve lokalne podatke."""
        # 1. Obriši SQLite podatke
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM files")
            cursor.execute("DELETE FROM knowledge_fts")
            cursor.execute("DELETE FROM entities")
            try:
                cursor.execute("DELETE FROM vec_items")
                cursor.execute("DELETE FROM vec_metadata")
            except:
                pass
            conn.commit()
        except Exception as e:
            print(f"Greška pri brisanju SQLite podataka: {e}")
        finally:
            conn.close()
        
        # 2. Obriši JSONL
        if not keep_archive and os.path.exists(self.archive_path):
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

        conn = self._get_sqlite_conn()
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
        conn = self._get_sqlite_conn()
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
        conn = self._get_sqlite_conn()
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

    def get_decision_history(self, decision_id):
        """Dohvaća cijeli lanac promjena za jednu odluku (unatrag i unaprijed)."""
        conn = self._get_sqlite_conn()
        cursor = conn.cursor()
        
        # 1. Nađi korijensku odluku (prvu u lancu) ili idi ciklički
        # Za sada ćemo samo uzeti trenutnu i tražiti sve koji su je zamijenili 
        # ili koje je ona zamijenila.
        
        # Pojednostavljeno: nađi sve odluke koje imaju isti 'content' (približno) 
        # ili su povezane preko superseded_by (Decision #ID format).
        
        all_decisions = []
        
        def find_related(current_id):
            cursor.execute("SELECT id, content, valid_from, valid_to, superseded_by, created_at FROM entities WHERE id = ?", (current_id,))
            res = cursor.fetchone()
            if not res: return
            
            dec = {
                "id": res[0],
                "content": res[1],
                "valid_from": res[2],
                "valid_to": res[3],
                "superseded_by": res[4],
                "created_at": res[5]
            }
            all_decisions.append(dec)
            
            # Ako ima superseded_by, prati lanac unaprijed
            if dec["superseded_by"] and "Decision #" in dec["superseded_by"]:
                import re
                match = re.search(r'Decision #(\d+)', dec["superseded_by"])
                if match:
                    next_id = int(match.group(1))
                    if next_id != current_id: # Spriječi infinit loop
                        find_related(next_id)

        find_related(decision_id)
        conn.close()
        return sorted(all_decisions, key=lambda x: x['created_at'])

    def ratify_decision(self, decision_id, valid_from=None, valid_to=None, superseded_by=None):
        """
        Ratificira odluke - ažurira njene temporalne parametre.
        """
        conn = self._get_sqlite_conn()
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
        
        # Log event
        self.log_event("decision_ratified", {
            "decision_id": decision_id,
            "updates": {
                "valid_from": valid_from,
                "valid_to": valid_to,
                "superseded_by": superseded_by
            }
        })
        
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
        
        # Log event
        self.log_event("decision_superseded", {
            "old_decision_id": old_decision_id,
            "new_decision_id": new_id,
            "new_decision_text": new_decision_text,
            "valid_from": valid_from
        })
        
        return new_id
