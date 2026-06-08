# Process: Agent Mode Protocol (Picard & OpenClaw style)

## 🎯 Cilj
Pretvoriti Picarda u proaktivnog agenta koji samostalno nadzire projekt i rješava zadatke asinkrono.

## 🔄 Operativni ciklus (Heartbeat)
Picard svakih nekoliko minuta izvršava sljedeće akcije:
1.  **Scanning:** Provjera `TASK_QUEUE.md` za nove zadatke.
2.  **Execution:** Ako postoji zadatak, Picard ga označava s `[/]` i kreće u rješavanje (Planning -> Execution).
3.  **Monitoring:** Provjera terminala i `TODO` komentara.
4.  **Reporting:** Ažuriranje `current_status.md` i javljanje korisniku ako je zadatak gotov.

## 📝 Komunikacijski kanali
- **Aktivni rad:** Unutar VS Code chata.
- **Asinkrono delegiranje:** Preko `TASK_QUEUE.md`.
- **Dugoročna memorija:** `kronos/docs/` (Architecture, Process, Decisions).

## 🛡️ Sigurnost
Picard nikada ne pokreće destruktivne naredbe bez izričitog odobrenja u `TASK_QUEUE.md` ili chatu.
