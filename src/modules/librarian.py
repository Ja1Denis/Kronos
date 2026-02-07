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
