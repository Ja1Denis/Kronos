from colorama import Fore, Style
import chromadb

def check():
    db_path = "data/store"
    print(f"{Fore.CYAN}🔎 Provjeravam bazu na putanji: {db_path}{Style.RESET_ALL}")
    
    try:
        client = chromadb.PersistentClient(path=db_path)
        collections = client.list_collections()
        
        if not collections:
            print(f"{Fore.RED}❌ Baza je prazna. Nema kolekcija.{Style.RESET_ALL}")
            return
            
        print(f"{Fore.GREEN}✅ Pronađeno {len(collections)} kolekcija.{Style.RESET_ALL}")
        
        for col in collections:
            collection = client.get_collection(name=col.name)
            count = collection.count()
            print(f"  📂 Kolekcija: {col.name} -> {count} zapisa.")
            if count == 0:
                 print(f"{Fore.YELLOW}  (Prazna kolekcija){Style.RESET_ALL}")
            
    except Exception as e:
        print(f"{Fore.RED}❌ Greška pri pristupu bazi: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    check()
