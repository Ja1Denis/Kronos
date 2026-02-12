import pytest
import os
from src.utils.metadata_helper import is_safe_path, enforce_metadata_types, validate_line_range

def test_path_traversal_prevention():
    root = os.getcwd()
    
    # Malicious inputs
    assert is_safe_path("../../../etc/passwd", root) == False
    assert is_safe_path("/etc/passwd", root) == False
    assert is_safe_path("C:\\Windows\\System32\\config\\SAM", root) == False
    assert is_safe_path("file\x00.md", root) == False
    assert is_safe_path("file\n.md", root) == False
    
    # Valid inputs
    assert is_safe_path("README.md", root) == True
    assert is_safe_path("./src/main.py", root) == True
    
    # Symlink mock (teško bez pravih symlinkova, ali logika pokriva realpath)
    # realpath rješava symlinkove na stvarni path, pa ako on vodi van, startswith će failati.

def test_metadata_type_enforcement():
    # Invalid types
    assert enforce_metadata_types(None) == None
    assert enforce_metadata_types("string") == None
    assert enforce_metadata_types([]) == None
    
    # Missing/invalid source
    assert enforce_metadata_types({}) == None
    assert enforce_metadata_types({'source': None}) == None
    assert enforce_metadata_types({'source': 123}) == None
    assert enforce_metadata_types({'source': ''}) == None
    assert enforce_metadata_types({'source': '   '}) == None
    
    # Invalid lines
    assert enforce_metadata_types({'source': 'README.md', 'start_line': -5}) == None
    assert enforce_metadata_types({'source': 'README.md', 'start_line': 1, 'end_line': 0}) == None
    assert enforce_metadata_types({'source': 'README.md', 'start_line': '1'}) == None
    
    # Unsafe path in metadata
    assert enforce_metadata_types({'source': '/etc/passwd'}) == None
    
    # Valid
    meta = {'source': 'README.md', 'start_line': 1, 'end_line': 10}
    assert enforce_metadata_types(meta) == meta

def test_line_range_validation():
    # Create a small temp file for testing
    test_file = "temp_test_lines.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Line 1\nLine 2\nLine 3\nLine 4\nLine 5\n")
        
    try:
        # Invalid start
        valid, err = validate_line_range(-1, 5, test_file)
        assert valid == False
        
        # End < Start
        valid, err = validate_line_range(5, 4, test_file)
        assert valid == False
        
        # Empty range
        valid, err = validate_line_range(5, 5, test_file)
        assert valid == False
        
        # Empty range (Start == End is allowed if it's 1 line, wait, usually end is inclusive)
        # In our case, end_line 1 to start_line 1 is 1 line.
        # But user spec says "end > start" for "no empty ranges".
        # Let's check my implementation: if end < start it fails.
        # User said: start=5, end=5 -> Invalid.
        
        # Huge range
        valid, err = validate_line_range(1, 20000, test_file)
        assert valid == False
        assert "Range too large" in err
        
        # Exceeds file length
        valid, err = validate_line_range(1, 10, test_file)
        assert valid == False
        assert "exceeds file length" in err
        
        # Valid
        valid, err = validate_line_range(1, 3, test_file)
        assert valid == True
        
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

def test_malicious_inputs_dont_crash():
    from src.utils.file_helper import read_file_safe
    
    MALICIOUS_INPUTS = [
        # Path traversal
        {"file_path": "../../../etc/passwd", "start_line": 1, "end_line": 10},
        {"file_path": "..\\..\\..\\Windows\\System32\\config\\SAM", "start_line": 1, "end_line": 10},
        
        # Null bytes
        {"file_path": "file\x00.txt", "start_line": 1, "end_line": 10},
        
        # Huge ranges
        {"file_path": "valid.txt", "start_line": 1, "end_line": 999999999},
        
        # Negative indices
        {"file_path": "valid.txt", "start_line": -100, "end_line": 10},
        
        # Invalid types
        {"file_path": None, "start_line": 1, "end_line": 10},
        {"file_path": 12345, "start_line": 1, "end_line": 10},
        {"file_path": ["array"], "start_line": 1, "end_line": 10},
        
        # Empty/whitespace
        {"file_path": "", "start_line": 1, "end_line": 10},
        {"file_path": "   ", "start_line": 1, "end_line": 10},
    ]
    
    for inputs in MALICIOUS_INPUTS:
        try:
            result = read_file_safe(inputs["file_path"], inputs["start_line"], inputs["end_line"])
            # Should return error dictionary, not crash
            assert isinstance(result, dict)
            assert "error" in result
            print(f"✅ Handled malicious input: {inputs['file_path']}")
        except Exception as e:
            pytest.fail(f"❌ CRASHED on input: {inputs}\nError: {e}")

def test_croatian_characters():
    from src.utils.file_helper import read_file_safe
    # Create test file with Croatian text
    test_content = """
    Ovo je test sa hrvatskim znakovima.
    Češće ćemo čitati čudne riječi.
    Džabe što šalješ poruke.
    """
    test_file = "test_croatian.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)
    
    try:
        # Test reading
        result = read_file_safe(test_file, 1, 4)
        
        assert "error" not in result
        content = result["content"]
        assert "č" in content
        assert "ć" in content
        assert "š" in content
        # assert "đ" in content # Word 'Džabe' has dž, 'znakovima' has no đ, but let's check č/ć
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

def test_concurrent_file_reads():
    """Test 50 simultaneous reads of same file"""
    from src.utils.file_helper import read_file_safe
    from concurrent.futures import ThreadPoolExecutor
    
    test_file = "test_concurrent.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("Line 1\n" * 100)
        
    try:
        def read_file_task(i):
            return read_file_safe(test_file, 1, 10)
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(read_file_task, i) for i in range(50)]
            results = [f.result() for f in futures]
        
        # All should succeed
        errors = [r for r in results if "error" in r]
        assert len(errors) == 0, f"Failed {len(errors)}/50 concurrent reads: {errors}"
    finally:
        if os.path.exists(test_file):
            os.remove(test_file)

if __name__ == "__main__":
    pytest.main([__file__])
