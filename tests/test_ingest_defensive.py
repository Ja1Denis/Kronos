import pytest
from src.modules.oracle import Oracle

def test_metadata_validation_basics():
    oracle = Oracle(db_path="data/store_test")
    
    # Valid metadata
    assert oracle.validate_metadata({"source": "test.py", "start_line": 1, "end_line": 10}) is True
    
    # Missing source
    assert oracle.validate_metadata({"start_line": 1}) is False
    
    # Invalid line type
    assert oracle.validate_metadata({"source": "test.py", "start_line": "1"}) is False
    
    # None or empty
    assert oracle.validate_metadata(None) is False
    assert oracle.validate_metadata({}) is False

def test_safe_upsert_enrichment(tmp_path):
    # Mocking collection to avoid real DB if possible, or just use a test DB
    oracle = Oracle(db_path=str(tmp_path / "store"))
    
    docs = ["hello"]
    metas = [{"source": "test.md", "start_line": 1, "end_line": 1}]
    ids = ["id1"]
    
    oracle.safe_upsert(docs, metas, ids)
    
    # Verify result in Chroma
    res = oracle.collection.get(ids=["id1"])
    assert len(res["ids"]) == 1
    meta = res["metadatas"][0]
    assert "indexed_at" in meta
    assert "content_hash" in meta
    assert meta["source"] == "test.md"
