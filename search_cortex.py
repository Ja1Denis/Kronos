import sqlite3
import os

db_path = 'data/metadata.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Pretraživanje za 'cortex' ---")
query = "SELECT type, content, project, file_path FROM entities WHERE content LIKE ? OR project LIKE ? OR file_path LIKE ? ORDER BY rowid DESC LIMIT 30"
cursor.execute(query, ('%cortex%', '%cortex%', '%cortex%'))

rows = cursor.fetchall()
if not rows:
    print("Nije pronađeno ništa za 'cortex'.")
else:
    for row in rows:
        etype, content, project, file_path = row
        print(f"[{etype}] Project: {project} | File: {os.path.basename(file_path)}")
        print(f"  Content: {content[:200]}...")
        print("-" * 20)

conn.close()
