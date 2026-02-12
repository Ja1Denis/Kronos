import pytest
from src.modules.oracle import Oracle, QueryType
from src.modules.types import Pointer
from src.modules.context_budgeter import ContextComposer, ContextItem, BudgetConfig

def test_response_builders_and_tokens():
    oracle = Oracle()
    
    # Test Pointers
    p1 = Pointer(
        file_path="test.py", 
        section="test", 
        line_range=(1, 10), 
        keywords=["test"],
        confidence=0.9,
        last_modified="0",
        content_hash="abc",
        indexed_at="2026-01-01"
    )
    p2 = Pointer(
        file_path="other.py", 
        section="other", 
        line_range=(20, 30), 
        keywords=["other"],
        confidence=0.8,
        last_modified="0",
        content_hash="def",
        indexed_at="2026-01-01"
    )
    
    resp = oracle.build_pointer_response([p1, p2])
    assert resp["type"] == "pointer_response"
    assert resp["estimated_tokens"] > 0
    assert len(resp["pointers"]) == 2
    print(f"✅ Pointer response tokens: {resp['estimated_tokens']}")

    # Test Mixed
    chunk = {"content": "This is a full chunk of text.", "metadata": {"source": "doc.md"}, "score": 0.95}
    resp = oracle.build_mixed_response([chunk], [p1])
    assert resp["type"] == "mixed_response"
    assert resp["estimated_tokens"] > 10 # Some tokens must exist
    print(f"✅ Mixed response tokens: {resp['estimated_tokens']}")

def test_composer_priority_and_passes():
    config = BudgetConfig(global_limit=50) # Budget dovoljno za pointere (10), premal za big chunk (120)
    composer = ContextComposer(config)
    
    # Dodajemo veliki chunk koji bi sam pojeo budget (400 chars -> ~120 tokens s marginom)
    big_chunk = ContextItem(content="X" * 400, kind="chunk", source="big.py", utility_score=0.5) 
    
    # Dodajemo pointere s RAZLIČITIM sadržajem da izbjegnemo deduplikaciju
    p1 = ContextItem(content="Pointer ONE content", kind="pointer", source="p1.py", utility_score=0.7)
    p2 = ContextItem(content="Pointer TWO content", kind="pointer", source="p2.py", utility_score=0.7)
    
    print(f"DEBUG Costs: p1={p1.token_cost}, p2={p2.token_cost}, big={big_chunk.token_cost}")
    
    composer.add_item(big_chunk)
    composer.add_item(p1)
    composer.add_item(p2)
    
    context = composer.compose()
    audit = composer.get_audit_report()
    
    print(f"\n--- DEBUG AUDIT ---\n{audit}\n--- END AUDIT ---")
    print(f"\n--- DEBUG CONTEXT ---\n{context}\n--- END DEBUG ---")
    
    # Provjera: Pointers bi morali ući PRVI jer su u Pass 1, a Chunk bi trebao biti REJECTED
    assert "p1.py" in context
    assert "p2.py" in context
    assert "big.py" not in context
    assert "global_budget_exceeded" in audit or "Considered for downgrade" in audit
    print("✅ Composer 2-pass priority test passed.")

def test_fetch_exact_logic():
    from src.utils.file_helper import read_file_safe
    # Test safe path rejection
    res = read_file_safe("/etc/passwd", 1, 10)
    assert res["error"] == "invalid_path"
    
    # Test invalid range
    res = read_file_safe("README.md", 100, 10) # start > end
    assert res["error"] == "invalid_range"
