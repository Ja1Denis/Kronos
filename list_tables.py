import sqlite3
import os

db_path = r'E:\G\GeminiCLI\ai-test-project\kronos\data\metadata.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables:", tables)

cursor.execute("SELECT * FROM knowledge_fts LIMIT 1;")
print("Example row from knowledge_fts:", cursor.fetchone())
conn.close()
