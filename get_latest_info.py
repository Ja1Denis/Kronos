import sqlite3
import os

db_path = 'data/metadata.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("--- Zadnjih 10 Zadataka (Tasks) ---")
cursor.execute("SELECT content, file_path FROM entities WHERE type='task' ORDER BY rowid DESC LIMIT 10")
for row in cursor.fetchall():
    print(f"- {row[0]} (Iz: {os.path.basename(row[1])})")

print("\n--- Zadnjih 5 Odluka (Decisions) ---")
cursor.execute("SELECT content, file_path FROM entities WHERE type='decision' ORDER BY rowid DESC LIMIT 5")
for row in cursor.fetchall():
    print(f"- {row[0]} (Iz: {os.path.basename(row[1])})")

conn.close()
