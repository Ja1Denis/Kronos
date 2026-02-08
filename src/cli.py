import typer
import os
import sys
from typing import Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
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
    recursive: bool = typer.Option(False, "--recursive", "-r", help="Rekurzivno pretraživanje")
):
    """
    Učitava dokumente i stvara semantičku memoriju.
    """
    console.print(Panel(f"[bold accent]Kronos Ingestor[/] v0.1\n[info]Učitavam iz: {path}[/]", border_style="accent"))

    ingestor = Ingestor()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        
        task = progress.add_task("[cyan]Skaniram datoteke...", total=None)
        files = ingestor._scan_files(path, recursive)
        progress.update(task, total=len(files), description=f"[cyan]Obrađujem {len(files)} datoteka...")
        
        for file_path in files:
            progress.console.print(f" [dim]→ {os.path.basename(file_path)}[/]")
            ingestor._process_file(file_path, silent=True)
            progress.advance(task)

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
    limit: int = typer.Option(5, "--limit", "-n", help="Broj rezultata")
):
    """
    Postavlja pitanje Kronosu i pretražuje memoriju.
    """
    oracle = Oracle()
    
    with console.status("[bold magenta]Kronos razmišlja...", spinner="dots8Bit"):
        results = oracle.ask(query, project=project, limit=limit, silent=True)

    if not results:
        console.print("[warning]Nema pronađenih rezultata za tvoj upit.[/]")
        return

    console.print(f"\n[header]Kronos je pronašao sljedeće odgovore:[/]\n")

    for i, res in enumerate(results):
        source = res['metadata'].get('source', 'Nepoznato')
        source_name = os.path.basename(source)
        score = res['score']
        m_type = res['type']
        content = res['content']
        
        # Formatiranje boje ovisno o tipu
        type_color = "green" if "Vector" in m_type else "yellow"
        proj_tag = f"[[dim]{res['metadata'].get('project', 'unknown')}[/]] "
        
        panel_content = f"{content}\n\n[dim]Izvor: {source_name} | Score: {score:.2%}[/]"
        panel = Panel(
            panel_content,
            title=f"{proj_tag}[{type_color}]{m_type} #{i+1}[/]",
            border_style=type_color,
            padding=(1, 2)
        )
        console.print(panel)
        console.print("")

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
def chat():
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
            # Probajmo detektirati projekt iz samog upita (pametna pretraga)
            target_project = None
            if "matematika" in query.lower(): target_project = "matematikapro"
            elif "kronos" in query.lower(): target_project = "kronos"
            
            results = oracle.ask(query, project=target_project, limit=3, silent=True)

        if not results:
            console.print("[warning]Nema pronađenih rezultata za tvoj upit.[/]")
            continue

        for i, res in enumerate(results):
            source = os.path.basename(res['metadata'].get('source', 'Nepoznato'))
            project_tag = res['metadata'].get('project', 'unknown')
            score = res['score']
            m_type = res['type']
            content = res['content']
            
            type_color = "green" if "Vector" in m_type else "yellow"
            
            panel = Panel(
                f"{content}\n\n[dim]Projekt: {project_tag} | Izvor: {source} | Score: {score:.2%}[/]",
                title=f"[{type_color}]{m_type} #{i+1}[/]",
                border_style=type_color,
                padding=(1, 2)
            )
            console.print(panel)

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
    
    # Izvrši ratifikaciju
    success = librarian.ratify_decision(
        decision_id,
        valid_from=valid_from,
        valid_to=valid_to,
        superseded_by=supersede
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
