import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.modules.ingestor import Ingestor
from src.utils.logger import logger

from threading import Timer

class DebouncedEventHandler(FileSystemEventHandler):
    """Handler koji koristi debounce tehniku za stabilnije praćenje promjena."""
    
    def __init__(self, ingestor, debounce_interval=2.0):
        self.ingestor = ingestor
        self.debounce_interval = debounce_interval
        self.timers = {}

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.md'):
            self._schedule_processing(event.src_path)

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.md'):
            self._schedule_processing(event.src_path)

    def _schedule_processing(self, file_path):
        """Zadaje zadatak s odgodom. Ako se dogodi novi event, resetira timer."""
        if file_path in self.timers:
            self.timers[file_path].cancel()
        
        logger.info(f"⏳ Detektirane promjene na {os.path.basename(file_path)}, čekam stabilizaciju...")
        
        timer = Timer(self.debounce_interval, self._process_file, args=[file_path])
        self.timers[file_path] = timer
        timer.start()

    def _process_file(self, file_path):
        """Callback funkcija koja se izvršava nakon isteka timera."""
        if file_path in self.timers:
            del self.timers[file_path]
            
        logger.info(f"🔄 Procesiram: {os.path.basename(file_path)}")
        try:
            self.ingestor._process_file(file_path, silent=False)
        except Exception as e:
            logger.error(f"Greška tijekom procesiranja {file_path}: {e}")

class Watcher:
    """Glavna klasa za nadzor foldera."""
    
    def __init__(self, path=".", recursive=True):
        self.path = path
        self.recursive = recursive
        self.ingestor = Ingestor()
        self.event_handler = DebouncedEventHandler(self.ingestor)
        self.observer = Observer()

    def run(self):
        """Pokreće monitoring u petlji."""
        logger.info(f"👀 Kronos Watcher pokrenut na: {os.path.abspath(self.path)}")
        self.observer.schedule(self.event_handler, self.path, recursive=self.recursive)
        self.observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
            logger.info("🛑 Watcher zaustavljen.")
        self.observer.join()
