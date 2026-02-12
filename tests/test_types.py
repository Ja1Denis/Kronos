import pytest
import os
import hashlib
from datetime import datetime, timedelta
from src.modules.types import Pointer, QueryType, SearchResult

def test_pointer_serialization():
    # Test creation and to_context
    p = Pointer(
        file_path="test.md",
        section="Intro",
        line_range=(1, 10),
        keywords=["test", "unit"],
        confidence=0.95,
        last_modified=str(datetime.now().timestamp()),
        content_hash=hashlib.sha256(b"hello").hexdigest(),
        indexed_at=datetime.now().isoformat()
    )
    
    context = p.to_context()
    assert "test.md" in context
    assert "Intro" in context
    assert "1-10" in context
    assert "0.95" in context

    # Test verify_content
    assert p.verify_content("hello") is True
    assert p.verify_content("world") is False

def test_pointer_stale_logic(tmp_path):
    test_file = tmp_path / "stale_test.txt"
    test_file.write_text("content")
    
    mtime = os.path.getmtime(str(test_file))
    
    p = Pointer(
        file_path=str(test_file),
        section="Test",
        line_range=(1, 1),
        keywords=[],
        confidence=1.0,
        last_modified=str(mtime),
        content_hash="hash",
        indexed_at="now"
    )
    
    # Not stale yet
    assert p.is_stale() is False
    
    # Wait a bit and modify
    import time
    time.sleep(1.1)
    test_file.write_text("new content")
    
    # Should be stale now
    assert p.is_stale() is True

def test_search_result_types():
    p = Pointer(
        file_path="test.md",
        section="Intro",
        line_range=(1, 10),
        keywords=["test"],
        confidence=0.9,
        last_modified="0",
        content_hash="abc",
        indexed_at="now"
    )
    
    res_pointer = SearchResult(type="pointer", pointer=p)
    res_chunk = SearchResult(type="chunk", content="some content", metadata={"source": "abc"})
    
    assert res_pointer.type == "pointer"
    assert res_pointer.pointer.file_path == "test.md"
    assert res_chunk.type == "chunk"
    assert res_chunk.content == "some content"

def test_query_type_enum():
    assert QueryType.LOOKUP.value == "lookup"
    assert QueryType.AGGREGATION.value == "aggregation"
    assert QueryType.SEMANTIC.value == "semantic"
