import sqlite3
import os

db_path = 'data/metadata.db'
if not os.path.exists(db_path):
    print(f"Error: {db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()
try:
    cursor.execute("SELECT content FROM knowledge_fts WHERE content LIKE '%Pitagor%' LIMIT 1")
    row = cursor.fetchone()
    if row:
        print(f"Found: {row[0][:200]}...")
    else:
        print("No results found in SQLite for 'Pitagor'")
except Exception as e:
    print(f"Error: {e}")
finally:
    conn.close()
