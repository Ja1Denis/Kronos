import os
import hashlib
from datetime import datetime
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Literal, Dict
from enum import Enum

@dataclass
class Pointer:
    file_path: str
    section: str
    line_range: Tuple[int, int]
    keywords: List[str]
    confidence: float
    last_modified: str
    content_hash: str  # SHA256
    indexed_at: str    # ISO timestamp

    def to_context(self) -> str:
        """Formatira za LLM."""
        lines = f"{self.line_range[0]}-{self.line_range[1]}"
        kw_str = ", ".join(self.keywords)
        return (f"📍 Reference: {self.file_path} (Lines: {lines})\n"
                f"   Section: {self.section}\n"
                f"   Keywords: {kw_str}\n"
                f"   Confidence: {self.confidence:.2f}")

    def to_dict(self) -> dict:
        """Serijalizacija za API."""
        return {
            "file_path": self.file_path,
            "section": self.section,
            "line_range": list(self.line_range),
            "keywords": self.keywords,
            "confidence": self.confidence,
            "last_modified": self.last_modified,
            "content_hash": self.content_hash,
            "indexed_at": self.indexed_at
        }

    def is_stale(self) -> bool:
        """Provjerava timestamp."""
        if not os.path.exists(self.file_path):
            return True
        current_mtime = os.path.getmtime(self.file_path)
        try:
            # Pretpostavljamo da je last_modified stringified float timestamp
            # ili ISO format.
            stored_mtime = float(self.last_modified)
            return current_mtime > (stored_mtime + 1.0) # Grace period of 1s
        except ValueError:
            try:
                stored_dt = datetime.fromisoformat(self.last_modified)
                return current_mtime > (stored_dt.timestamp() + 1.0)
            except Exception:
                return True

    def verify_content(self, current_content: str) -> bool:
        """Provjerava hash."""
        current_hash = hashlib.sha256(current_content.encode()).hexdigest()
        return current_hash == self.content_hash

class QueryType(Enum):
    """
    LOOKUP: 'What is X?', 'Where is Y?' - Traženje specifične informacije.
    AGGREGATION: 'List all X', 'Count Y' - Prikupljanje više informacija.
    SEMANTIC: Općeniti upiti o značenju ili arhitekturi.
    """
    LOOKUP = "lookup"
    AGGREGATION = "aggregation"
    SEMANTIC = "semantic"

@dataclass
class SearchResult:
    type: Literal["pointer", "chunk", "exact"]
    pointer: Optional[Pointer] = None
    content: Optional[str] = None
    metadata: Optional[Dict] = None
    score: float = 0.0
