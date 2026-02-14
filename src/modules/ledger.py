import sqlite3
import time
import os
from dataclasses import dataclass
from typing import Dict, Any, List

@dataclass
class SavingsRecord:
    timestamp: float
    query: str
    model: str
    tokens_potential: int
    tokens_actual: int
    tokens_saved: int
    usd_saved: float

class SavingsLedger:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """Kreira tablicu ako ne postoji."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS savings_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL,
                    query TEXT,
                    model TEXT,
                    tokens_potential INTEGER,
                    tokens_actual INTEGER,
                    tokens_saved INTEGER,
                    usd_saved REAL
                )
            """)
            # Index za brže pretrage po vremenu
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON savings_log(timestamp)")
            conn.commit()

    def record_savings(self, query: str, model: str, potential: int, actual: int, usd_saved: float):
        """Bilježi novu transakciju uštede."""
        saved = max(0, potential - actual)
        timestamp = time.time()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO savings_log 
                (timestamp, query, model, tokens_potential, tokens_actual, tokens_saved, usd_saved)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (timestamp, query, model, potential, actual, saved, usd_saved))
            conn.commit()

    def get_summary(self, days: int = 30) -> Dict[str, Any]:
        """Vraća ukupnu statistiku za zadnjih N dana."""
        cutoff = time.time() - (days * 86400)
        
        with sqlite3.connect(self.db_path) as conn:
            # Ukupno
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_queries,
                    SUM(tokens_potential) as total_potential,
                    SUM(tokens_actual) as total_actual,
                    SUM(tokens_saved) as total_saved_tokens,
                    SUM(usd_saved) as total_usd
                FROM savings_log
            """)
            total_stats = cursor.fetchone()
            
            # Zadnjih N dana
            cursor = conn.execute("""
                SELECT 
                    SUM(tokens_saved) as recent_saved,
                    SUM(usd_saved) as recent_usd
                FROM savings_log
                WHERE timestamp > ?
            """, (cutoff,))
            recent_stats = cursor.fetchone()
            
            return {
                "total_queries": total_stats[0] or 0,
                "total_potential_tokens": total_stats[1] or 0,
                "total_actual_tokens": total_stats[2] or 0,
                "total_saved_tokens": total_stats[3] or 0,
                "total_usd_saved": total_stats[4] or 0.0,
                "recent_saved_tokens": recent_stats[0] or 0,
                "recent_usd_saved": recent_stats[1] or 0.0,
                "days_period": days
            }

    def get_recent_transactions(self, limit: int = 5) -> List[SavingsRecord]:
        """Vraća zadnjih N transakcija."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, query, model, tokens_potential, tokens_actual, tokens_saved, usd_saved 
                FROM savings_log 
                ORDER BY timestamp DESC LIMIT ?
            """, (limit,))
            
            return [SavingsRecord(*row) for row in cursor.fetchall()]
