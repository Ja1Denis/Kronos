import argparse
import sys
import os

# Dodajemo trenutni direktorij u sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def main():
    parser = argparse.ArgumentParser(description="Kronos: Semantička Memorija za AI Agente")
    subparsers = parser.add_subparsers(dest="command", help="Dostupne komande")

    # Komanda: Ingest (Unos)
    ingest_parser = subparsers.add_parser("ingest", help="Učitaj .md datoteke u bazu")
    ingest_parser.add_argument("path", help="Putanja do direktorija ili datoteke")
    ingest_parser.add_argument("--recursive", "-r", action="store_true", help="Rekurzivno pretraživanje")

    # Komanda: Query (Pretraga)
    query_parser = subparsers.add_parser("query", help="Postavi pitanje Kronosu")
    query_parser.add_argument("text", help="Tekst upita")
    query_parser.add_argument("--limit", "-n", type=int, default=5, help="Broj rezultata")

    args = parser.parse_args()

    if args.command == "ingest":
        # from modules.ingestor import Ingestor
        from modules.ingestor import Ingestor
        ingestor = Ingestor()
        ingestor.run(args.path, recursive=args.recursive)

    elif args.command == "query":
        # from modules.oracle import Oracle
        from modules.oracle import Oracle
        oracle = Oracle()
        oracle.ask(args.text, limit=args.limit)

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
