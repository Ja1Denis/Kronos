---
description: Kako odgovarati koristeći Kronos MCP alat
---

Kad korisnik postavi pitanje koje zahtijeva pretragu baze znanja (@kronos):

1. **Pozovi alat**: Izvrši `kronos_query` s parametrima `query` i OBAVEZNO `client_model` (npr. "gemini-3-flash" ili onaj koji trenutno koristiš).
2. **Analiziraj izlaz**: Pročitaj cijeli izlaz alata (i ako je u `output.txt`).
3. **Formiraj odgovor**: Odgovori korisniku na temelju pronađenih podataka.
4. **Zalijepi izvještaj**: OBAVEZNO na sam kraj poruke zalijepi sekciju `### 🛡️ Kronos Efficiency Report` točno onako kako ju je alat vratio.
   - ⚠️ **VAŽNO:** Ako nisi pozvao alat u ovom koraku, **NE SMIJEŠ** ručno generirati ili kopirati ovaj izvještaj kako bi izbjegao lažne podatke. Koristi ga samo kada je autentičan.

// turbo-all
