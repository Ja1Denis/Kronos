import os
import time
import uuid
import sqlite3
from datetime import datetime
from typing import List, Dict, Any, Optional
from src.utils.logger import logger
from src.modules.librarian import Librarian

class ApprovalManager:
    def __init__(self, librarian: Optional[Librarian] = None):
        self.librarian = librarian or Librarian()
        self._init_db()

    def _init_db(self):
        """Kreira tablicu za approvals (odobrenja) ako ne postoji."""
        conn = self.librarian._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS approvals (
                id TEXT PRIMARY KEY,
                skill_name TEXT,
                query TEXT,
                status TEXT, -- 'PENDING', 'APPROVED', 'REJECTED'
                created_at TEXT,
                resolved_at TEXT
            )
        ''')
        conn.commit()
        conn.close()

    def create_request(self, skill_name: str, query: str) -> str:
        """
        Kreira novi zahtjev za odobrenje i vraća njegov jedinstveni ID.
        """
        req_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        conn = self.librarian._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO approvals (id, skill_name, query, status, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (req_id, skill_name, query, 'PENDING', timestamp))
            conn.commit()
            logger.info(f"Created approval request {req_id} for skill '{skill_name}'")
        except Exception as e:
            logger.error(f"Failed to create approval request: {e}")
            raise e
        finally:
            conn.close()
            
        return req_id

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Vraća sve aktivne zahtjeve na čekanju."""
        conn = self.librarian._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, skill_name, query, status, created_at 
            FROM approvals 
            WHERE status = 'PENDING'
            ORDER BY created_at ASC
        ''')
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": r[0],
                "skill_name": r[1],
                "query": r[2],
                "status": r[3],
                "created_at": r[4]
            }
            for r in rows
        ]

    def get_request(self, req_id: str) -> Optional[Dict[str, Any]]:
        """Dohvaća detalje određenog zahtjeva."""
        conn = self.librarian._get_sqlite_conn()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, skill_name, query, status, created_at, resolved_at 
            FROM approvals 
            WHERE id = ?
        ''', (req_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        return {
            "id": row[0],
            "skill_name": row[1],
            "query": row[2],
            "status": row[3],
            "created_at": row[4],
            "resolved_at": row[5]
        }

    def resolve_request(self, req_id: str, status: str) -> bool:
        """
        Odobrava ili odbija zahtjev.
        status može biti 'APPROVED' ili 'REJECTED'.
        """
        if status not in ['APPROVED', 'REJECTED']:
            logger.error(f"Invalid status for resolve: {status}")
            return False
            
        timestamp = datetime.now().isoformat()
        
        conn = self.librarian._get_sqlite_conn()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE approvals 
                SET status = ?, resolved_at = ? 
                WHERE id = ?
            ''', (status, timestamp, req_id))
            conn.commit()
            logger.info(f"Resolved request {req_id} as {status}")
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Failed to resolve request {req_id}: {e}")
            return False
        finally:
            conn.close()

    def wait_for_approval(self, req_id: str, timeout_sec: int = 60, poll_interval_sec: float = 0.5) -> bool:
        """
        Blokira izvođenje i periodički provjerava bazu podataka dok zahtjev ne bude odobren ili odbijen.
        Vraća True ako je odobreno, inače False (odbijeno ili timeout).
        """
        start_time = time.time()
        logger.info(f"Waiting for approval of request {req_id} (timeout: {timeout_sec}s)...")
        
        while time.time() - start_time < timeout_sec:
            req = self.get_request(req_id)
            if not req:
                logger.warning(f"Request {req_id} not found while waiting.")
                return False
                
            if req["status"] == "APPROVED":
                logger.info(f"Request {req_id} APPROVED by user.")
                return True
            elif req["status"] == "REJECTED":
                logger.info(f"Request {req_id} REJECTED by user.")
                return False
                
            time.sleep(poll_interval_sec)
            
        logger.warning(f"Approval request {req_id} TIMED OUT after {timeout_sec}s.")
        # Automatski odbijamo u slučaju timeouta iz sigurnosnih razloga
        self.resolve_request(req_id, "REJECTED")
        return False
