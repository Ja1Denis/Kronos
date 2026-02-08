import sqlite3
import os

db_path = 'data/metadata.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def migrate_table(table_name, path_col):
    print(f"Migriram tablicu {table_name}...")
    cursor.execute(f"SELECT DISTINCT {path_col} FROM {table_name} WHERE project IS NULL")
    paths = cursor.fetchall()
    
    for (path,) in paths:
        if not path: continue
        project = "default"
        if "MatematikaPro" in path:
            project = "matematikapro"
        elif "kronos" in path.lower():
            project = "kronos"
        
        cursor.execute(f"UPDATE {table_name} SET project = ? WHERE {path_col} = ?", (project, path))
    conn.commit()

migrate_table("files", "path")
migrate_table("entities", "file_path")
# FTS5 virtual table needs a different approach or just re-ingest.
# But for now, let's at least fix SQLite tables.

conn.close()
print("Migracija završena.")
