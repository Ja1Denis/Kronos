import time
import threading
import signal
import sys
import traceback
from typing import Dict, Any, Optional
from datetime import datetime

import asyncio
from src.modules.job_manager import JobManager
from src.modules.notification_manager import notification_manager
from src.modules.analyst import proactive_analyst
from src.modules.ingestor import Ingestor

# Map job types to handler functions
# For now only 'ingest' is supported
JOB_HANDLERS = {
    "ingest": "handle_ingest",
    "ingest_batch": "handle_ingest_batch",
    "test_job": "handle_test"
}

class Worker:
    def __init__(self, manager: Optional[JobManager] = None, poll_interval: float = 0.5):
        self.manager = manager if manager else JobManager()
        self.poll_interval = poll_interval
        self._shutdown_event = threading.Event()
        self._thread = None
        self._current_job_id = None
        
    def start(self):
        """Starts the worker thread."""
        if self._thread and self._thread.is_alive():
            print("⚠️ Worker already running.")
            return

        print("🚀 Worker starting...")
        self._shutdown_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="KronosWorker")
        self._thread.start()
        
    def stop(self):
        """Signals the worker to stop gracefully."""
        print("🛑 Worker stopping...")
        self._shutdown_event.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            if self._thread.is_alive():
                print("⚠️ Worker thread did not exit in time.")
            else:
                print("✅ Worker stopped.")

    async def _notify(self, job_id: str, status: str, progress: int = 0, msg: str = ""):
        """Helper to send async notifications from sync worker."""
        try:
            await notification_manager.notify_job_update(job_id, status, progress, msg)
        except Exception as e:
            print(f"⚠️ Notification Error: {e}")

    def _run_loop(self):
        """Main worker loop."""
        print("🔧 Worker loop active.")
        
        # Create a new event loop for this thread if needed
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
        while not self._shutdown_event.is_set():
            try:
                # 1. Fetch Job
                job = self.manager.get_next_job()
                if not job:
                    time.sleep(self.poll_interval)
                    continue

                # 2. Check cancellation (just in case)
                if job['status'] == 'cancelled':
                    continue

                # 3. Start Job
                job_id = job['id']
                if not self.manager.start_job(job_id):
                    # Could not lock job, maybe another worker took it
                    continue

                self._current_job_id = job_id
                job_type = job['type']
                print(f"🔨 Worker picked up job {job_id} ({job_type})")
                
                # Notify Start
                loop.run_until_complete(
                    self._notify(job_id, "running", 0, f"Started job {job_type}")
                )

                # 4. Execute
                try:
                    self._execute_job(job, loop) # Pass loop for progress updates
                except Exception as e:
                    error_msg = f"{str(e)}\n{traceback.format_exc()}"
                    print(f"❌ Job {job_id} failed: {e}")
                    self.manager.fail_job(job_id, error_msg)
                    
                    # Notify Failure
                    loop.run_until_complete(
                        self._notify(job_id, "failed", 0, str(e))
                    )
                finally:
                    self._current_job_id = None
            
            except Exception as e:
                print(f"❌ Critical Worker Error: {e}")
                traceback.print_exc()
                time.sleep(5.0) # Backoff

    def _execute_job(self, job: Dict[str, Any], loop):
        job_type = job['type']
        params = job.get('params', {})
        
        handler_name = JOB_HANDLERS.get(job_type)
        if not handler_name:
            raise ValueError(f"Unknown job type: {job_type}")
            
        handler = getattr(self, handler_name, None)
        if not handler:
            raise ValueError(f"Handler method {handler_name} not found")
            
        # Run handler (handler doesn't need loop usually, but good to have)
        # We might want to pass a progress_callback to handlers
        
        def progress_cb(p: int):
            self.manager.update_progress(job['id'], p)
            # Optional: Notify progress (maybe not every % to avoid spam)
            if p % 10 == 0:
                loop.run_until_complete(
                    self._notify(job['id'], "running", p)
                )

        # Run handler
        result = handler(job, params)
        
        # --- PROACTIVE ANALYSIS ---
        # If this was an ingest job, run proactive analysis
        if job_type in ["ingest", "ingest_batch"] and result.get("status") != "failed":
            files_to_analyze = []
            if job_type == "ingest":
                files_to_analyze = [params.get("path")]
            else:
                files_to_analyze = params.get("files", [])
            
            project = params.get("project", "default")
            
            # Run analysis in the loop
            print(f"🧠 Triggering proactive analysis for {len(files_to_analyze)} files...")
            loop.run_until_complete(
                proactive_analyst.analyze_ingest(files_to_analyze, project=project)
            )

        # Complete
        self.manager.complete_job(job['id'], result)
        print(f"✅ Job {job['id']} completed successfully.")
        
        # Notify Completion
        loop.run_until_complete(
            self._notify(job['id'], "completed", 100, "Job Finished")
        )

    # --- HANDLERS ---

    def handle_test(self, job, params):
        """Test handler that simulates work."""
        duration = params.get("duration", 1)
        print(f"Simulating work for {duration}s...")
        
        steps = 10
        for i in range(steps):
            if self._shutdown_event.is_set():
                raise InterruptedError("Worker shutting down")
            
            # Auto-update progress
            progress = int((i + 1) / steps * 100)
            self.manager.update_progress(job['id'], progress)
            time.sleep(duration / steps)
            
        return {"msg": "Test work done", "params": params}

    def handle_ingest(self, job, params):
        """Runs the Ingestor."""
        path = params.get("path")
        project = params.get("project")
        recursive = params.get("recursive", False)
        
        if not path:
            raise ValueError("Missing 'path' parameter for ingest job")
            
        print(f"📂 Ingesting: {path} (Project: {project})")
        
        # Initialize Ingestor
        # Note: Ingestor might take time. We should ideally pass a progress callback to it.
        # For now, we update progress to 10% started, 90% done, 100% finished.
        self.manager.update_progress(job['id'], 10)
        
        ingestor = Ingestor()
        ingestor.run(path, project_name=project, recursive=recursive, silent=True)
        
        self.manager.update_progress(job['id'], 90)
        
        from src.modules.librarian import Librarian
        stats = Librarian().get_stats()
        
        return {
            "path": path,
            "status": "ingested",
            "db_stats": stats
        }

    def handle_ingest_batch(self, job, params):
        """Runs the Ingestor for a list of files."""
        files = params.get("files", [])
        project = params.get("project", "default")
        
        if not files:
            return {"status": "skipped", "reason": "no files"}
            
        print(f"📦 Batch Ingesting: {len(files)} files (Project: {project})")
        
        self.manager.update_progress(job['id'], 5)
        
        ingestor = Ingestor()
        
        # We can update progress per file
        total = len(files)
        for i, file_path in enumerate(files):
            if self._shutdown_event.is_set():
                raise InterruptedError("Worker shutting down")
                
            ingestor._process_file(file_path, project=project, silent=True)
            
            # Update progress (5 to 95 range)
            progress = int(5 + (i + 1) / total * 90)
            self.manager.update_progress(job['id'], progress)

        self.manager.update_progress(job['id'], 100)
        
        from src.modules.librarian import Librarian
        stats = Librarian().get_stats()
        
        return {
            "count": len(files),
            "status": "completed",
             "db_stats": stats
        }
