# Specifikacija: Kronos Proof-of-Value (Token Savings) 💰

## Cilj
Pružiti korisniku jasan, mjerljiv i vizualan dokaz ekonomske isplativosti korištenja Kronos sustava u usporedbi s tradicionalnim RAG (Retrieval-Augmented Generation) pristupima.

## 1. Metodologija izračuna (Shadow Accounting)

Sustav će prilikom svakog upita (`kronos_query`) računati dva paralelna scenarija:

### A. Tradicionalni RAG (Potential)
- **Definicija:** Scenario u kojem se top `N` pronađenih isječaka (chunkova) šalje LLM-u u cijelosti.
- **Formula:** `Σ (token_cost svih pronađenih chunkova) + system_prompt_base`.
- **Pretpostavka:** Standardni RAG sustavi šalju prosječno 10-15k tokena po upitu za duboki kontekst koda.

### B. Kronos Smart Fetch (Actual)
- **Definicija:** Stvarni broj tokena poslan klijentu nakon optimizacije, dedup-a i pointerizacije.
- **Formula:** `ContextComposer.current_tokens`.

### C. Ušteda (Savings)
- `Efficiency % = (1 - Actual/Potential) * 100`
- `USD Saved = (Potential - Actual) * Price_per_Token` (npr. bazirano na Gemini 1.5 Flash cijenama).

## 2. Vizualna prezentacija: "Savings Footer"

Na kraju svakog odgovora, sustav će dodati formatirani Markdown blok:

```markdown
---
### 🛡️ Kronos Efficiency Report
- **Actual Input:** 420 tokens (Pointer Optimized)
- **Standard RAG:** 12,800 tokens (Full Context)
- **Savings:** **96.7% Token Reduction** 📉
- **ROI:** Ovaj upit vam je uštedio cca **$0.0017**.
---
```

## 3. Akumulirana statistika: "Financial Efficiency"

Nadogradnja `kronos_stats` alata s novim poljima:
- `total_tokens_saved_global`: Suma svih ušteda od instalacije.
- `total_dollars_saved`: Preračunata vrijednost u USD.
- `avg_efficiency_rate`: Prosječni postotak optimizacije.

## 4. Implementacijske faze

1.  **Phase 1 (Core):** Nadogradnja `ContextComposer` klase da prima `potential_tokens` varijablu.
2.  **Phase 2 (Telemetry):** Dodavanje SQLite tablice `savings_log` za perzistentno praćenje ušteda kroz vrijeme.
3.  **Phase 3 (MCP UI):** Integracija footera u `mcp_server.py`.
4.  **Phase 4 (Web):** (Opcionalno) `/dashboard` endpoint na FastAPI serveru.

---
*Status: Draft / Ready for Implementation*
