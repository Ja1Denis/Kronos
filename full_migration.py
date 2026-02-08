import sqlite3
import os

db_path = 'data/metadata.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

def get_project(path):
    if not path: return "default"
    if "MatematikaPro" in path:
        return "matematikapro"
    elif "kronos" in path.lower():
        return "kronos"
    return "default"

print("1. Dodajem stupce ako nedostaju...")
for table in ["files", "entities"]:
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN project TEXT")
    except sqlite3.OperationalError:
        pass

print("2. Migriram 'files' i 'entities'...")
for table_name, path_col in [("files", "path"), ("entities", "file_path")]:
    cursor.execute(f"SELECT DISTINCT {path_col} FROM {table_name}")
    paths = cursor.fetchall()
    for (path,) in paths:
        cursor.execute(f"UPDATE {table_name} SET project = ? WHERE {path_col} = ?", (get_project(path), path))

print("3. Migriram 'knowledge_fts' (re-create)...")
cursor.execute("SELECT path, content, stemmed_content FROM knowledge_fts")
old_data = cursor.fetchall()

cursor.execute("DROP TABLE knowledge_fts")
cursor.execute('''
    CREATE VIRTUAL TABLE knowledge_fts USING fts5(
        path, project, content, stemmed_content
    )
''')

for path, content, stemmed in old_data:
    cursor.execute("INSERT INTO knowledge_fts (path, project, content, stemmed_content) VALUES (?, ?, ?, ?)",
                   (path, get_project(path), content, stemmed))

conn.commit()
conn.close()
print("Sve migracije završene uspješno!")
