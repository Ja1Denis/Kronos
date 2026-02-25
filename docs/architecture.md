# Arhitektura Sustava

## Baza Podataka
Odluka: Koristit ćemo SQLite za pohranu metapodataka zbog jednostavnosti i portabilnosti.
[2026-01-01 -> 2026-12-31]

## Agentic Pointers (Late Retrieval)
Kronos je prešao na "Late Retrieval" arhitekturu prilagođenu autonomnim LLM agentima.

**Ključni Koncepti:**
1. **Pointers By Default:** Umjesto da "zatrpava" LLM dugim isječcima koda, Oracle (Hybrid Search) za veliku većinu upita (Score < 0.85) prvo vraća strukturirani "Jelovnik" (Menu) koji sadrži samo metapodatke: `File Path`, `Sections` i izračunate `Matching Keywords`.
2. **Agent Autonomy:** Breme odlučivanja je na LLM Agentu. Agent pregledava dobivene Pointers. Ako ocijeni da je Pointer relevantan za rješavanje zadatka, agent samostalno koristi Misaoni Alat (`fetch_exact`).
3. **O(1) FastPath Retrieval:** Sam trenutak čitanja datoteke (Tool Call) izvršava se kroz iznimno brzi pristup kako bi se agentu odmah vratio potpuni kontekst samo za dijelove koji mu zaista i trebaju.

Ovakav pristup smanjuje potrošnju memorije, drastično čisti radni kontekst LLM-a (sprečava halucinacije zbog predugih logova) i ubrzava interakciju.
