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
        Pronalazi sve .md i .txt datoteke.
        """
        files = []
        full_path = os.path.abspath(path)

        if os.path.isfile(full_path):
            return [full_path]

        extensions = ["*.md", "*.txt", "*.php", "*.js"]
        for ext in extensions:
            pattern = f"**/{ext}" if recursive else ext
            files.extend(glob.glob(os.path.join(full_path, pattern), recursive=recursive))
        
        return list(set(files)) # Unique files
    
    def _process_file(self, file_path, project="default", silent=False):
        """
        Čita datoteku, dijeli je na chunkove i sprema.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
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

            for chunk in chunks:
                stemmed_chunk = stem_text(chunk, mode="aggressive")
                self.librarian.store_fts(file_path, chunk, stemmed_chunk, project=project)
            
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
            ids = [f"{os.path.basename(file_path)}_{i}_{hash(chunk)}" for i in range(len(chunks))]
            metadatas = [file_meta for _ in chunks]
            
            self.oracle.collection.upsert(
                documents=chunks,
                metadatas=metadatas,
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
        Pametniji chunking baziran na Markdown zaglavljima (#).
        Pokušava zadržati kontekst zaglavlja.
        """
        chunks = []
        import re
        
        # Razdvajamo po zaglavljima (npr. # Naslov)
        # Ovo je jednostavna implementacija, LangChain ima bolju.
        parts = re.split(r'(^#+\s.*$)', text, flags=re.MULTILINE)
        
        current_chunk = ""
        
        for part in parts:
            if not part.strip():
                continue
                
            # Ako je zaglavlje, započni novi chunk ako je stari prevelik
            if re.match(r'^#+\s', part):
                if len(current_chunk) > self.chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = part
                else:
                    current_chunk += "\n" + part
            else:
                # Običan tekst
                if len(current_chunk) + len(part) > self.chunk_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = part
                else:
                    current_chunk += "\n" + part
                    
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        return chunks
