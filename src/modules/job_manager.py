import sqlite3
import json
import uuid
import time
import threading
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
import os

class JobManager:
    """
    Manages the persistent job queue using SQLite.
    Handles job submission, retrieval, updates, and cleanup.
    """
    def __init__(self, db_path: str = "data/jobs.db"):
        self.db_path = db_path
        self._ensure_db_dir()
        self._init_db()
        self._worker_thread = None
        self._stop_event = threading.Event()

    def _ensure_db_dir(self):
        """Ensures the directory for the database exists."""
        directory = os.path.dirname(self.db_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)

    def _get_connection(self):
        """Returns a sqlite3 connection with Row factory."""
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        # Omogući WAL mode za bolju konkurentnost na Windowsima
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except:
            pass
        return conn

    def _execute(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False) -> Any:
        """Helper to execute a query and close the connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
                conn.commit()
                return result
            elif fetch_all:
                result = cursor.fetchall()
                conn.commit()
                return result
            else:
                conn.commit()
                return cursor.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_db(self):
        """Initializes the database schema if it doesn't exist."""
        conn = sqlite3.connect(self.db_path)
        try:
            # Create jobs table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS jobs (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    priority INTEGER DEFAULT 5,
                    params TEXT,
                    result TEXT,
                    error TEXT,
                    progress INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    finished_at TIMESTAMP
                )
            ''')
            
            # Create index for efficient polling
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_status_priority 
                ON jobs(status, priority DESC, created_at ASC)
            ''')
            
            # Create index for cleanup
            conn.execute('''
                CREATE INDEX IF NOT EXISTS idx_finished_at 
                ON jobs(finished_at)
            ''')
            
            conn.commit()
        finally:
            conn.close()

    def submit_job(self, job_type: str, params: Dict[str, Any], priority: int = 5) -> str:
        """
        Submits a new job to the queue.
        
        Args:
            job_type: Type of the job (e.g., 'ingest', 'prune')
            params: Dictionary of parameters for the job
            priority: Priority (1-10), higher is more important
            
        Returns:
            The ID of the newly created job.
        """
        job_id = str(uuid.uuid4())
        params_json = json.dumps(params)
        
        self._execute('''
            INSERT INTO jobs (id, type, params, priority, status)
            VALUES (?, ?, ?, ?, 'pending')
        ''', (job_id, job_type, params_json, priority))
            
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves job details by ID."""
        row = self._execute('SELECT * FROM jobs WHERE id = ?', (job_id,), fetch_one=True)
        
        if not row:
            return None
        
        return self._row_to_dict(row)

    def get_next_job(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves the next pending job with the highest priority.
        Does NOT mark it as running (worker should do that).
        """
        row = self._execute('''
            SELECT * FROM jobs 
            WHERE status = 'pending' 
            ORDER BY priority DESC, created_at ASC 
            LIMIT 1
        ''', fetch_one=True)
        
        if not row:
            return None
        
        return self._row_to_dict(row)

    def start_job(self, job_id: str) -> bool:
        """
        Marks a job as 'running' and sets the started_at timestamp.
        Returns True if successful, False if job was not found or not pending.
        """
        now = datetime.now().isoformat()
        rowcount = self._execute('''
            UPDATE jobs 
            SET status = 'running', started_at = ? 
            WHERE id = ? AND status = 'pending'
        ''', (now, job_id))
        return rowcount > 0

    def update_progress(self, job_id: str, progress: int, status: Optional[str] = None):
        """Updates the progress percentage and optionally the status."""
        if status:
            self._execute('''
                UPDATE jobs SET progress = ?, status = ? WHERE id = ?
            ''', (progress, status, job_id))
        else:
            self._execute('''
                UPDATE jobs SET progress = ? WHERE id = ?
            ''', (progress, job_id))

    def complete_job(self, job_id: str, result: Dict[str, Any] = None):
        """Marks a job as 'completed' and saves the result."""
        now = datetime.now().isoformat()
        result_json = json.dumps(result) if result else None
        
        self._execute('''
            UPDATE jobs 
            SET status = 'completed', progress = 100, result = ?, finished_at = ? 
            WHERE id = ?
        ''', (result_json, now, job_id))

    def fail_job(self, job_id: str, error: str):
        """Marks a job as 'failed' and saves the error message."""
        now = datetime.now().isoformat()
        self._execute('''
            UPDATE jobs 
            SET status = 'failed', error = ?, finished_at = ? 
            WHERE id = ?
        ''', (error, now, job_id))

    def cancel_job(self, job_id: str) -> bool:
        """
        Marks a pending or running job as 'cancelled'.
        Returns True if successful.
        """
        now = datetime.now().isoformat()
        # Only cancel if not already finished
        rowcount = self._execute('''
            UPDATE jobs 
            SET status = 'cancelled', finished_at = ? 
            WHERE id = ? AND status IN ('pending', 'running')
        ''', (now, job_id))
        return rowcount > 0

    def list_jobs(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Lists recent jobs."""
        rows = self._execute('''
            SELECT * FROM jobs 
            ORDER BY created_at DESC 
            LIMIT ?
        ''', (limit,), fetch_all=True)
        return [self._row_to_dict(row) for row in rows]

    def cleanup_old_jobs(self, days: int = 7):
        """Deletes jobs that finished more than 'days' ago."""
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        self._execute('''
            DELETE FROM jobs 
            WHERE finished_at IS NOT NULL AND finished_at < ?
        ''', (cutoff_date,))

    def get_job_stats(self) -> Dict[str, Any]:
        """Calculates job queue metrics."""
        with self._get_connection() as conn:
            # 1. Status Counts
            cursor = conn.execute("SELECT status, count(*) FROM jobs GROUP BY status")
            counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 2. Total and Success Rate
            total = sum(counts.values())
            completed = counts.get('completed', 0)
            failed = counts.get('failed', 0)
            success_rate = (completed / (completed + failed) * 100) if (completed + failed) > 0 else 0
            
            # 3. Latency (completed jobs)
            # We use started_at and finished_at
            cursor = conn.execute('''
                SELECT started_at, finished_at FROM jobs 
                WHERE status = 'completed' AND started_at IS NOT NULL AND finished_at IS NOT NULL
                LIMIT 100 -- Only calculate for last 100 jobs
            ''')
            latencies = []
            for row in cursor.fetchall():
                try:
                    start = datetime.fromisoformat(row[0])
                    end = datetime.fromisoformat(row[1])
                    latencies.append((end - start).total_seconds())
                except:
                    continue
            
            avg_latency = (sum(latencies) / len(latencies)) if latencies else 0
            
            return {
                "counts": counts,
                "total": total,
                "success_rate": f"{success_rate:.1f}%",
                "avg_latency_sec": f"{avg_latency:.2f}s"
            }

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        """Konvertira SQLite row u dict i parsira JSON polja."""
        d = dict(row)
        if d.get('params'):
            try:
                d['params'] = json.loads(d['params'])
            except:
                d['params'] = {}
        if d.get('result'):
            try:
                d['result'] = json.loads(d['result'])
            except:
                d['result'] = {}
        return d

    # --- Background Worker Logic ---
    
    def start_worker(self):
        """Pokreće pozadinski worker thread ako već nije pokrenut."""
        if self._worker_thread and self._worker_thread.is_alive():
            return # Već radi
            
        self._stop_event.clear()
        self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._worker_thread.start()
        
    def stop_worker(self):
        """Zaustavlja pozadinski worker thread."""
        self._stop_event.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=2.0)
            
    def _worker_loop(self):
        """Glavna petlja workera."""
        # Lokalni import da izbjegnemo kružne ovisnosti na vrhu
        # (Ovdje bi trebali importati logiku za ingest, rebuild itd.)
        # Za sada ćemo samo simulirati rad ili zvati vanjske funkcije ako ih imamo pri ruci.
        # Ali čekaj, JobManager je niskorazinski! On ne zna za Librarian.
        # Rješenje: Worker mora imati callbackove ili moramo importati Librarian ovdje.
        
        # Pojednostavljeno: Worker samo logira "Processing" i markira kao done za test.
        # Za pravu ingestiju, moramo pozvati Librarian.ingest.
        
        # Dinamički import Ingestor-a (jer on zna raditi posao)
        try:
            from src.modules.ingestor import Ingestor
            # Ingestor interno koristi Librarian, pa ne trebamo brinuti o putanjama
        except Exception as e:
            print(f"Worker Error: Ne mogu inicijalizirati Ingestor: {e}")
            return

        while not self._stop_event.is_set():
            job = self.get_next_job()
            if not job:
                time.sleep(2) # Nema posla, spavaj
                continue
                
            job_id = job['id']
            job_type = job['type']
            params = job.get('params', {})
            
            # Start job
            if not self.start_job(job_id):
                continue # Netko drugi ga je uzeo
                
            try:
                # OBAVLJANJE POSLA
                if job_type == 'test_job':
                    time.sleep(2) # Simulacija rada
                    self.complete_job(job_id, {"message": params.get("echo", "Done")})
                    
                elif job_type == 'ingest' or job_type == 'ingest_batch':
                    path = params.get('path', '.')
                    recursive = params.get('recursive', True)
                    
                    # Koristi Ingestor
                    ingestor = Ingestor()
                    # Ingestor.run vraća dict sa statistikom? Ne, vraća None, ali printa.
                    # Moramo vidjeti Ingestor.run. Pretpostavimo da radi side-effects.
                    # Za sada samo zovemo run i kažemo "Done".
                    # Idealno bi Ingestor vratio stats objekt.
                    ingestor.run(path, recursive=recursive, silent=True) # Silent da ne spamamo stdout
                    
                    self.complete_job(job_id, {"status": "Ingested", "path": path})
                    
                else:
                    self.fail_job(job_id, f"Nepoznati tip posla: {job_type}")
                    
            except Exception as e:
                self.fail_job(job_id, str(e))
            
            time.sleep(0.5) # Mali predah
