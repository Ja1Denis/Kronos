
import sqlite3
import json

conn = sqlite3.connect('data/metadata.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT type, content, file_path FROM entities WHERE content LIKE '%aiohttp%'")
rows = cursor.fetchall()

for row in rows:
    print(f"TYPE: {row['type']} | FILE: {row['file_path']}")
    print(f"CONTENT: {row['content']}")
    print("-" * 50)
conn.close()
