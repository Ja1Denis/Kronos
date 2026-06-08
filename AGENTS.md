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

---

## 🏛️ Kronos Architect Protocol

This skill defines the **mandatory process** that an Agent must follow before beginning any complex planning or coding task.

### 🎯 Purpose
The goal is to eliminate redundancy, ensure architectural consistency, and reduce token consumption by reusing existing solutions from the Kronos Knowledge Base.

### 🛑 Phase 1: STOP & THINK (Analysis)
Before writing a single line of code or a detailed plan:
1.  **Identify Key Concepts**: Extract 3-5 keywords from the user's request (e.g., "fallback", "5th grade", "curriculum", "pdf export").
2.  **Formulate Questions**: What don't you know? What *might* already exist? (e.g., "Is there already a fallback spec?", "Do we have a generator for 1st grade?").

### 🔍 Phase 2: SEARCH (Discovery)
Use the `kronos_search` tool to find relevant documents.
*   **Query**: Use keywords from Phase 1.
*   **Limit**: Set to at least 5-10 results.
*   **Result Analysis**: Carefully read summaries (chunks). If you see a promising filename (e.g., `027-smart-fallback.md`), note it.

### 🧠 Phase 3: QUERY (Deep Understanding)
If keyword search isn't enough, or if you need specific details, use `kronos_query`.
*   **Example**: "Explain how the current `DeterministicClassifier` works and where fallback logic is added."
*   **Example**: "What is the directory structure for the 1st-grade curriculum?"

### ♻️ Phase 4: REUSE ANALYSIS (Assessment)
Based on gathered information, answer:
1.  **What do we already have?** (e.g., "We have a spec in `027-smart-fallback.md`", "We have `Method 1` defined").
2.  **What do we need to change?** (e.g., "We only need to implement `MixedTaskEngine` as per instructions").
3.  **What is new?** (What *doesn't* exist and must be created from scratch).

### 📝 Phase 5: SYNTHESIS (Report & Plan)
Create a short report for the user and (if necessary) an `implementation_plan.md` that explicitly references found documents.

> **Report Format:**
> *   🚀 **Found in Kronos**: [Links to documents/code]
> *   💡 **Savings**: "Instead of writing X, we will use Y."
> *   🛠️ **Plan**: "We will implement logic from document Z..."

---

### 💡 Usage Example

**Request**: "Create a system for PDF export of tasks."

1.  **Agent**: "Wait, maybe this already exists."
2.  **Tool**: `kronos_search(query="pdf export", project="MatematikaPro")`
3.  **Result**: Found `018-pdf-export.md`.
4.  **Agent**: "Aha! We already have a spec that says to use Puppeteer. I won't use jsPDF because the spec says otherwise."
5.  **Plan**: "I am implementing the `Puppeteer` service according to spec 018."
