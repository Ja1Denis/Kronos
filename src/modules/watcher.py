import os
import time
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.modules.job_manager import JobManager
from src.utils.logger import logger

class BatchJobEventHandler(FileSystemEventHandler):
    """
    Handler koji prikuplja promjene i šalje ih kao batch job u JobManager.
    """
    
    def __init__(self, debounce_interval=5.0, max_batch_size=20):
        self.job_manager = JobManager()
        self.debounce_interval = debounce_interval
        self.max_batch_size = max_batch_size
        
        self.pending_files = set()
        self.timer = None
        self.lock = threading.Lock()

    def on_modified(self, event):
        if self._is_relevant(event):
            self._add_to_batch(event.src_path)

    def on_created(self, event):
        if self._is_relevant(event):
            self._add_to_batch(event.src_path)

    def _is_relevant(self, event):
        """Provjerava je li datoteka relevantna za Kronos."""
        if event.is_directory:
            return False
            
        # Ignoriraj baze podataka i privremene datoteke
        if any(x in event.src_path for x in ['.db', '.store', '.gemini', '.git', '__pycache__', 'test_output.txt']):
             return False
             
        # Relevantne ekstenzije
        return any(event.src_path.endswith(ext) for ext in ['.md', '.txt', '.php', '.js', '.py'])

    def _add_to_batch(self, file_path):
        """Dodaje datoteku u batch i (re)starta timer."""
        with self.lock:
            self.pending_files.add(os.path.abspath(file_path))
            
            # Ako smo dosegli max size, šalji odmah
            if len(self.pending_files) >= self.max_batch_size:
                self._submit_batch()
                return

            # Resetira ili pokreće timer
            if self.timer:
                self.timer.cancel()
            
            self.timer = threading.Timer(self.debounce_interval, self._submit_batch)
            self.timer.start()
            logger.info(f"⏳ Detektirana promjena: {os.path.basename(file_path)}. Batch size: {len(self.pending_files)}")

    def _submit_batch(self):
        """Šalje prikupljene datoteke u JobManager."""
        with self.lock:
            if not self.pending_files:
                return

            files_to_process = list(self.pending_files)
            self.pending_files.clear()
            
            if self.timer:
                self.timer.cancel()
                self.timer = None

            # Kreiraj Job
            # Pokušavamo detektirati zajednički projekt iz prve datoteke (približno)
            project_name = "default"
            # TODO: Naprednije detektiranje projekta ako je potrebno
            
            job_id = self.job_manager.submit_job(
                job_type="ingest_batch",
                params={
                    "files": files_to_process,
                    "project": project_name
                },
                priority=3 # Niži prioritet od manualnog 'ask' ili direktnog 'ingest'
            )
            
            logger.success(f"🚀 Watcher poslao batch posao {job_id} ({len(files_to_process)} datoteka)")

class Watcher:
    """Glavna klasa za nadzor foldera (Faza 8 - Job Queue version)."""
    
    def __init__(self, path=".", recursive=True, debounce=5.0):
        self.path = path
        self.recursive = recursive
        self.event_handler = BatchJobEventHandler(debounce_interval=debounce)
        self.observer = Observer()

    def start(self):
        """Pokreće observer u pozadinskoj niti."""
        logger.info(f"👀 Kronos Watcher (Batch Mode) pokrenut na: {os.path.abspath(self.path)}")
        self.observer.schedule(self.event_handler, self.path, recursive=self.recursive)
        self.observer.start()

    def stop(self):
        """Zaustavlja observer."""
        self.observer.stop()
        self.observer.join()
        logger.info("🛑 Watcher zaustavljen.")

    def run(self):
        """Blokirajuća metoda za samostalno pokretanje."""
        self.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()
