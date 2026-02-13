import os
import sys

# Ensure src is in path
sys.path.append(os.getcwd())

try:
    from src.modules.kronos_core import FastPath as RustFastPath
    print("Rust engine loaded.")
    engine = RustFastPath()
    
    # Try inserting some data
    engine.insert("Daj mi detalje o T034.", "Test data")
    print("Insert OK.")
    
    # Try searching
    print("Searching for 'T034'...")
    res = engine.search("T034")
    print(f"Search 'T034' result: {res}")
    
    print("Searching for 'Daj mi detalje o T034.'...")
    res = engine.search("Daj mi detalje o T034.")
    print(f"Search full result: {res}")
    
except Exception as e:
    print(f"ERROR: {e}")
except BaseException as e:
    print(f"CRITICAL ERROR (BaseException): {type(e)}")
