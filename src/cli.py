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
