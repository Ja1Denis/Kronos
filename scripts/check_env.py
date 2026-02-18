import sys
import os
import importlib.util

def check_package(package_name, import_name=None):
    if import_name is None:
        import_name = package_name
    
    try:
        if import_name == "mcp.server.fastmcp":
            from mcp.server.fastmcp import FastMCP
            print(f"✅ {package_name} is installed and working.")
            return True
        
        module = importlib.import_module(import_name)
        version = getattr(module, "__version__", "unknown")
        print(f"✅ {package_name} is installed (v{version}).")
        return True
    except ImportError:
        print(f"❌ {package_name} is NOT installed. (Module '{import_name}' not found)")
        return False
    except Exception as e:
        print(f"⚠️ {package_name} failed to import: {e}")
        return False

print(f"\n🔍 Checking Kronos Environment on Python {sys.version.split()[0]}...")
print(f"📂 Executable: {sys.executable}\n")

all_good = True

# Check critical dependencies
if not check_package("python-dotenv", "dotenv"): all_good = False
if not check_package("mcp", "mcp.server.fastmcp"): all_good = False
if not check_package("chromadb", "chromadb"): all_good = False
if not check_package("fastapi", "fastapi"): all_good = False
if not check_package("uvicorn", "uvicorn"): all_good = False
if not check_package("sentence-transformers", "sentence_transformers"): all_good = False

print("\n" + "-"*30)
if all_good:
    print("✅ Environment looks good! You can run Kronos.")
else:
    print("❌ Some dependencies are missing or broken.")
    print("👉 Run: pip install -r requirements.txt")
    print("👉 If using venv, ensure it is activated.")
print("-" * 30 + "\n")
