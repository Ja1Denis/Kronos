"""
Build Knowledge Graph Script

Skenira codebase i gradi graf znanja za Kronos v0.6.1.
Podržava Python i JavaScript/TypeScript parsiranje.
"""

import ast
import os
import json
import sys
import argparse
from pathlib import Path
from typing import Set, List, Dict

# Add src to path
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(script_dir, 'src'))

from modules.disk_graph import DiskKnowledgeGraph


class CodebaseParser:
    """Parser za ekstrakciju strukture koda u graf."""
    
    def __init__(self, graph: DiskKnowledgeGraph, project_name: str):
        self.graph = graph
        self.project_name = project_name
        self.visited_files: Set[str] = set()
    
    def parse_directory(self, root_dir: str, extensions: List[str] = None):
        """Parsiraj cijeli direktorij."""
        if extensions is None:
            extensions = ['.py', '.js', '.ts', '.jsx', '.tsx']
        
        for root, dirs, files in os.walk(root_dir):
            # Preskoči nebitne direktorije
            dirs[:] = [d for d in dirs if d not in [
                '.git', 'node_modules', '__pycache__', '.venv', 'venv',
                'dist', 'build', '.pytest_cache', 'data', 'logs'
            ]]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    file_path = os.path.join(root, file)
                    self.parse_file(file_path)
    
    def parse_file(self, file_path: str):
        """Parsiraj jednu datoteku."""
        if file_path in self.visited_files:
            return
        self.visited_files.add(file_path)
        
        rel_path = os.path.relpath(file_path, os.getcwd())
        
        # Dodaj file node
        file_id = f"file:{self.project_name}:{rel_path}"
        self.graph.add_node(
            file_id,
            "file",
            content=rel_path,
            metadata={
                "project": self.project_name,
                "path": rel_path,
                "extension": os.path.splitext(file_path)[1]
            }
        )
        
        # Route based on extension
        ext = os.path.splitext(file_path)[1]
        
        try:
            if ext == '.py':
                self._parse_python(file_path, file_id, rel_path)
            elif ext in ['.js', '.ts', '.jsx', '.tsx']:
                self._parse_js(file_path, file_id, rel_path)
        except Exception as e:
            print(f"  ⚠️ Error parsing {rel_path}: {e}")
    
    def _parse_python(self, file_path: str, file_id: str, rel_path: str):
        """Parsiraj Python datoteku."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
                tree = ast.parse(content, filename=file_path)
            
            # Detektiraj imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # Dodaj import veze
            for imp in imports:
                imp_id = f"module:{imp}"
                self.graph.add_node(imp_id, "module", content=imp)
                self.graph.add_edge(file_id, imp_id, "IMPORTS", weight=0.5)
            
            # Detektiraj klase
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_id = f"class:{self.project_name}:{node.name}"
                    self.graph.add_node(
                        class_id,
                        "class",
                        content=node.name,
                        metadata={
                            "project": self.project_name,
                            "file": rel_path,
                            "docstring": ast.get_docstring(node)
                        }
                    )
                    self.graph.add_edge(file_id, class_id, "CONTAINS")
                    
                    # Metode klase
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_id = f"method:{class_id}:{item.name}"
                            self.graph.add_node(
                                method_id,
                                "method",
                                content=item.name,
                                metadata={
                                    "project": self.project_name,
                                    "class": node.name,
                                    "file": rel_path
                                }
                            )
                            self.graph.add_edge(class_id, method_id, "HAS_METHOD")
                
                # Detektiraj funkcije (top-level)
                elif isinstance(node, ast.FunctionDef) and node.col_offset == 0:
                    func_id = f"function:{self.project_name}:{node.name}"
                    self.graph.add_node(
                        func_id,
                        "function",
                        content=node.name,
                        metadata={
                            "project": self.project_name,
                            "file": rel_path
                        }
                    )
                    self.graph.add_edge(file_id, func_id, "DEFINES")
            
            print(f"  ✅ Parsed Python: {rel_path}")
        
        except SyntaxError as e:
            print(f"  ⚠️ Syntax error in {rel_path}: {e}")
        except Exception as e:
            print(f"  ⚠️ Error in {rel_path}: {e}")
    
    def _parse_js(self, file_path: str, file_id: str, rel_path: str):
        """Parsiraj JavaScript/TypeScript datoteku (jednostavno)."""
        # Jednostavno parsiranje - samo regex za exports i imports
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            import re
            
            # Regex za imports: import x from 'y' ili require('y')
            import_pattern = r"(?:import\s+.*?\s+from\s+['\"](.+?)['\"]|require\s*\(\s*['\"](.+?)['\"]\s*\))"
            for match in re.finditer(import_pattern, content):
                imp = match.group(1) or match.group(2)
                if imp:
                    imp_id = f"module:{imp}"
                    self.graph.add_node(imp_id, "module", content=imp)
                    self.graph.add_edge(file_id, imp_id, "IMPORTS", weight=0.5)
            
            # Regex za exports: export function x() ili export const x =
            export_pattern = r"export\s+(?:default\s+)?(?:function|class|const|let|var)\s+(\w+)"
            for match in re.finditer(export_pattern, content):
                name = match.group(1)
                export_id = f"export:{self.project_name}:{name}"
                self.graph.add_node(
                    export_id,
                    "export",
                    content=name,
                    metadata={"project": self.project_name, "file": rel_path}
                )
                self.graph.add_edge(file_id, export_id, "EXPORTS")
            
            print(f"  ✅ Parsed JS/TS: {rel_path}")
        
        except Exception as e:
            print(f"  ⚠️ Error in {rel_path}: {e}")


def main():
    parser = argparse.ArgumentParser(description='Build knowledge graph from codebase')
    parser.add_argument('project_path', help='Path to project directory')
    parser.add_argument('--project-name', help='Project name (default: directory name)')
    parser.add_argument('--db-path', default='data/knowledge_graph.db', help='Path to graph database')
    parser.add_argument('--clear', action='store_true', help='Clear existing graph before building')
    parser.add_argument('--extensions', nargs='+', default=['.py', '.js', '.ts', '.jsx', '.tsx'],
                       help='File extensions to parse')
    
    args = parser.parse_args()
    
    # Determine project name
    project_name = args.project_name or os.path.basename(os.path.abspath(args.project_path))
    
    print(f"\n🚀 Building knowledge graph for: {project_name}")
    print(f"📁 Source: {args.project_path}")
    print(f"💾 Graph DB: {args.db_path}")
    
    # Initialize graph
    graph = DiskKnowledgeGraph(args.db_path)
    
    if args.clear:
        print("🧹 Clearing existing graph...")
        graph.clear()
    
    # Add project node
    project_id = f"project:{project_name}"
    graph.add_node(
        project_id,
        "project",
        content=project_name,
        metadata={"path": args.project_path}
    )
    
    # Parse codebase
    parser = CodebaseParser(graph, project_name)
    parser.parse_directory(args.project_path, args.extensions)
    
    # Print stats
    stats = graph.get_stats()
    print(f"\n📊 Graph Statistics:")
    print(f"   Total nodes: {stats['total_nodes']}")
    print(f"   Total edges: {stats['total_edges']}")
    print(f"   Node types: {stats['node_types']}")
    print(f"   Relationship types: {stats['relationship_types']}")
    
    graph.close()
    print(f"\n✅ Knowledge graph built successfully!")


if __name__ == "__main__":
    main()
