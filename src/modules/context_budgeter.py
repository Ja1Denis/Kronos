import hashlib
from dataclasses import dataclass, field
from typing import List, Literal, Optional, Dict, Set, Any
import logging

# Simple logger setup
logger = logging.getLogger(__name__)

@dataclass
class BudgetConfig:
    global_limit: int = 4000
    briefing_limit: int = 300
    entities_limit: int = 800
    chunks_limit: int = 3200
    recent_changes_limit: int = 250
    
    # File Caps
    file_max_chunks: int = 3
    file_max_tokens: int = 900
    min_unique_files: int = 4
    
    # Chunk Caps
    chunk_hard_cap: int = 600  # Trim if larger than this
    chunk_fat_threshold: int = 900 # Never raw, only excerpt (though hard cap handles this mostly)

    @staticmethod
    def from_profile(name: str):
        """Returns a predefined budget configuration."""
        if name == "light":
            return BudgetConfig(
                global_limit=2000,
                briefing_limit=200,
                entities_limit=400,
                chunks_limit=1400,
                file_max_chunks=2,
                file_max_tokens=600
            )
        elif name == "extra": # Za velike code refaktore
            return BudgetConfig(
                global_limit=8000,
                briefing_limit=500,
                entities_limit=1500,
                chunks_limit=5000,
                recent_changes_limit=500,
                file_max_chunks=5,
                file_max_tokens=2000
            )
        else: # Normal / Default
            return BudgetConfig()

@dataclass
class ContextItem:
    content: str
    kind: Literal["cursor", "entity", "chunk", "evidence", "briefing", "recent_changes", "pointer"]
    source: str
    utility_score: float = 0.5
    token_cost: int = 0
    dedup_key: str = ""

    def __post_init__(self):
        if not self.token_cost:
            self.token_cost = self.estimate_tokens(self.content)
        self._generate_dedup_key()
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        VAŽNO: Prevents budget overflow s robusnom procjenom.
        """
        # DEFENSE 1: Handle None/non-string
        if text is None:
            return 0
        if not isinstance(text, str):
            text = str(text)
        
        # DEFENSE 2: Handle empty string
        if len(text.strip()) == 0:
            return 0
        
        # Main estimation logic (rough estimate: chars / 4)
        estimated = len(text) / 4
        
        # DEFENSE 3: Safety margin (20% overhead)
        estimated *= 1.2
        
        # DEFENSE 4: Cap at maximum (prevent overflow/DoS)
        MAX_TOKENS_PER_ITEM = 100000
        if estimated > MAX_TOKENS_PER_ITEM:
            logger.warning(f"Token estimate exceeds max: {estimated}")
            estimated = MAX_TOKENS_PER_ITEM
            
        # DEFENSE 5: Floor at minimum for non-empty string
        return max(1, int(estimated))

    def _generate_dedup_key(self):
        # Create hash of content (normalized) + source
        # We normalize whitespace to catch near-duplicates
        norm_content = " ".join(self.content.split())
        self.dedup_key = hashlib.md5((norm_content + self.source).encode()).hexdigest()

    def __post_init_checks__(self): # Not used but good to have logic
        if not self.dedup_key:
            self._generate_dedup_key()

    def render(self) -> str:
        """Returns the formatted string for the LLM."""
        if self.kind == "entity":
            # Entity Format: One-liners (1-2 linije sažetka)
            # Take first 2 lines or first 200 chars
            lines = self.content.strip().split('\n')
            summary = " ".join(lines[:2])
            if len(summary) > 200:
                summary = summary[:197] + "..."
            return f"- [{self.kind.upper()}] {summary} (Source: {self.source})"
        
        elif self.kind == "cursor":
            return f"--- CURSOR CONTEXT ({self.source}) ---\n{self.content}\n--- END CURSOR ---"
        
        elif self.kind == "briefing":
             return f"--- BRIEFING ---\n{self.content}\n"

        elif self.kind == "pointer":
            return f"--- POINTER ({self.source}) ---\n{self.content}"
            
        else:
            return f"--- {self.kind.upper()} ({self.source}) ---\n{self.content}"

class ContextComposer:
    def __init__(self, config: BudgetConfig = BudgetConfig()):
        self.config = config
        self.items: List[ContextItem] = []
        self.audit_log: List[str] = []
        
        # State tracking during composition
        self.current_tokens = 0
        self.category_tokens: Dict[str, int] = {
            "cursor": 0, "entity": 0, "chunk": 0, 
            "evidence": 0, "briefing": 0, "recent_changes": 0,
            "pointer": 0
        }
        self.file_chunk_counts: Dict[str, int] = {}
        self.file_token_counts: Dict[str, int] = {}
        self.seen_keys: Set[str] = set()
        self.audit_log: List[str] = []

    def add_item(self, item: ContextItem):
        self.items.append(item)

    def _log_rejection(self, item: ContextItem, reason: str):
        msg = f"REJECTED [{item.kind}] {item.source[:30]}... ({item.token_cost} tok): {reason}"
        self.audit_log.append(msg)
        # print(msg) # Optional debug

    def compose(self) -> str:
        """
        Main algorithm (Greedy Assembly).
        """
        # Reset state
        self.current_tokens = 0
        self.category_tokens = {k: 0 for k in self.category_tokens}
        self.file_chunk_counts = {}
        self.file_token_counts = {}
        self.seen_keys = set()
        self.audit_log = []
        
        final_context = []

        # 1. Pre-processing & Sorting
        # Priority mapping:
        # Cursor: 1.0 (Always) -> Handled by separate logic usually, but here we treat it as top priority
        # Entities: 0.9
        # Chunks: 0.5 - 0.8 (based on utility score)
        # Recent Diffs: 0.6
        
        # 1. Pre-processing
        for item in self.items:
            # Apply "Fat Chunk Rule" - hard trimming
            if item.kind == "chunk" and item.token_cost > self.config.chunk_hard_cap:
                limit_chars = self.config.chunk_hard_cap * 4
                item.content = item.content[:limit_chars] + "...[TRIMMED]"
                item.token_cost = self.config.chunk_hard_cap
            
            # Ensure base priorities
            if item.kind == "cursor": item.utility_score = 10.0
            elif item.kind == "briefing": item.utility_score = 9.0
            elif item.kind == "entity" and item.utility_score <= 0.5: item.utility_score = 0.8
            elif item.kind == "pointer": item.utility_score = 0.7 # High priority for pointers
            elif item.kind == "recent_changes" and item.utility_score <= 0.5: item.utility_score = 0.6
        
        # Pass-based sorting:
        # Pass 1: Mandatory/Small items (Cursor, Briefing, Entity, Pointer)
        # Pass 2: Large items (Chunk, Evidence, Recent Changes)
        pass1_kinds = ["cursor", "briefing", "entity", "pointer"]
        pass1_items = [i for i in self.items if i.kind in pass1_kinds]
        pass2_items = [i for i in self.items if i.kind not in pass1_kinds]
        
        # Sort both by utility
        pass1_items.sort(key=lambda x: x.utility_score, reverse=True)
        pass2_items.sort(key=lambda x: x.utility_score, reverse=True)
        
        # 2. Greedy Fill
        for item in pass1_items + pass2_items:
            # 2.1 check Deduplication
            if item.dedup_key in self.seen_keys:
                self._log_rejection(item, "duplicate")
                continue

            # 2.2 Global Budget Check
            if self.current_tokens + item.token_cost > self.config.global_limit:
                # SPECIAL: If a CHUNK doesn't fit, can we try to add it as a POINTER?
                if item.kind == "chunk":
                     # Create a virtual pointer (simulated)
                     # In a real scenario, Oracle provides the pointer, but here we can at least log it
                     self._log_rejection(item, "global_budget_exceeded (Considered for downgrade)")
                else:
                     self._log_rejection(item, "global_budget_exceeded")
                continue

            # 2.3 File Caps (only for chunks/evidence/recent)
            if item.kind in ["chunk", "evidence", "recent_changes"]:
                file_chunks = self.file_chunk_counts.get(item.source, 0)
                file_tokens = self.file_token_counts.get(item.source, 0)
                
                # Dynamic File Cap: Allow more chunks for documentation and specs
                current_file_max_chunks = self.config.file_max_chunks
                current_file_max_tokens = self.config.file_max_tokens
                
                source_lower = item.source.lower()
                if any(x in source_lower for x in ["docs", "specs", "requirements", "tasks.md"]):
                    current_file_max_chunks = 10  # Deep memory for our own docs
                    current_file_max_tokens = 3000 # Allow more tokens for docs
                
                if file_chunks >= current_file_max_chunks:
                    self._log_rejection(item, f"file_chunk_cap ({current_file_max_chunks})")
                    continue
                
                if file_tokens + item.token_cost > current_file_max_tokens:
                    self._log_rejection(item, f"file_token_cap ({current_file_max_tokens})")
                    continue

            # 2.4 Category Caps
            cat_limit = getattr(self.config, f"{item.kind}_limit", None)
            # Note: "cursor" usually doesn't have a limit in config, or we trust it fits if global fits
            # "entities" -> entities_limit
            # "chunk" -> chunks_limit
            
            # Map plural names in config to singular kind
            if item.kind == "chunk": cat_limit = self.config.chunks_limit
            elif item.kind == "entity": cat_limit = self.config.entities_limit
            
            if cat_limit is not None:
                if self.category_tokens[item.kind] + item.token_cost > cat_limit:
                    self._log_rejection(item, f"{item.kind}_limit_exceeded")
                    continue

            # ACCEPT ITEM
            self.seen_keys.add(item.dedup_key)
            self.current_tokens += item.token_cost
            self.category_tokens[item.kind] = self.category_tokens.get(item.kind, 0) + item.token_cost
            self.audit_log.append(f"ADD [{item.kind}] {item.source[:30]}: +{item.token_cost} tokens (total: {self.current_tokens})")
            
            # POST-CHECK: Verify budget not exceeded (paranoid check)
            assert self.current_tokens <= self.config.global_limit, f"BUG: Budget exceeded! {self.current_tokens} > {self.config.global_limit}"

            if item.kind in ["chunk", "evidence", "recent_changes"]:
                self.file_chunk_counts[item.source] = self.file_chunk_counts.get(item.source, 0) + 1
                self.file_token_counts[item.source] = self.file_token_counts.get(item.source, 0) + item.token_cost
            
            final_context.append(item)

        # 3. Final Render (Sort by kind for structure: Briefing -> Entities -> Chunks)
        # Define render order
        render_order = {"briefing": 0, "cursor": 1, "entity": 2, "recent_changes": 3, "pointer": 4, "chunk": 5, "evidence": 6}
        
        final_context.sort(key=lambda x: render_order.get(x.kind, 99))
        
        output_str = ""
        for item in final_context:
            output_str += item.render() + "\n\n"
            
        return output_str.strip()

    def get_audit_report(self) -> str:
        report = "=== CONTEXT COMPOSER AUDIT ===\n"
        report += f"Total Tokens: {self.current_tokens} / {self.config.global_limit}\n"
        report += "Category Breakdown:\n"
        for cat, tokens in self.category_tokens.items():
            report += f"  - {cat}: {tokens}\n"
        
        report += "\nRejections:\n"
        for log in self.audit_log:
            report += f"  - {log}\n"
        return report
