# Agent Instructions for Kronos Project

## 🛡️ Kronos: The Semantic Memory System
Kronos is a semantic memory and knowledge retrieval system designed to provide project-specific context with extreme token efficiency.

### 🛠️ Available MCP Tools

#### `kronos_query`
This is your primary tool for retrieving knowledge about the project, architecture, or specific code entities.

**Parameters:**
- `query` (string): Your question about the project.
- `mode` (string): 'light' (budget-friendly), 'auto' (standard), 'extra' (verbose).

**When to use:**
- When the user asks about the overall architecture ("How does Kronos work?").
- When you need to find specific definitions or decisions ("What was the decision on T034?").
- When you need to explore unfamiliar modules in the current workspace.

---

#### `kronos_search`
Low-level semantic search that returns raw chunks with relevance scores. Use this if you need granular control over search results.

---

#### `kronos_stats`
Provides a high-level overview of the knowledge base (size, entity counts, job queue status).

---

#### `kronos_decisions`
Retrieves specifically 'decision' type entities. Use this to check architectural boundaries and project rules.

---

### 💡 Best Practices for Agents
1. **Prefer `kronos_query`**: It uses the `ContextComposer` to automatically format results into a compact, budget-aware response (using Pointers and selective fetching).
2. **Context Awareness**: If you are in a specific file and get stuck, use `kronos_query` to see if there is existing knowledge or documentation about that file/module.
3. **Hybrid Power**: Kronos combines Vector search, FTS5 (Keyword), and Rust FastPath. It is very robust against typos and code snippets.
