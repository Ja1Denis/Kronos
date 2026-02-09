
import time
from sentence_transformers import CrossEncoder

start = time.time()
print("Učitavam model...")
model = CrossEncoder("BAAI/bge-reranker-base", max_length=512)
print(f"Učitan za {time.time() - start:.2f}s")

query = "Koja je baza podataka?"
documents = [
    "Koristimo PostgreSQL v17 kao primarnu bazu.",
    "Lubenica je voće.",
    "Python je programski jezik.",
    "Baza podataka je mjesto za pohranu.",
    "SQLite koristimo za testove."
]

pairs = [[query, d] for d in documents]

start = time.time()
scores = model.predict(pairs)
print(f"Inference za {len(documents)} parova: {time.time() - start:.2f}s")

for d, s in zip(documents, scores):
    print(f"{s:.4f}: {d}")
