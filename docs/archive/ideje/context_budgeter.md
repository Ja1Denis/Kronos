“Context Budgeter”: automatsko slaganje konteksta u budžet
Ideja: Kronos ne vraća “top‑k snippeta”, nego vraća optimalan paket konteksta koji stane u točno zadani token budžet (npr. 1200 tokena) i maksimalizira šansu da LLM riješi task u jednom pokušaju. To je srž “context engineering” pristupa: kontekst je ograničen resurs i treba ga kurirati, ne samo dohvatiti.

Zašto je to “van kutije” i zašto konkurenti to ne rade dobro
Većina RAG alata radi retrieval (naći relevantno), ali ne radi dobro “sastavljanje” (što izbaciti, što sažeti, kako formatirati) pod strogo ograničenim budžetom, i zato ili šalju previše (skupo/sporo) ili premalo (loše). Sourcegraph eksplicitno naglašava da coding assistant ima gomilu različitih “context sources” (code, git, CI, editor state…) i da je retrieval samo prvi korak; pravi problem je kompozicija konteksta.

Kako to izgleda na primjeru
Korisnik pita u IDE-u:
“Zašto login ponekad vraća 500 umjesto 401?”

Kronos od watchera i indeksa već ima hrpu mogućih izvora. “Context Budgeter” napravi:

Skupi kandidate iz više izvora (ne samo vektori):

cursor file + okolina funkcije

najrelevantniji chunkovi iz searcha

zadnji diffovi (watcher)

zadnji error log (ako postoji)
(Ovo je upravo ono što Sourcegraph navodi kao tipične izvore).
​

Svakom kandidatu da “value score” i “token cost”.

Složi paket unutar budžeta (npr. 1200 tokena):

200 tokena: “briefing” (sažetak relevantnog flowa)

700 tokena: 2 ključna snippeta s file+line

200 tokena: zadnji diff / promjene

100 tokena: error log / stack trace isječak

Vrati to IDE-u/LLM-u u stabilnom formatu (uvijek isti layout).

Rezultat: manje tokena + veća “single‑shot” uspješnost, jer LLM dobije strukturiran i “najisplativiji” kontekst, ne samo slične paragrafe.

Zašto je ovo izvedivo “sad”
Ne treba ti graf, ne treba ti savršeni parser. Treba ti:

normalizirani “context items” (svaki ima type, score, tekst, token_estimate)

greedy/knapsack algoritam (jednostavno prvo greedy)

pravila formatiranja (briefing uvijek prvi, snippeti uvijek s line range)

To je 3–7 dana posla, i odmah osjetiš razliku.

Minimalni MVP (da ga riješite “barem jedan” problem)
Uvedi 4 vrste context itema:

cursor_context (uvijek)

retrieved_snippets (iz Chroma/FTS)

recent_changes (iz watchera)

project_map (kratko: list top 5 relevantnih fileova/simbola)

I uvedi jedan parametar: budget_tokens.

Endpoint:
POST /query { question, budget_tokens, path_hint? }
→ vraća { briefing, items[] } gdje ukupni zbroj tokena ne prelazi budžet.

Zašto je ovo “najbolji na svijetu” smjer
Jer praktično sve se svodi na “koliko dobro puniš kontekst” — Anthropic to doslovno tretira kao disciplinu: učinkovito kuriranje i upravljanje kontekstom je ključ jer je kontekst finite resource. A u kodiranju je to još ekstremnije: imaš stotine fajlova i tisuće simbola, ali u prompt stane samo malo.