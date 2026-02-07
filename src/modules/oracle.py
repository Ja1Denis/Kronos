from colorama import Fore, Style
import chromadb

class Oracle:
    def __init__(self, db_path="data/store"):
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="kronos_memory")
        # Više ne učitavamo SentenceTransformer!
        # ChromaDB koristi svoj ugrađeni ONNX model.

    def ask(self, query, limit=5):
        """
        Postavlja pitanje Kronosu.
        Koristi ChromaDB-ov ugrađeni embedding (ONNX - brz!).
        """
        print(f"{Fore.MAGENTA}🔮 Oracle traži odgovor na: '{query}'{Style.RESET_ALL}")
        
        # ChromaDB automatski vektorizira query koristeći isti model kao pri unosu
        results = self.collection.query(
            query_texts=[query],  # Umjesto query_embeddings!
            n_results=limit
        )
        
        # Ispiši rezultate
        documents = results['documents'][0]
        metadatas = results['metadatas'][0]
        distances = results['distances'][0]
        
        if not documents:
            print(f"{Fore.YELLOW}Nema rezultata.{Style.RESET_ALL}")
            return []
            
        print(f"{Fore.GREEN}Pronađeno {len(documents)} rezultata:{Style.RESET_ALL}")
        for doc, meta, dist in zip(documents, metadatas, distances):
            source = meta.get('source', 'Unknown')
            # Prikaži samo ime datoteke, ne cijelu putanju
            source_name = source.split('\\')[-1] if '\\' in source else source.split('/')[-1]
            print(f"\n{Fore.CYAN}📄 {source_name}{Style.RESET_ALL} (Score: {1-dist:.2%})")
            print(f"   {doc[:300]}...")
            print("-" * 50)
            
        return documents
