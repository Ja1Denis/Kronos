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
        """Kreira tablice za praćenje datoteka."""
        conn = sqlite3.connect(self.meta_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS files (
                path TEXT PRIMARY KEY,
                last_modified REAL,
                hash TEXT,
                processed_at TEXT
            )
        ''')
        conn.commit()
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
