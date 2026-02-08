import os
import sys
import subprocess

# Putanja do Kronos root-a (gdje je cli.py)
KRONOS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKSPACE_ROOT = os.path.dirname(KRONOS_ROOT)

projects_to_ingest = [
    "CroStem",
    "CroStem_v012",
    "SerbStem",
    "Skills",
    "SlovStem",
    "WordpressPlugin",
    "WordpressPublisher",
    "cortex-api",
    "kronos"
]

def ingest_project(name):
    project_path = os.path.join(WORKSPACE_ROOT, name)
    if not os.path.exists(project_path):
        print(f"⚠️ Preskačem {name}, putanja ne postoji: {project_path}")
        return

    print(f"\n🚀 Ingesting project: {name}...")
    
    # Postavljamo PYTHONPATH kako bi src moduli bili vidljivi
    env = os.environ.copy()
    env["PYTHONPATH"] = KRONOS_ROOT

    cmd = [
        sys.executable, 
        os.path.join(KRONOS_ROOT, "src", "cli.py"), 
        "ingest", 
        project_path, 
        "--project", name, 
        "--recursive"
    ]
    
    try:
        subprocess.run(cmd, env=env, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ Greška pri ingestiji projekta {name}: {e}")

if __name__ == "__main__":
    print(f"📂 Kronos Root: {KRONOS_ROOT}")
    print(f"🏠 Workspace Root: {WORKSPACE_ROOT}")
    
    for proj in projects_to_ingest:
        ingest_project(proj)
    
    print("\n✅ Ingestija svih projekata završena!")
