Uzmimo “1 pametnu stvar” koju konkurenti rijetko isporuče kao gotov feature, a ti možeš: debugging‑specifičan retrieval paket (logs/traces/diffs + code), s jasnim scoringom i fallbackom. To je vrlo izvedivo i odmah daje wow‑efekt u IDE‑u, jer debugging nije “semantic search”, nego “nađi dokaz i mjesto gdje pukne”.
​

Feature: Debug Repro Pack (MVP)
Što korisnik vidi
U IDE-u napišeš:

“Zašto test test_login_expired_token baca 500?”

Kronos vrati JSON koji LLM može direktno pojesti:

json
{
  "task": "debug",
  "hypothesis_targets": [
    {"file":"auth/middleware.py","line_start":21,"line_end":88,"why":"Stack frame + recent change"},
    {"file":"auth/jwt.py","line_start":40,"line_end":120,"why":"Exception message match"}
  ],
  "evidence": {
    "stack_trace": ["..."],
    "failing_test": "tests/test_auth.py::test_login_expired_token",
    "recent_diffs": ["commit abc123 touched auth/jwt.py, auth/middleware.py"],
    "logs": ["[ERROR] JWTExpired ..."]
  },
  "snippets": [
    {"file":"auth/jwt.py","line_start":40,"line_end":120,"text":"..."},
    {"file":"auth/middleware.py","line_start":21,"line_end":88,"text":"..."}
  ]
}
LLM dobije: (a) gdje pukne, (b) što se mijenjalo, (c) relevantan kod, (d) repro info. To je “repro harness + code to fix”, što se u praksi preporučuje za debug‑orijentirani RAG.

Kako to implementiraš bez velikog rizika
Korak 1: Detektiraj da je upit “debug”
Rule-based: ako upit ima “error/exception/trace/500/test fails/zašto puca” ili IDE šalje stack trace/test name → debug mode. (Ovo je najlakši dio.)

Korak 2: Normaliziraj stack trace u “signature”
Iz stack trace-a izvuci:

file paths + line numbers + function names (frameovi)

exception class + message (kao tekst)

Ne treba embeddings za ovo: prvo radi symbolic/lexical match po pathovima i simbolima (to je preporuka i u debug RAG pristupima).
​

Korak 3: Kandidati za retrieval (3 korpusa)
Code snippets (funkcije oko frameova + njihovi neposredni calleri ako možeš)

Recent diffs (zadnjih N commitova ili watcher eventovi: “touched files/symbols”)

Logs/test output (ako imaš lokalne logove, ili barem test failure output)

Debug RAG blueprintovi eksplicitno kažu: prioritet su artefakti koji nose dokaz (stack traces, failing test output, diffs).
​

Korak 4: Scoring (jednostavno, ali pametno)
Za svaki candidate snippet izračunaj score kao zbroj:

Path overlap: koliko se poklapa putanja s frameovima

Symbol overlap: poklapanje imena funkcija/klasa iz trace-a

Recency boost: ako je file nedavno mijenjan (watcher)

BM25/FTS na exception message (sekundarno)

Embedding cosine (tek kao rerank, opcionalno)

Ovo je praktično identično “pragmatičnom scoring receptu” za debug RAG: hard signals prvo, embeddings kao pomoć, ne kao glavni kriterij.
​

Korak 5: Fallback
Ako nema trace/logova, vrati se na standardni semantic search nad kodom. (Ovo čuva pouzdanost i brzinu.)

Što dobivaš (konkretno)
Manje tokena: jer ne šalješ “sve o JWT-u”, nego “dokaz + 2 filea”

Veći hit rate: jer stack trace “sidri” retrieval na pravo mjesto

Wow efekt: jer LLM prestane pitati “daj još konteksta” i odmah predlaže minimalni patch + test plan (što debug RAG promptovi i preporučuju).
​

Kako da znaš da radi
Mjeri 3 metrike na 20 bugova:

“Top‑3 files contain fix?” (recall@3 za file)

“Tokens sent to LLM”

“# iteracija do patcha koji prođe failing test”

Ako hoćeš, reci mi na čemu radiš najčešće (Python? Rust? TS?) i odakle možeš uzeti stack trace (pytest output? runtime logs?). Na temelju toga ti predložim minimalan format “evidence ingest” koji se uklapa u Kronos bez velikog refaktora.