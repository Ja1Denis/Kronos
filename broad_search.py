import sqlite3
import os

db_path = r'E:\G\GeminiCLI\ai-test-project\kronos\data\metadata.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

search_terms = ['Denis', '2. razred', 'opisZadataka']
print(f"--- Pretraživanje za {search_terms} ---")

for term in search_terms:
    query = "SELECT project, content, path FROM knowledge_fts WHERE content LIKE ? OR path LIKE ? LIMIT 5"
    cursor.execute(query, (f'%{term}%', f'%{term}%'))
    rows = cursor.fetchall()
    
    if rows:
        print(f"\n--- Rezultati za: {term} ---")
        for row in rows:
            project, content, file_path = row
            print(f"[CHUNK] Project: {project} | File: {os.path.basename(file_path)}")
            print(f"  Content: {content[:200]}...")
            print("-" * 10)

conn.close()
