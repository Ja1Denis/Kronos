import json
import time
import os
from src.modules.oracle import Oracle
from rich.console import Console
from rich.table import Table

console = Console()

def run_benchmark(questions_path: str = None):
    if not questions_path:
        questions_path = os.path.join("eval", "questions.json")
        
    if not os.path.exists(questions_path):
        console.print(f"[red]❌ Test pitanja nisu pronađena na {questions_path}[/]")
        return

    with open(questions_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    oracle = Oracle()
    
    table = Table(title="📊 Kronos Benchmark Rezultati")
    table.add_column("Upit", style="cyan")
    table.add_column("Recall@5", justify="center")
    table.add_column("Vrijeme (ms)", justify="right")
    table.add_column("Entiteti found", justify="center")

    total_latency = 0
    total_recall = 0
    
    report_rows = []

    for q in questions:
        query = q["query"]
        expected = q["expected_keywords"]
        project = q.get("project")

        start_time = time.time()
        results = oracle.ask(query, project=project, limit=5, silent=True)
        latency = (time.time() - start_time) * 1000
        
        # Izračunaj recall (koliko se ključnih riječi pojavljuje u rezultatima)
        combined_text = ""
        for ent in results["entities"]:
            combined_text += ent["content"] + " "
        for chunk in results["chunks"]:
            combined_text += chunk["content"] + " "
        
        combined_text = combined_text.lower()
        found_keywords = [k for k in expected if k.lower() in combined_text]
        recall = len(found_keywords) / len(expected) if expected else 1.0
        
        entities_found = len(results["entities"])
        
        table.add_row(
            query, 
            f"{recall:.0%}", 
            f"{latency:.1f}", 
            str(entities_found)
        )
        
        total_latency += latency
        total_recall += recall
        
        report_rows.append({
            "query": query,
            "recall": recall,
            "latency": latency,
            "entities": entities_found
        })

    console.print(table)
    
    avg_recall = total_recall / len(questions)
    avg_latency = total_latency / len(questions)
    
    console.print(f"\n[bold green]Prosječni Recall@5: {avg_recall:.2%}[/]")
    console.print(f"[bold cyan]Prosječna Latencija: {avg_latency:.1f} ms[/]")

    # Generiraj Markdown Report
    _generate_markdown_report(report_rows, avg_recall, avg_latency)

def _generate_markdown_report(rows, avg_recall, avg_latency):
    report_path = os.path.join("eval", "benchmark_report.md")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Kronos Benchmark Report\n\n")
        f.write(f"Datum: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        f.write("## Sažetak\n")
        f.write(f"- **Prosječni Recall@5:** {avg_recall:.2%}\n")
        f.write(f"- **Prosječna Latencija:** {avg_latency:.1f} ms\n\n")
        
        f.write("## Detaljni Rezultati\n")
        f.write("| Upit | Recall | Latencija (ms) | Entiteti |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        for r in rows:
            f.write(f"| {r['query']} | {r['recall']:.0%} | {r['latency']:.1f} | {r['entities']} |\n")
            
    console.print(f"\n[dim]Report spremljen u: {report_path}[/]")

if __name__ == "__main__":
    run_benchmark()
