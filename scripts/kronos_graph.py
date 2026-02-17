#!/usr/bin/env python3
"""
Kronos Graph CLI - Command line tool for knowledge graph queries.

Usage:
    kronos-graph search <query>     # Search nodes
    kronos-graph class <name>       # Show class details
    kronos-graph file <path>        # Show file details
    kronos-graph project <name>     # Show project details
    kronos-graph deps <node_id>     # Show dependencies
    kronos-graph stats              # Show graph statistics
    kronos-graph projects           # List all projects
    kronos-graph visualize         # Generate visualization (text)
"""

import sys
import os
import argparse
import json

# Add src to path
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(script_dir, '..', 'src'))

from modules.disk_graph import DiskKnowledgeGraph


def format_node(node, indent=0):
    """Format single node for display."""
    prefix = "  " * indent
    node_type = node.get('node_type', 'unknown')
    content = node.get('content', '')
    metadata = node.get('metadata', {})
    
    if isinstance(metadata, str):
        try:
            metadata = json.loads(metadata)
        except:
            pass
    
    lines = [f"{prefix}[{node_type}] {content}"]
    
    if metadata and isinstance(metadata, dict):
        # Show relevant metadata
        if 'file' in metadata:
            lines.append(f"{prefix}  file: {metadata['file']}")
        if 'project' in metadata:
            lines.append(f"{prefix}  project: {metadata['project']}")
        if 'docstring' in metadata and metadata['docstring']:
            doc = metadata['docstring'][:100]
            lines.append(f"{prefix}  doc: {doc}...")
    
    return "\n".join(lines)


def cmd_stats(graph, args):
    """Show graph statistics."""
    stats = graph.get_stats()
    
    print("\n📊 Graph Statistics")
    print("=" * 40)
    print(f"  Total nodes: {stats['total_nodes']}")
    print(f"  Total edges: {stats['total_edges']}")
    print()
    print("  Node types:")
    for ntype, count in stats['node_types'].items():
        print(f"    {ntype}: {count}")
    print()
    print("  Relationship types:")
    for rtype, count in stats['relationship_types'].items():
        print(f"    {rtype}: {count}")
    
    return 0


def cmd_projects(graph, args):
    """List all projects in graph."""
    projects = graph.search_nodes(node_type='project')
    
    print("\n📁 Projects in Graph")
    print("=" * 40)
    
    for proj in projects:
        # Get file count
        files = graph.get_neighbors(proj['node_id'], rel_type='CONTAINS', direction='outgoing')
        
        print(f"\n  🗂️  {proj['content']}")
        print(f"      ID: {proj['node_id']}")
        print(f"      Files: {len(files)}")
        
        # Show modules/dependencies
        modules = graph.get_neighbors(proj['node_id'], rel_type='IMPORTS', direction='outgoing')
        if modules:
            unique_modules = set(m.get('content', '') for m in modules[:10])
            print(f"      Dependencies: {', '.join(list(unique_modules)[:5])}...")
    
    return 0


def cmd_search(graph, args):
    """Search nodes by query."""
    query = args.query
    
    print(f"\n🔍 Search: '{query}'")
    print("=" * 40)
    
    # Search by content
    results = graph.search_nodes(content_query=query, limit=20)
    
    if not results:
        print("  No results found.")
        return 0
    
    print(f"  Found {len(results)} results:\n")
    
    # Group by type
    by_type = {}
    for r in results:
        ntype = r.get('node_type', 'unknown')
        if ntype not in by_type:
            by_type[ntype] = []
        by_type[ntype].append(r)
    
    for ntype, nodes in by_type.items():
        print(f"  [{ntype}] ({len(nodes)}):")
        for n in nodes[:5]:
            print(f"    - {n.get('content', n['node_id'])}")
        if len(nodes) > 5:
            print(f"    ... and {len(nodes) - 5} more")
        print()
    
    return 0


def cmd_class(graph, args):
    """Show class details."""
    class_name = args.name
    
    # Search for class
    classes = [n for n in graph.search_nodes(node_type='class') 
               if class_name.lower() in n.get('content', '').lower()]
    
    if not classes:
        print(f"\n❌ Class '{class_name}' not found.")
        return 1
    
    for cls in classes:
        print(f"\n📦 Class: {cls['content']}")
        print("=" * 40)
        print(f"  ID: {cls['node_id']}")
        
        # Methods
        methods = graph.get_neighbors(cls['node_id'], rel_type='HAS_METHOD', direction='outgoing')
        print(f"\n  Methods ({len(methods)}):")
        for m in methods[:10]:
            print(f"    - {m.get('content', '')}")
        if len(methods) > 10:
            print(f"    ... and {len(methods) - 10} more")
        
        # Dependencies/Imports
        imports = graph.get_neighbors(cls['node_id'], rel_type='IMPORTS', direction='outgoing')
        print(f"\n  Imports ({len(imports)}):")
        for imp in imports[:10]:
            print(f"    - {imp.get('content', '')}")
    
    return 0


def cmd_file(graph, args):
    """Show file details."""
    path = args.path
    
    # Search for file
    files = [n for n in graph.search_nodes(node_type='file') 
             if path.lower() in n.get('content', '').lower()]
    
    if not files:
        print(f"\n❌ File '{path}' not found.")
        return 1
    
    for f in files:
        print(f"\n📄 File: {f['content']}")
        print("=" * 40)
        print(f"  ID: {f['node_id']}")
        
        # Get subgraph
        subgraph = graph.get_subgraph(f['node_id'], depth=2)
        
        print(f"\n  Structure ({len(subgraph['nodes'])} nodes, {len(subgraph['edges'])} edges):")
        
        # Group edges by type
        edge_types = {}
        for e in subgraph['edges']:
            rel = e.get('relationship_type', 'unknown')
            if rel not in edge_types:
                edge_types[rel] = []
            edge_types[rel].append(e)
        
        for rel, edges in edge_types.items():
            print(f"\n    [{rel}]:")
            for e in edges[:5]:
                # Get target node content
                target_id = e.get('to_node', '')
                target = subgraph['nodes'].get(target_id, {})
                content = target.get('content', target_id)
                print(f"      -> {content}")
    
    return 0


def cmd_deps(graph, args):
    """Show dependencies for a node."""
    node_id = args.node_id
    
    # Try to find node
    node = graph.get_node(node_id)
    if not node:
        # Try search
        results = graph.search_nodes(content_query=node_id, limit=1)
        if results:
            node = results[0]
        else:
            print(f"\n❌ Node '{node_id}' not found.")
            return 1
    
    print(f"\n🔗 Dependencies for: {node.get('content', node_id)}")
    print("=" * 40)
    
    # Outgoing dependencies
    outgoing = graph.get_neighbors(node['node_id'], direction='outgoing')
    if outgoing:
        print(f"\n  Outgoing ({len(outgoing)}):")
        for n in outgoing[:10]:
            rel = n.get('relationship_type', '')
            content = n.get('content', '')
            print(f"    [{rel}] {content}")
    
    # Incoming dependencies  
    incoming = graph.get_neighbors(node['node_id'], direction='incoming')
    if incoming:
        print(f"\n  Incoming ({len(incoming)}):")
        for n in incoming[:10]:
            rel = n.get('relationship_type', '')
            content = n.get('content', '')
            print(f"    [{rel}] {content}")
    
    return 0


def cmd_visualize(graph, args):
    """Generate text visualization of graph."""
    print("\n📈 Graph Visualization (Text Mode)")
    print("=" * 40)
    
    # Get top nodes by connections
    files = graph.search_nodes(node_type='file', limit=10)
    
    for f in files:
        content = f.get('content', '')
        if len(content) > 40:
            content = content[:37] + "..."
        
        # Get connections
        neighbors = graph.get_neighbors(f['node_id'], direction='both')
        
        # Group by relationship
        by_rel = {}
        for n in neighbors:
            rel = n.get('relationship_type', 'unknown')
            if rel not in by_rel:
                by_rel[rel] = []
            by_rel[rel].append(n.get('content', '')[:20])
        
        print(f"\n📄 {content}")
        for rel, nodes in by_rel.items():
            if nodes:
                print(f"   {rel}: {', '.join(nodes[:3])}")
    
    return 0


def main():
    parser = argparse.ArgumentParser(
        description='Kronos Graph CLI - Knowledge Graph queries',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  kronos-graph stats              # Show graph statistics
  kronos-graph projects           # List all projects
  kronos-graph search stem       # Search for 'stem'
  kronos-graph class Oracle      # Show Oracle class
  kronos-graph file oracle.py    # Show oracle.py details
  kronos-graph deps oracle       # Show dependencies
  kronos-graph visualize         # Text visualization
        """
    )
    
    parser.add_argument('--db-path', default='data/knowledge_graph.db',
                       help='Path to graph database')
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # stats
    subparsers.add_parser('stats', help='Show graph statistics')
    
    # projects
    subparsers.add_parser('projects', help='List all projects')
    
    # search
    search_parser = subparsers.add_parser('search', help='Search nodes')
    search_parser.add_argument('query', help='Search query')
    
    # class
    class_parser = subparsers.add_parser('class', help='Show class details')
    class_parser.add_argument('name', help='Class name')
    
    # file
    file_parser = subparsers.add_parser('file', help='Show file details')
    file_parser.add_argument('path', help='File path')
    
    # deps
    deps_parser = subparsers.add_parser('deps', help='Show dependencies')
    deps_parser.add_argument('node_id', help='Node ID or name')
    
    # visualize
    subparsers.add_parser('visualize', help='Generate visualization')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 0
    
    # Initialize graph
    try:
        graph = DiskKnowledgeGraph(args.db_path)
    except Exception as e:
        print(f"❌ Error connecting to graph: {e}")
        return 1
    
    # Route to command
    try:
        if args.command == 'stats':
            return cmd_stats(graph, args)
        elif args.command == 'projects':
            return cmd_projects(graph, args)
        elif args.command == 'search':
            return cmd_search(graph, args)
        elif args.command == 'class':
            return cmd_class(graph, args)
        elif args.command == 'file':
            return cmd_file(graph, args)
        elif args.command == 'deps':
            return cmd_deps(graph, args)
        elif args.command == 'visualize':
            return cmd_visualize(graph, args)
        else:
            parser.print_help()
            return 0
    finally:
        graph.close()


if __name__ == '__main__':
    sys.exit(main())
