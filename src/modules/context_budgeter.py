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
    metadata: Dict[str, Any] = field(default_factory=dict)

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
    def __init__(self, config: BudgetConfig = BudgetConfig(), model_name: str = "gemini-3-flash"):
        self.config = config
        self.items: List[ContextItem] = []
        self.audit_log: List[str] = []
        self.model_name = model_name.lower()
        
        # Pricing mapping (USD per 1M tokens) - 2026 estimates
        self.pricing = {
            "gemini-3-flash": 0.10,
            "gemini-3-pro": 1.25,
            "gemini-2-flash": 0.15,
            "claude-3.5-sonnet": 3.00,
            "claude-3-opus": 15.00,
            "gpt-4o": 5.00,
            "default": 0.15
        }
        
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
        
        # Savings Metrics
        self.potential_tokens = 0 # What a "dumb" RAG would send

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
        # Calculate potential tokens (Full RAG estimate)
        # We assume full RAG doesn't trim and doesn't pointerize.
        self.potential_tokens = sum(item.token_cost for item in self.items)

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
            elif item.kind == "pointer": item.utility_score = 0.7 
            elif item.kind == "recent_changes" and item.utility_score <= 0.5: item.utility_score = 0.6
        
        # Pass-based sorting
        pass1_kinds = ["cursor", "briefing", "entity", "pointer"]
        pass1_items = [i for i in self.items if i.kind in pass1_kinds]
        pass2_items = [i for i in self.items if i.kind not in pass1_kinds]
        
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
                 self._log_rejection(item, "global_budget_exceeded")
                 continue

            # 2.3 File Caps
            if item.kind in ["chunk", "evidence", "recent_changes"]:
                file_chunks = self.file_chunk_counts.get(item.source, 0)
                file_tokens = self.file_token_counts.get(item.source, 0)
                
                current_file_max_chunks = self.config.file_max_chunks
                current_file_max_tokens = self.config.file_max_tokens
                
                source_lower = item.source.lower()
                if any(x in source_lower for x in ["docs", "specs", "requirements", "tasks.md"]):
                    current_file_max_chunks = 10
                    current_file_max_tokens = 3000
                
                if file_chunks >= current_file_max_chunks:
                    self._log_rejection(item, f"file_chunk_cap ({current_file_max_chunks})")
                    continue
                
                if file_tokens + item.token_cost > current_file_max_tokens:
                    self._log_rejection(item, f"file_token_cap ({current_file_max_tokens})")
                    continue

            # 2.4 Category Caps
            cat_limit = None
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
            self.audit_log.append(f"ADD [{item.kind}] {item.source[:30]}: +{item.token_cost} tokens")
            
            if item.kind in ["chunk", "evidence", "recent_changes"]:
                self.file_chunk_counts[item.source] = self.file_chunk_counts.get(item.source, 0) + 1
                self.file_token_counts[item.source] = self.file_token_counts.get(item.source, 0) + item.token_cost
            
            final_context.append(item)

        # 3. Final Render
        render_order = {"briefing": 0, "cursor": 1, "entity": 2, "recent_changes": 3, "pointer": 4, "chunk": 5, "evidence": 6}
        final_context.sort(key=lambda x: render_order.get(x.kind, 99))
        
        output_str = ""
        for item in final_context:
            output_str += item.render() + "\n\n"
            
        return output_str.strip()

    def get_efficiency_report(self) -> str:
        """Generira vizualni izvještaj o uštedi tokena."""
        actual = self.current_tokens
        saved = max(0, self.potential_tokens - actual)
        efficiency = (saved / self.potential_tokens * 100) if self.potential_tokens > 0 else 0
        
        # Dinamička procijenu cijene bazirana na modelu
        price_per_m = self.pricing.get(self.model_name, self.pricing["default"])
        usd_saved = (saved / 1_000_000) * price_per_m
        
        report = "\n---\n"
        report += f"### 🛡️ Kronos Efficiency Report ({self.model_name.upper()} Optimized)\n"
        report += f"- **Actual Input:** {actual:,} tokens\n"
        report += f"- **Raw RAG Context:** {self.potential_tokens:,} tokens\n"
        report += f"- **Savings:** **{efficiency:.1f}% Token Reduction** 📉\n"
        if saved > 0:
            report += f"- **Estimated ROI:** Uštedjeli ste cca **${usd_saved:.6f}**.\n"
        report += "---\n"
        return report

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
