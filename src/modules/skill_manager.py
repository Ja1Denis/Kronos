import os
import re
import json
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.utils.logger import logger
from src.modules.librarian import Librarian

class SkillManager:
    def __init__(self, librarian: Optional[Librarian] = None):
        self.librarian = librarian or Librarian()
        
        # Odredi staze do skill direktorija
        curr_dir = os.path.dirname(os.path.abspath(__file__)) # src/modules
        src_dir = os.path.dirname(curr_dir) # src
        self.root_dir = os.path.dirname(src_dir) # kronos
        self.workspace_root = os.path.dirname(self.root_dir) # ai-test-project
        
        # Pobrini se da tablica postoji
        self._init_db()

    def _init_db(self):
        """Kreira tablicu za skillove ako ne postoji."""
        conn = self.librarian._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registered_skills (
                name TEXT PRIMARY KEY,
                description TEXT,
                path TEXT,
                parameters_json TEXT,
                created_at TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def _parse_skill_md(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        Parsira SKILL.md i izvlači YAML frontmatter i opis.
        """
        if not os.path.exists(file_path):
            return None
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Regex za pronalaženje YAML frontmattera
            yaml_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
            if not yaml_match:
                return None
                
            yaml_text = yaml_match.group(1)
            
            # Jednostavno ručno parsiranje YAML-a (samo name i description)
            metadata = {}
            for line in yaml_text.split('\n'):
                if ':' in line:
                    key, val = line.split(':', 1)
                    metadata[key.strip().lower()] = val.strip()
            
            name = metadata.get('name')
            description = metadata.get('description', '')
            
            if not name:
                # Fallback na ime foldera ako name nije definiran
                name = os.path.basename(os.path.dirname(file_path))
                
            return {
                "name": name,
                "description": description,
                "path": file_path,
                "parameters": {}  # Parametri se mogu proširiti u budućnosti
            }
        except Exception as e:
            logger.error(f"Failed to parse skill file {file_path}: {e}")
            return None

    def scan_and_register_skills(self) -> List[Dict[str, Any]]:
        """
        Skenira cijeli radni prostor za SKILL.md datoteke (preskačući venv, node_modules, .git itd.)
        i registrira sve pronađene skillove u bazu i vektorski indeks.
        """
        registered = []
        exclude_dirs = {'.git', 'venv', '.venv', 'node_modules', '__pycache__', '.pytest_cache', 'backups', 'logs', 'data'}
        
        logger.info(f"Scanning workspace root for SKILL.md files: {self.workspace_root}")
        
        try:
            for root, dirs, files in os.walk(self.workspace_root):
                # Filtriraj ignorirane direktorije na licu mjesta da os.walk ne ulazi u njih
                dirs[:] = [d for d in dirs if d not in exclude_dirs and not d.startswith('.')]
                
                for file in files:
                    if file.upper() == 'SKILL.MD':
                        skill_md_path = os.path.join(root, file)
                        skill_data = self._parse_skill_md(skill_md_path)
                        if skill_data:
                            self.register_skill(
                                name=skill_data["name"],
                                description=skill_data["description"],
                                path=skill_data["path"],
                                parameters=skill_data["parameters"]
                            )
                            registered.append(skill_data)
        except Exception as e:
            logger.error(f"Error while walking workspace for skills: {e}")
                            
        return registered

    def register_skill(self, name: str, description: str, path: str, parameters: Dict[str, Any] = None) -> bool:
        """
        Registrira pojedini skill u SQLite i stvara embedding za opis.
        """
        if parameters is None:
            parameters = {}
            
        timestamp = datetime.now().isoformat()
        
        try:
            conn = self.librarian._get_sqlite_conn()
            cursor = conn.cursor()
            
            # 1. Spremanje u registered_skills
            cursor.execute('''
                INSERT OR REPLACE INTO registered_skills (name, description, path, parameters_json, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, description, path, json.dumps(parameters), timestamp))
            conn.commit()
            conn.close()
            
            # 2. Vektorsko indeksiranje u vec_metadata / vec_items
            if self.librarian.embedding_function:
                embeddings = self.librarian.embedding_function([f"Skill: {name}. Description: {description}"])
                if embeddings:
                    embedding = embeddings[0]
                    import sqlite_vec
                    
                    conn = self.librarian._get_sqlite_conn()
                    cursor = conn.cursor()
                    try:
                        uid = f"skill_{name.replace(' ', '_').lower()}"
                        meta = {
                            "type": "skill",
                            "name": name,
                            "description": description,
                            "path": path,
                            "created_at": timestamp
                        }
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO vec_metadata (custom_id, document, metadata_json, project)
                            VALUES (?, ?, ?, ?)
                        ''', (uid, description, json.dumps(meta), "skills"))
                        
                        rowid = cursor.lastrowid
                        
                        cursor.execute('''
                            INSERT OR REPLACE INTO vec_items (rowid, embedding)
                            VALUES (?, ?)
                        ''', (rowid, sqlite_vec.serialize_float32(embedding)))
                        conn.commit()
                        logger.info(f"Successfully vectorized and registered skill: {name}")
                    except Exception as e:
                        conn.rollback()
                        logger.error(f"Failed to save skill vector: {e}")
                    finally:
                        conn.close()
            
            return True
        except Exception as e:
            logger.error(f"Failed to register skill {name}: {e}")
            return False

    def list_skills(self) -> List[Dict[str, Any]]:
        """Vraća sve registrirane skillove iz baze."""
        conn = self.librarian._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute("SELECT name, description, path, parameters_json, created_at FROM registered_skills")
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "name": r[0],
                "description": r[1],
                "path": r[2],
                "parameters": json.loads(r[3]),
                "created_at": r[4]
            }
            for r in rows
        ]

    def match_skill(self, query: str, threshold: float = 0.7) -> Optional[Dict[str, Any]]:
        """
        Pretražuje registrirane skillove semantički i vraća najbolji ako prelazi prag.
        """
        if not self.librarian.embedding_function:
            logger.warning("No embedding function available for skill matching.")
            return None
            
        try:
            emb = self.librarian.embedding_function([query])[0]
            import sqlite_vec
            emb_bytes = sqlite_vec.serialize_float32(emb)
            
            conn = self.librarian._get_sqlite_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT m.custom_id, m.document, m.metadata_json, v.distance
                FROM vec_items v
                JOIN vec_metadata m ON v.rowid = m.rowid
                WHERE v.embedding MATCH ? AND k = 1
                  AND json_extract(m.metadata_json, '$.type') = 'skill'
                ORDER BY v.distance ASC
            ''', (emb_bytes,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                custom_id, document, metadata_json, distance = row
                score = 1.0 - distance
                logger.info(f"Skill match result: {custom_id} with score {score:.4f} (distance {distance:.4f})")
                
                if score >= threshold:
                    meta = json.loads(metadata_json)
                    return {
                        "name": meta.get("name"),
                        "description": meta.get("description"),
                        "path": meta.get("path"),
                        "score": score
                    }
            return None
        except Exception as e:
            logger.error(f"Error matching skill: {e}")
            return None
