import os
import glob
from src.utils.logger import logger
from src.utils.stemmer import stem_text
from src.modules.librarian import Librarian
from src.modules.oracle import Oracle
from src.modules.extractor import Extractor

class Ingestor:
    def __init__(self, chunk_size=1000, db_path="data"):
        self.chunk_size = chunk_size
        self.librarian = Librarian(db_path)
        self.oracle = Oracle(os.path.join(db_path, "store"))
        self.extractor = Extractor()
        
        if not os.path.exists(os.path.join(db_path, "archive.jsonl")):
            logger.warning("🚧 Kreiram novu arhivu...")

    def run(self, path, project_name=None, recursive=False, silent=False):
        """
        Glavna metoda za pokretanje ingestije na cijeloj putanji (folder ili file).
        """
        # Detektiraj ime projekta ako nije zadan
        if not project_name:
            full_path = os.path.abspath(path)
            project_name = os.path.basename(full_path)
            if not project_name: # Slučaj ako je path npr. "C:/"
                project_name = "default"

        if not silent:
            logger.info(f"Pokrećem Ingestora na projektu [bold cyan]{project_name}[/] (putanja: {path})")
        
        files = self._scan_files(path, recursive)
        self.run_batch(files, project_name=project_name, silent=silent)

    def run_batch(self, files, project_name="default", silent=False):
        """
        Obrađuje listu datoteka.
        """
        if not files:
            return

        if not silent:
            logger.info(f"Ingestor obrađuje batch od {len(files)} datoteka.")

        processed_count = 0
        for file_path in files:
            if os.path.exists(file_path):
                self._process_file(file_path, project=project_name, silent=silent)
                processed_count += 1
            
        if not silent:
            logger.success(f"Batch završen. Obrađeno {processed_count} datoteka.")

    def _scan_files(self, path, recursive):
        """
        Pronalazi sve podržane datoteke, preskačući nepoželjne foldere.
        """
        files = []
        full_path = os.path.abspath(path)

        if os.path.isfile(full_path):
            return [full_path]

        # Folderi koje UVIJEK preskačemo
        blacklist = {
            'node_modules', '.git', '.venv', 'venv', '__pycache__', 
            '.pytest_cache', 'dist', 'build', '.vscode', '.agent',
            '.vercel', 'target', 'data', 'logs', 'backups', 'benchmarks',
            'tests', '.pytest_cache', '.antigravity'
        }

        if recursive:
            extensions = [".md", ".txt", ".php", ".js", ".jsx", ".tsx", ".html", ".htm", ".py"]
            for root, dirs, filenames in os.walk(full_path):
                # In-place modifikacija dirs liste omogućuje os.walk-u da ih preskoči
                dirs[:] = [d for d in dirs if d not in blacklist and not d.startswith('.')]
                
                for filename in filenames:
                    # Dodatna provjera za fazaX.md i slične task fajlove
                    import re
                    if re.match(r'faza\d+.*\.md$', filename, re.IGNORECASE) or 'handoff' in filename.lower():
                        continue
                        
                    if any(filename.endswith(ext) for ext in extensions):
                        files.append(os.path.join(root, filename))
        else:
            extensions = ["*.md", "*.txt", "*.php", "*.js", "*.jsx", "*.tsx", "*.html", "*.htm", "*.py"]
            import re
            for ext in extensions:
                found = glob.glob(os.path.join(full_path, ext))
                for f in found:
                    fname = os.path.basename(f)
                    if not (re.match(r'faza\d+.*\.md$', fname, re.IGNORECASE) or 'handoff' in fname.lower()):
                        files.append(f)
        
        return list(set(files)) # Unique files
    
    def _process_file(self, file_path, project="default", silent=False):
        """
        Čita datoteku, dijeli je na chunkove i sprema.
        """
        try:
            from src.utils.file_helper import detect_encoding
            encoding = detect_encoding(file_path)
            with open(file_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()
                
            if not content.strip():
                return
                
            chunks = self._chunk_content(content)
            file_meta = {
                "source": file_path, 
                "filename": os.path.basename(file_path),
                "project": project
            }
            
            # 1. Pripremi FTS (očisti stare zapise)
            self.librarian.delete_fts(file_path)

            for chunk_data in chunks:
                chunk_text = chunk_data["content"]
                stemmed_chunk = stem_text(chunk_text, mode="aggressive")
                self.librarian.store_fts(
                    file_path, 
                    chunk_text, 
                    stemmed_chunk, 
                    project=project,
                    start_line=chunk_data.get("start_line", 1),
                    end_line=chunk_data.get("end_line", 1)
                )
            
            # 2. Ekstrakcija i pohrana strukturiranih podataka
            extracted_data = self.extractor.extract(content)
            if any(extracted_data.values()):
                self.librarian.store_extracted_data(file_path, extracted_data, project=project)
                summary = self.extractor.summarize_extraction(extracted_data)
                if not silent:
                    logger.info(f"   Strukturirano znanje: {summary}")

            # 3. Spremi u arhivu (JSONL)
            self.librarian.store_archive(chunks, file_meta, extracted_data=extracted_data)
            
            # Vektorizacija (ChromaDB)
            ids = []
            final_metas = []
            final_docs = []
            
            for i, chunk_data in enumerate(chunks):
                uid = f"{os.path.basename(file_path)}_{i}_{hash(chunk_data['content'])}"
                ids.append(uid)
                
                chunk_meta = file_meta.copy()
                chunk_meta["start_line"] = chunk_data["start_line"]
                chunk_meta["end_line"] = chunk_data["end_line"]
                
                final_metas.append(chunk_meta)
                final_docs.append(chunk_data["content"])
            
            self.oracle.safe_upsert(
                documents=final_docs,
                metadatas=final_metas,
                ids=ids
            )
            
            # 4. Označi kao obrađeno
            self.librarian.mark_as_processed(file_path, project=project)
            
            if not silent:
                logger.success(f"Vektorizirano: {os.path.basename(file_path)} [{project}]")
            
        except Exception as e:
            logger.error(f"Greška pri čitanju {file_path}: {e}")

    def _chunk_content(self, text):
        """
        Chunking koji prati brojeve linija.
        Vraća listu dict-ova: [{'content': str, 'start_line': int, 'end_line': int}]
        """
        lines = text.splitlines(keepends=True)
        chunks = []
        current_chunk_lines = []
        current_start_line = 1
        current_size = 0
        
        for i, line in enumerate(lines):
            line_num = i + 1
            line_len = len(line)
            
            # Ako dodavanje linije prelazi chunk_size, spremi trenutni chunk
            if current_size + line_len > self.chunk_size and current_chunk_lines:
                chunks.append({
                    "content": "".join(current_chunk_lines).strip(),
                    "start_line": current_start_line,
                    "end_line": line_num - 1
                })
                current_chunk_lines = []
                current_start_line = line_num
                current_size = 0
            
            current_chunk_lines.append(line)
            current_size += line_len
            
        if current_chunk_lines:
            chunks.append({
                "content": "".join(current_chunk_lines).strip(),
                "start_line": current_start_line,
                "end_line": len(lines)
            })
            
        return chunks
