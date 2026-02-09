import sqlite3
import os

db_path = 'data/metadata.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

search_terms = ['activation', 'T100', 'stali', 'gdje', 'status']
print(f"--- Pretraživanje za {search_terms} ---")

for term in search_terms:
    query = "SELECT type, content, project, file_path FROM entities WHERE content LIKE ? OR file_path LIKE ? ORDER BY rowid DESC LIMIT 5"
    cursor.execute(query, (f'%{term}%', f'%{term}%'))
    rows = cursor.fetchall()
    
    if rows:
        print(f"\n--- Rezultati za: {term} ---")
        for row in rows:
            etype, content, project, file_path = row
            print(f"[{etype}] Project: {project} | File: {os.path.basename(file_path)}")
            print(f"  Content: {content[:200]}...")
            print("-" * 10)

conn.close()
