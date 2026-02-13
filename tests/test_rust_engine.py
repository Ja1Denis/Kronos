import pytest
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def test_rust_fastpath_import():
    """Test da li se FastPath može uvesti (Rust/PyO3)"""
    try:
        from src.modules.fast_path import FastPath
        from src.modules.librarian import Librarian
        lib = Librarian()
        fp = FastPath(lib)
        assert fp is not None
        print("✅ FastPath import successful")
    except ImportError as e:
        pytest.fail(f"FastPath import failed: {e}")
    except Exception as e:
        pytest.fail(f"FastPath initialization failed: {e}")

def test_rust_engine_search():
    """Test pretrage u FastPath-u (ako je inicijaliziran)"""
    from src.modules.fast_path import FastPath
    from src.modules.librarian import Librarian
    lib = Librarian()
    fp = FastPath(lib)
    
    # Warmup da napunimo indekse
    fp.warmup()
    
    # Pokušaj naći nešto što bi trebalo biti u bazi (npr. 'kronos')
    res = fp.search("kronos")
    assert isinstance(res, dict)
    assert "type" in res
    print(f"✅ FastPath search result for 'kronos': {res['type']} - Confidence: {res['confidence']}")
