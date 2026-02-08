import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from src.modules.ingestor import Ingestor
from src.utils.logger import logger

class KronosHandler(FileSystemEventHandler):
    """Handler koji reagira na promjene u datotečnom sustavu."""
    
    def __init__(self, ingestor: Ingestor):
        self.ingestor = ingestor

    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith('.md'):
            logger.info(f"🔄 Datoteka promijenjena: {os.path.basename(event.src_path)}")
            # Kratka pauza da se osigura da je file sistem završio pisanje
            time.sleep(0.5)
            self.ingestor._process_file(event.src_path, silent=False)

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith('.md'):
            logger.info(f"🆕 Nova datoteka: {os.path.basename(event.src_path)}")
            time.sleep(0.5)
            self.ingestor._process_file(event.src_path, silent=False)

class Watcher:
    """Glavna klasa za nadzor foldera."""
    
    def __init__(self, path=".", recursive=True):
        self.path = path
        self.recursive = recursive
        self.ingestor = Ingestor()
        self.event_handler = KronosHandler(self.ingestor)
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
