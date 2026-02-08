import typer
import os
import sys
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.theme import Theme
from rich import print as rprint

from src.modules.ingestor import Ingestor
from src.modules.oracle import Oracle
from src.modules.librarian import Librarian

# Tema boja (Cyberpunk vibe)
custom_theme = Theme({
    "info": "cyan",
    "warning": "yellow",
    "error": "bold red",
    "success": "bold green",
    "accent": "magenta",
    "header": "bold magenta",
})

console = Console(theme=custom_theme)
app = typer.Typer(help="Kronos: Semantička Memorija za AI Agente", add_completion=False)

@app.command()
def ingest(
    path: str = typer.Argument(..., help="Putanja do direktorija ili datoteke"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Ime projekta"),
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Rekurzivno pretraživanje")
):
    """
    Učitava dokumente i stvara semantičku memoriju.
    """
    console.print(Panel(f"[bold accent]Kronos Ingestor[/] v1.1\n[info]Učitavam iz: {path}[/]", border_style="accent"))

    ingestor = Ingestor()
    
    # Ako projekt nije zadan, Ingestor će ga sam detektirati iz putanje u .run()
    ingestor.run(path, project_name=project, recursive=recursive, silent=False)

    # Prikaži statistiku nakon unosa
    stats = Librarian().get_stats()
    table = Table(title="Status Memorije", box=None, header_style="bold cyan")
    table.add_column("Metrika", style="accent")
    table.add_column("Vrijednost", justify="right")
    
    table.add_row("Ukupno datoteka", str(stats.get('total_files', 0)))
    table.add_row("Ukupno chunkova", str(stats.get('total_chunks', 0)))
    
    for etype, count in stats.get('entities', {}).items():
        table.add_row(f"Entiteti ({etype})", str(count))
        
    console.print("\n")
    console.print(table)
    console.print(f"\n[bold success]✅ Ingestija završena![/]")

@app.command()
def ask(
    query: str = typer.Argument(..., help="Tvoje pitanje za Kronosa"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filtriraj po imenu projekta"),
    limit: int = typer.Option(5, "--limit", "-n", help="Broj rezultata"),
    hyde: bool = typer.Option(False, "--hyde", help="Koristi hipotetsku pretragu (HyDE)"),
    expand: bool = typer.Option(False, "--expand", "-e", help="Koristi proširenje upita (Expansion)")
):
    """
    Postavlja pitanje Kronosu i pretražuje memoriju.
    """
    oracle = Oracle()
    
    # with console.status("[bold magenta]Kronos razmišlja...", spinner="dots8Bit"):
    results = oracle.ask(query, project=project, limit=limit, silent=True, hyde=hyde, expand=expand)

    if not results["entities"] and not results["chunks"]:
        console.print("[warning]Nema pronađenih rezultata za tvoj upit.[/]")
        return

    # 1. PRIKAZ ENTITETA (Structured Objects)
    if results["entities"]:
        console.print(f"\n[bold accent]💎 Pronađeni Entiteti ({len(results['entities'])}):[/]")
        for ent in results["entities"]:
            source = ent['metadata'].get('source')
            source_name = os.path.basename(source) if source else "Ručni unos"
            proj_tag = f"[{ent['metadata'].get('project', 'unknown')}]"
            
            # Entity Card formatiranje
            etype = ent['type']
            type_style = "bold green" if etype == "DECISION" else "bold yellow"
            
            print(f"\n{proj_tag} {etype} #{ent['id']}")
            print(f"{ent['content']}")
            print(f"Izvor: {source_name} | Kreirano: {ent['created_at']}")
            print("-" * 30)

    # 2. PRIKAZ CHUNKOVA (Evidence)
    if results["chunks"]:
        header = "\n[bold info]📖 Citati iz dokumenata (Evidence):[/]" if results["entities"] else "\n[header]Pronađeni citati:[/]"
        console.print(header)
        
        for i, res in enumerate(results["chunks"]):
            source = res['metadata'].get('source', 'Nepoznato')
            source_name = os.path.basename(source)
            method = res['method']
            score = res.get('score', 0)
            content = res['content']
            project_name = res['metadata'].get('project', 'unknown')
            
            # Jednostavan ispis umjesto Panel-a
            print(f"\n--- Citat #{i+1} [{project_name}] ---")
            print(f"Izvor: {source_name}")
            print(f"Metoda: {method} (Score: {score:.2%})")
            print(content[:500])  # Ograniči na 500 znakova
            print("-" * 50)

@app.command()
def analyze():
    """
    Pokreće semantičku analizu i klasteriranje sadržaja (Auto-Tagging).
    Identificira glavne teme u projektu i označava relevantne dijelove.
    """
    from src.modules.curator import Curator
    curator = Curator()
    curator.run_clustering_pipeline()

@app.command()
def graph(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filtriraj po projektu"),
    fmt: str = typer.Option("text", "--format", "-f", help="Format ispisa: text ili dot")
):
    """
    Generira graf znanja projekta (veze između odluka i modula).
    """
    from src.modules.curator import Curator
    curator = Curator()
    if fmt == "dot":
        print(curator.generate_graph(project, "dot"))
    else:
        curator.generate_graph(project, "text")

@app.command()
def save(
    content: str = typer.Argument(..., help="Sadržaj koji želiš spremiti"),
    etype: Optional[str] = typer.Option(None, "--as", "-a", help="Tip zapisa (decision, fact, task)"),
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Projekt")
):
    """
    Ručno sprema zapis u semantičku memoriju.
    """
    librarian = Librarian()
    
    # Wizard if etype is missing
    if not etype:
        console.print("\n[bold cyan]Odaberi tip zapisa:[/]")
        console.print("  1. [green]DECISION[/] (Odluka)")
        console.print("  2. [yellow]TASK[/] (Zadatak)")
        console.print("  3. [white]FACT[/] (Činjenica)")
        
        choice = console.input("\nTraženi broj (1/2/3): ")
        if choice == "1": etype = "decision"
        elif choice == "2": etype = "task"
        else: etype = "fact"

    new_id = librarian.save_entity(etype.lower(), content, project=project)
    
    if new_id:
        console.print(f"\n[bold success]✅ Zapis spremljen![/] (ID: #{new_id}, Tip: {etype.upper()})")
    else:
        console.print("\n[warning]⚠️ Zapis nije spremljen (vjerojatno već postoji).[/]")

@app.command()
def watch(
    path: str = typer.Argument(".", help="Putanja za nadzor"),
    recursive: bool = typer.Option(True, "--recursive", "-r", help="Rekurzivni nadzor")
):
    """
    Pokreće Daemon mode koji automatski pronalazi promjene u tekstovima.
    """
    from src.modules.watcher import Watcher
    console.print(Panel(f"[bold accent]Kronos Watcher (Daemon)[/]\n[info]Pratim promjene u: {path}[/]", border_style="accent"))
    
    watcher = Watcher(path=path, recursive=recursive)
    watcher.run()

@app.command()
def chat(
    hyde: bool = typer.Option(False, "--hyde", help="Koristi HyDE mode u ovom sessionu"),
    expand: bool = typer.Option(False, "--expand", "-e", help="Koristi Expansion mode")
):
    """
    Pokreće interaktivni razgovor s Kronosom.
    """
    oracle = Oracle()
    console.print(Panel("[bold accent]Kronos Interaktivni Terminal[/]\n[info]Pitaj me bilo što. Upiši 'exit' za kraj.[/]", border_style="accent"))
    
    while True:
        query = console.input("\n[bold cyan]Ti > [/]")
        if query.lower() in ["exit", "quit", "izlaz", "kraj"]:
            console.print("[yellow]Pozdrav! Kronos se vraća u san...[/]")
            break
        
        if not query.strip():
            continue
            
        with console.status("[bold magenta]Kronos razmišlja...", spinner="dots8Bit"):
            # Poboljšana detekcija projekta iz upita
            target_project = None
            q_lower = query.lower()
            
            # Dohvati listu svih projekata za pametnije uparivanje
            all_projs = []
            try:
                all_projs = librarian.get_project_stats().keys()
                for p in all_projs:
                    if p and p.lower() in q_lower:
                        target_project = p
                        break
            except:
                pass # Ako ne možemo dohvatiti projekte, nastavi bez toga
            
            # Prvi pokušaj (s projektom ako je detektiran)
            results = oracle.ask(query, project=target_project, limit=3, silent=True, hyde=hyde, expand=expand)
            
            # FALLBACK: Ako nema rezultata, pokušaj bez filtera projekta
            if not results["entities"] and not results["chunks"] and target_project:
                results = oracle.ask(query, project=None, limit=3, silent=True, hyde=hyde, expand=expand)
                target_project = None # Resetiraj za prikaz

        if not results["entities"] and not results["chunks"]:
            console.print("[warning]Nema pronađenih rezultata za tvoj upit.[/]")
            continue

        # Kratki prikaz u chat modu
        if results["entities"]:
            ent = results["entities"][0]
            print(f"\n[{ent['metadata'].get('project', 'unknown')}] {ent['type']}: {ent['content']}")
        
        if results["chunks"]:
            chunk = results["chunks"][0]
            source = os.path.basename(chunk['metadata'].get('source', 'Nepoznato'))
            print(f"\n📖 Iz dokumenta '{source}':")
            print(chunk['content'][:400])

@app.command()
def stats():
    """
    Prikazuje statistiku baze podataka i memorije.
    """
    librarian = Librarian()
    stats_data = librarian.get_stats()
    
    table = Table(title="📊 Kronos Statistika", border_style="accent")
    table.add_column("Kategorija", style="cyan")
    table.add_column("Detalji", style="white")
    
    table.add_row("Indeksirane Datoteke", str(stats_data.get('total_files', 0)))
    table.add_row("Semantički Chunkovi", str(stats_data.get('total_chunks', 0)))
    
    # Entiteti
    entities_str = "\n".join([f"• {k.capitalize()}: {v}" for k, v in stats_data.get('entities', {}).items()])
    table.add_row("Ekstrahirano Znanje", entities_str or "0")
    
    # Veličina
    db_size = stats_data.get('db_size_kb', 0) + stats_data.get('chroma_size_kb', 0)
    table.add_row("Veličina Baze", f"{db_size/1024:.2f} MB")
    
    console.print(table)
    
@app.command()
def projects():
    """
    Prikazuje listu svih projekata i njihovu statistiku.
    """
    librarian = Librarian()
    proj_stats = librarian.get_project_stats()
    
    if not proj_stats:
        console.print("[warning]Nema aktivnih projekata u memoriji.[/]")
        return
        
    table = Table(title="🏢 Kronos Multi-Project Dashboard", border_style="accent")
    table.add_column("Projekt", style="bold cyan")
    table.add_column("Files", justify="center")
    table.add_column("Chunks", justify="center")
    table.add_column("Knowledge (Entities)", style="dim")
    
    for name, data in proj_stats.items():
        entities_summary = ", ".join([f"{k}:{v}" for k, v in data["entities"].items()])
        table.add_row(
            name or "default",
            str(data["files"]),
            str(data["chunks"]),
            entities_summary or "None"
        )
        
    console.print(table)

@app.command()
def decisions(
    project: Optional[str] = typer.Option(None, "--project", "-p", help="Filtriraj po projektu"),
    all: bool = typer.Option(False, "--all", "-a", help="Prikaži i zamijenjene odluke")
):
    """
    Prikazuje sve odluke u bazi znanja.
    """
    librarian = Librarian()
    decision_list = librarian.get_decisions(project=project, include_superseded=all)
    
    if not decision_list:
        console.print("[warning]Nema odluka u bazi.[/]")
        return
    
    table = Table(title="⚖️ Odluke", border_style="accent")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Sadržaj", style="white", max_width=50)
    table.add_column("Vrijedi", style="cyan")
    table.add_column("Status", style="green")
    
    for dec in decision_list:
        dec_id = str(dec['id'])
        content = dec['content'][:45] + "..." if len(dec['content']) > 45 else dec['content']
        
        v_from = dec.get('valid_from') or "∞"
        v_to = dec.get('valid_to') or "∞"
        validity = f"{v_from} → {v_to}"
        
        status = "[red]Zamijenjena[/]" if dec.get('superseded_by') else "[green]Aktivna[/]"
        
        table.add_row(dec_id, content, validity, status)
    
    console.print(table)
    console.print(f"\n[dim]Ukupno: {len(decision_list)} odluka[/]")

@app.command()
def history(
    decision_id: int = typer.Argument(..., help="ID odluke za koju želiš vidjeti povijest")
):
    """
    Prikazuje evoluciju (povijest) određene odluke.
    """
    librarian = Librarian()
    history_list = librarian.get_decision_history(decision_id)
    
    if not history_list:
        console.print(f"[error]❌ Nema povijesti za ID {decision_id}.[/]")
        return
        
    console.print(Panel(f"[bold accent]Kronos Timeline: Evolucija Odluke #{decision_id}[/]", border_style="accent"))
    
    for i, dec in enumerate(history_list):
        is_current = dec['id'] == decision_id
        arrow = "🟢 [bold white]SADA[/]" if is_current else "⚪ [dim]PRIJE[/]"
        
        status = "[red]ZAMIJENJENA[/]" if dec.get('superseded_by') else "[green]AKTIVNA[/]"
        
        content = f"{dec['content']}\n\n[dim]Vrijedi od: {dec.get('valid_from') or '?'}[/]"
        if dec.get('superseded_by'):
            content += f"\n[dim]Zamijenjena: {dec.get('valid_to')} ({dec.get('superseded_by')})[/]"
            
        panel = Panel(
            content,
            title=f"{arrow} - Odluka #{dec['id']} ({status})",
            border_style="accent" if is_current else "dim",
            padding=(1, 2)
        )
        console.print(panel)
        if i < len(history_list) - 1:
            console.print("      [bold magenta]│[/]")
            console.print("      [bold magenta]▼[/]")

@app.command()
def benchmark():
    """
    Pokreće benchmark testove i generira report o performansama.
    """
    from src.benchmark import run_benchmark
    run_benchmark()

@app.command()
def ratify(
    decision_id: int = typer.Argument(..., help="ID odluke za ratifikaciju"),
    valid_from: Optional[str] = typer.Option(None, "--from", "-f", help="Datum od kada vrijedi (YYYY-MM-DD)"),
    valid_to: Optional[str] = typer.Option(None, "--to", "-t", help="Datum do kada vrijedi (YYYY-MM-DD)"),
    supersede: Optional[str] = typer.Option(None, "--supersede", "-s", help="Nova odluka koja zamjenjuje ovu")
):
    """
    Ratificira odluku - ažurira njene temporalne parametre.
    
    Primjer:
        kronos ratify 5 --from 2026-01-01 --to 2026-12-31
    """
    librarian = Librarian()
    
    # Provjeri postoji li odluka
    decision = librarian.get_decision_by_id(decision_id)
    if not decision:
        console.print(f"[error]❌ Odluka s ID-om {decision_id} nije pronađena.[/]")
        return
    
    console.print(Panel(
        f"[bold accent]Ratifikacija Odluke #{decision_id}[/]\n\n"
        f"[info]{decision['content'][:100]}{'...' if len(decision['content']) > 100 else ''}[/]",
        border_style="accent"
    ))
    
    # Ako ni jedan parametar nije zadan, prikaži interaktivni mod
    if not any([valid_from, valid_to, supersede]):
        console.print("\n[dim]Trenutne vrijednosti:[/]")
        console.print(f"  Valid From: {decision.get('valid_from') or 'Nije definirano'}")
        console.print(f"  Valid To: {decision.get('valid_to') or 'Nije definirano'}")
        console.print(f"  Superseded By: {decision.get('superseded_by') or 'Nije zamijenjeno'}")
        
        console.print("\n[warning]Koristi --from, --to ili --supersede za ažuriranje.[/]")
        return
    
    # Izvrši ratifikaciju / zamjenu
    if supersede:
        new_id = librarian.supersede_decision(decision_id, supersede)
        success = new_id is not None
        if success:
            console.print(f"\n[bold success]✅ Odluka #{decision_id} zamijenjena novom (#{new_id})![/]")
    else:
        success = librarian.ratify_decision(
            decision_id,
            valid_from=valid_from,
            valid_to=valid_to,
            superseded_by=None
        )
    
    if success:
        console.print(f"\n[bold success]✅ Odluka #{decision_id} uspješno ratificirana![/]")
        
        # Prikaži ažurirane vrijednosti
        updated = librarian.get_decision_by_id(decision_id)
        table = Table(show_header=False, box=None)
        table.add_column("Polje", style="dim")
        table.add_column("Vrijednost", style="cyan")
        
        table.add_row("Valid From", updated.get('valid_from') or "∞")
        table.add_row("Valid To", updated.get('valid_to') or "∞")
        table.add_row("Superseded By", updated.get('superseded_by') or "-")
        
        console.print(table)
    else:
        console.print(f"[error]❌ Greška pri ratifikaciji odluke.[/]")

@app.command()
def mcp():
    """
    Pokreće Kronos kao MCP (Model Context Protocol) server.
    
    Ovaj mod omogućuje integraciju s Claude Desktop, Gemini CLI i drugim MCP klijentima.
    Server koristi stdio transport.
    """
    console.print(Panel(
        "[bold accent]Kronos MCP Server[/]\n"
        "[info]Pokrećem Model Context Protocol server...[/]\n\n"
        "[dim]Alati: kronos_search, kronos_stats, kronos_decisions, kronos_ingest[/]",
        border_style="accent"
    ))
    
    from src.mcp_server import main as mcp_main
    mcp_main()

@app.command()
def backup(
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Putanja za backup datoteku (default: backups/)"),
):
    """
    Kreira sigurnosnu kopiju Kronos baze podataka.
    
    Sprema SQLite bazu i ChromaDB store u ZIP arhivu s vremenskom oznakom.
    """
    import zipfile
    import shutil
    from datetime import datetime
    
    console.print(Panel("[bold accent]Kronos Backup[/]\n[info]Kreiram sigurnosnu kopiju...[/]", border_style="accent"))
    
    # Definiraj putanje
    data_dir = "data"
    backup_dir = "backups"
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    # Generiraj ime backup datoteke
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = output or os.path.join(backup_dir, f"kronos_backup_{timestamp}.zip")
    
    # Provjeri postoji li data direktorij
    if not os.path.exists(data_dir):
        console.print("[error]❌ Data direktorij ne postoji. Nema podataka za backup.[/]")
        return
    
    with console.status("[bold cyan]Kreiram ZIP arhivu..."):
        try:
            with zipfile.ZipFile(backup_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Dodaj sve datoteke iz data direktorija
                for root, dirs, files in os.walk(data_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, ".")
                        zipf.write(file_path, arcname)
                        
            # Statistika
            backup_size = os.path.getsize(backup_filename) / (1024 * 1024)
            
            console.print(f"\n[bold success]✅ Backup uspješno kreiran![/]")
            console.print(f"   📁 Datoteka: [cyan]{backup_filename}[/]")
            console.print(f"   📦 Veličina: [cyan]{backup_size:.2f} MB[/]")
            
        except Exception as e:
            console.print(f"[error]❌ Greška pri kreiranju backupa: {e}[/]")

@app.command()
def restore(
    backup_file: str = typer.Argument(..., help="Putanja do backup ZIP datoteke"),
    force: bool = typer.Option(False, "--force", "-f", help="Preskoči potvrdu")
):
    """
    Vraća Kronos bazu iz sigurnosne kopije.
    
    UPOZORENJE: Ovo će prebrisati postojeće podatke!
    """
    import zipfile
    import shutil
    
    if not os.path.exists(backup_file):
        console.print(f"[error]❌ Backup datoteka ne postoji: {backup_file}[/]")
        return
    
    if not backup_file.endswith('.zip'):
        console.print("[error]❌ Datoteka mora biti ZIP arhiva.[/]")
        return
    
    console.print(Panel(
        f"[bold accent]Kronos Restore[/]\n"
        f"[warning]⚠️ UPOZORENJE: Ovo će prebrisati postojeće podatke![/]\n"
        f"[info]Backup: {backup_file}[/]",
        border_style="yellow"
    ))
    
    if not force:
        confirm = typer.confirm("Jesi li siguran da želiš nastaviti?", default=False)
        if not confirm:
            console.print("[info]Otkazano.[/]")
            return
    
    data_dir = "data"
    
    with console.status("[bold cyan]Vraćam podatke iz backupa..."):
        try:
            # Obriši postojeći data direktorij
            if os.path.exists(data_dir):
                shutil.rmtree(data_dir)
            
            # Raspakiraj backup
            with zipfile.ZipFile(backup_file, 'r') as zipf:
                zipf.extractall(".")
            
            console.print(f"\n[bold success]✅ Restore uspješan![/]")
            console.print(f"   📁 Podaci vraćeni iz: [cyan]{backup_file}[/]")
            
        except Exception as e:
            console.print(f"[error]❌ Greška pri vraćanju podataka: {e}[/]")

@app.command()
def rebuild():
    """
    Rekonstruira SQLite i ChromaDB baze iz archive.jsonl datoteke.
    Korisno kod migracija ili gubitka podataka.
    """
    confirm = typer.confirm("Ovo će obrisati trenutnu bazu i učitati sve iz arhive. Nastaviti?", default=False)
    if confirm:
        from src.rebuild_from_archive import rebuild as run_rebuild
        run_rebuild()
    else:
        console.print("[info]Otkazano.[/]")

@app.command()
def wipe():
    """
    Briše svu memoriju i resetira bazu.
    """
    confirm = typer.confirm("[error]Jesi li siguran da želiš obrisati CIJELU memoriju?[/]", default=False)
    if confirm:
        with console.status("[bold red]Brišem podatke..."):
            Librarian().wipe_all()
        console.print("[bold green]Memorija je uspješno resetirana.[/]")
    else:
        console.print("[info]Otkazano.[/]")

if __name__ == "__main__":
    app()
