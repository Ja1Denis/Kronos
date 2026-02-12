import os
import sys
import subprocess

def get_projects(workspace_root):
    projects = []
    # Skip these directories
    skip_dirs = {
        '.git', '.agent', '.bg-codes', '.github', '.idea', '.vscode', 
        '__pycache__', 'venv', 'node_modules', 'bin', 'obj', 'logs', 
        'dist', 'build', 'coverage', 'tmp', 'temp'
    }
    
    print(f"Scanning for projects in: {workspace_root}")
    
    try:
        entries = os.listdir(workspace_root)
        for entry in entries:
            full_path = os.path.join(workspace_root, entry)
            
            if os.path.isdir(full_path):
                if entry in skip_dirs or entry.startswith('.'):
                    continue
                projects.append(entry)
    except Exception as e:
        print(f"Error scanning directory: {e}")
        
    return projects

def ingest_project(name, kronos_root, workspace_root):
    project_path = os.path.join(workspace_root, name)
    cli_path = os.path.join(kronos_root, "src", "cli.py")
    
    print(f"\n---------------------------------------------------------")
    print(f"🚀 Processing project: {name}")
    print(f"📂 Path: {project_path}")
    print(f"---------------------------------------------------------")
    
    # Set PYTHONPATH so src modules are visible
    env = os.environ.copy()
    env["PYTHONPATH"] = kronos_root

    cmd = [
        sys.executable, 
        cli_path, 
        "ingest", 
        project_path, 
        "--project", name, 
        "--recursive"
    ]
    
    try:
        # Run the command and wait for it to complete
        subprocess.run(cmd, env=env, check=True)
        print(f"✅ Successfully ingested: {name}")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error ingesting {name}: {e}")
    except Exception as e:
        print(f"❌ Unexpected error for {name}: {e}")

if __name__ == "__main__":
    # KRONOS_ROOT is where this script resides (e:\G\GeminiCLI\ai-test-project\kronos)
    KRONOS_ROOT = os.path.dirname(os.path.abspath(__file__))
    
    # WORKSPACE_ROOT is the parent directory (e:\G\GeminiCLI\ai-test-project)
    WORKSPACE_ROOT = os.path.dirname(KRONOS_ROOT)
    
    print(f"⏲️  Kronos Root: {KRONOS_ROOT}")
    print(f"🏠 Workspace Root: {WORKSPACE_ROOT}")
    
    # 0. WIPE DATABASE
    print("\n🧹 Wiping existing database for a clean start...")
    try:
        env = os.environ.copy()
        env["PYTHONPATH"] = KRONOS_ROOT
        subprocess.run([sys.executable, os.path.join(KRONOS_ROOT, "src", "cli.py"), "wipe", "--force"], env=env, check=True)
        print("✅ Database wiped.")
    except Exception as e:
        print(f"⚠️ Warning during wipe: {e}")

    projects = get_projects(WORKSPACE_ROOT)
    # Poredaj tako da 'kronos' bude prvi radi verifikacije encoding fix-a
    if 'kronos' in projects:
        projects.remove('kronos')
        projects.insert(0, 'kronos')
        
    print(f"📋 Found {len(projects)} projects: {', '.join(projects)}")
    
    for project in projects:
        ingest_project(project, KRONOS_ROOT, WORKSPACE_ROOT)
        
    print(f"\n🎉 All ingestion tasks completed!")
