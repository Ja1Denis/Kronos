from src.modules.oracle import Oracle
from src.modules.context_budgeter import ContextComposer, ContextItem, BudgetConfig
import json

oracle = Oracle()
query = "kako se zove projekt na kojem radimo?"
print(f"Testing query: {query}")
resp = oracle.ask(query, silent=False)

# Simulate Composer
composer = ContextComposer(BudgetConfig())
items = []
for c in resp.get('chunks', []):
    items.append(ContextItem(
        content=c['content'], 
        source=c['metadata'].get('source', 'unknown'), 
        kind="chunk", 
        utility_score=c.get('utility_score', 0.5)
    ))
for p in resp.get('pointers', []):
    pointer_text = f"FILE: {p['file_path']}\nSECTION: {p['section']}\nMATCH: {', '.join(p['keywords'])}"
    items.append(ContextItem(
        content=pointer_text, 
        source=p['file_path'], 
        kind="pointer", 
        utility_score=p.get('confidence', 0.1)
    ))

for item in items:
    composer.add_item(item)

context = composer.compose()
print(f"\nFinal Context Length: {len(context)}")
print(f"\nAudit Report:\n{composer.get_audit_report()}")

if context:
    print("\n--- Context Preview ---")
    print(context[:1000])
else:
    print("\nWARNING: Context is EMPTY!")
