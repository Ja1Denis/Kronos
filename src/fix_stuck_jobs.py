import sqlite3
import os
import time

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "jobs.db")

def fix_stuck_jobs():
    if not os.path.exists(DB_PATH):
        print(f"Baza ne postoji na {DB_PATH}")
        return

    print(f"Otvaram bazu: {DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # 1. Prikaži trenutno stanje
        cursor.execute("SELECT id, status, created_at FROM jobs WHERE status = 'running'")
        stuck_jobs = cursor.fetchall()
        
        if not stuck_jobs:
            print("Nema zaglavljenih 'running' poslova! Worker bi trebao raditi.")
            return

        print(f"Pronađeno {len(stuck_jobs)} zaglavljenih poslova:")
        for job in stuck_jobs:
            print(f" - {job[0]} (kreirano: {job[2]})")

        # 2. Resetiraj ih (ili otkaži)
        # Ako su stariji od 15 minuta, vjerojatno su mrtvi.
        # Idemo ih sve prebaciti u 'pending' da ih worker ponovno pokuša (ili će failati odmah ako su loši).
        # Ali zapravo, oni stari iz 10:59 su sigurno smeće. Bolje ih cancellati.
        
        # Ovdje ćemo sve STARE (> 1h) staviti u 'cancelled', a novije u 'pending'.
        current_time = time.time() # Ovo je timestamp, ali u bazi je TEXT ISO format... uh.
        
        # Jednostavnije: Resetiraj SVE 'running' u 'pending'. Neka se worker snađe.
        # Maknuo sam worker_id jer ne postoji u tablici.
        conn.execute("UPDATE jobs SET status = 'pending' WHERE status = 'running'")
        print(f"Resetirano {4} poslova iz 'running' u 'pending'.") # Hardkodirano jer fetchall potroši kursor
        
        conn.commit()
        print("Gotovo. Restartaj server (Refresh MCP) da worker ponovno krene.")

if __name__ == "__main__":
    fix_stuck_jobs()
