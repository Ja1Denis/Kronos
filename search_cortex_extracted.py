import sqlite3
import os

db_path = 'data/metadata.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

search_term = 'cortex-search-extracted'
print(f"--- Pretraživanje za '{search_term}' ---")
query = "SELECT type, content, project, file_path FROM entities WHERE file_path LIKE ? ORDER BY rowid DESC LIMIT 30"
cursor.execute(query, (f'%{search_term}%',))

rows = cursor.fetchall()
if not rows:
    print(f"Nije pronađeno ništa za '{search_term}'.")
else:
    for row in rows:
        etype, content, project, file_path = row
        print(f"[{etype}] Project: {project} | File: {os.path.basename(file_path)}")
        print(f"  Content: {content[:200]}...")
        print("-" * 20)

conn.close()
