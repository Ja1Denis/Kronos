# Kronos ⏳
**Local Semantic Memory System for AI Agents**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status: v0.6.1](https://img.shields.io/badge/Status-v0.6.1--Stable-orange.svg)]()

Kronos is an advanced memory system that provides AI agents with long-term memory and deep project context understanding while **drastically reducing costs** through an innovative "Pointer-based" RAG approach.

---

## 💰 Token Efficiency - The Kronos Advantage

### Why are "Pointers" important?
Traditional RAG systems send **entire document blocks** to your LLM, consuming huge amounts of tokens. Kronos instead sends **lightweight pointers**, allowing the AI to decide what it actually needs.

### Visual Comparison
```text
┌─────────────────────────────────────────────────────────────┐
│ Traditional RAG (Sends all content)                        │
│ ████████████████████████████████████████████  15,000 tokens │
│ Cost: $0.021 per query                                      │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Kronos Pointers (Metadata only)                             │
│ ██ 300 tokens                                               │
│ Cost: $0.00042 per query                                    │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ Kronos Smart Fetch (Pointers + Selective Content)           │
│ ████████ 2,500 tokens                                       │
│ Cost: $0.0035 per query                                     │
└─────────────────────────────────────────────────────────────┘

📉 **83-98% reduction in token count**
💵 **5-50x cost savings**
```

### Real-world Cost Calculation
Based on **Gemini 1.5 Flash-8B** pricing ($0.10/1M input tokens):

| Monthly Volume    | Traditional RAG | Kronos (Pointers only) | Kronos (Smart Fetch) | Annual Savings  |
|-------------------|-----------------|------------------------|----------------------|-----------------|
| **1,000 queries**  | $15.00          | $0.30                  | $2.50                | **$150-176**    |
| **10,000 queries** | $150.00         | $3.00                  | $25.00               | **$1,500-1,764**|
| **100,000 queries**| $1,500.00       | $30.00                 | $250.00              | **$15,000-17,640**|

<sub>*Calculated with 15k tokens/query (RAG), 300 tokens/query (Pointer), 2.5k tokens/query (Smart Fetch)*</sub>

💡 **Break-even point: ~500 queries** (Kronos pays for itself in days, not months!)

---

## ✨ Key Features (v0.6.1)

- 📊 **Disk-Based Knowledge Graph**: SQLite-powered graph storage for low-RAM usage. Enables cross-project pattern matching and knowledge reuse.
- 🚀 **Multi-Agent Scaling**: Server-client architecture via **SSE transport**. Multiple IDE instances (VS Code, Cursor, Antigravity) can share the same memory without "database locked" errors.
- ⚡ **Rust Fast-Path (L0/L1)**: Ultra-fast literal match search implemented in Rust (**< 1ms**).
- 🛡️ **MCP IDE Integration**: Native stdio/SSE communication for Windows agents. Includes "Zero-Pollution" stdout shielding for maximum stability.
- 📉 **Shadow Accounting**: Built-in tracking of actual token and money savings reported in every AI response.
- 🔍 **Hybrid Search**: Combination of Vector search (ChromaDB) and precise FTS5 keyword search (SQLite).
- ⚖️ **Temporal Truth**: Tracks decision evolution over time (`valid_from`, `valid_to`).
- 📂 **Project Awareness**: Automatic knowledge isolation and filtering per project.
- 🛠️ **Smart Fetching**: AI independently requests exact code lines only when needed.

---

## 📈 Case Study: Reducing Hallucinations by 100%

In a real-world scenario (MatematikaPro project), Kronos prevented a "Senior-level" architectural error:

- **The Problem**: A standard AI agent hallucinated a missing component name (`TikuMessage`).
- **The Solution**: Kronos semantically mapped the requirement to the actual file (`TikuBubble.tsx`) using its Knowledge Graph.
- **The Result**: **97.8% Token Savings** and a surgical fix in under 30 seconds.

| Metric | Without Kronos | With Kronos | Savings |
| :--- | :--- | :--- | :--- |
| **Input Tokens** | ~145,000 | **~3,200** | **97.8%** 📉 |
| **Cost (Est.)** | ~$1.50 | **~$0.03** | **50x Cheaper** 💵 |

> [Read the full Impact Report here](docs/case-studies/impact-report.md)

---

## 🏗️ High-Level Architecture

```text
[ AI Client / Antigravity ] <--> [ FastAPI Server (Port 8765) ]
                                          |
        ┌─────────────────────────────────┴──────────────────────────────┐
        ▼                                 ▼                              ▼
 [ Rust FastPath ]                [ SQLite (FTS5) ]            [ ChromaDB (Vector) ]
 (Literal Matches)                (Keyword Rank)               (Semantic Score)
        │                                 │                              │
        └──────────────────────────┬──────┴──────────────────────────────┘
                                   ▼
                   [ Disk Knowledge Graph (v0.6.1) ]
                                   │
                   [ Oracle (Reranking & Selection) ]
                                   │
                          [ Context Budgeter ]
```

---

## 🚀 IDE Integration (MCP)

Kronos supports the **Model Context Protocol**. Configure your IDE (e.g., Gemini/Antigravity) by adding this to your `mcp_config.json`:

```json
{
  "mcpServers": {
    "kronos": {
      "command": "python",
      "args": ["-u", "C:/PATH/TO/KRONOS/src/mcp_server.py"],
      "env": {
        "PYTHONPATH": "C:/PATH/TO/KRONOS",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

> **Note:** Replace `C:/PATH/TO/KRONOS` with the actual absolute path to your cloned Kronos directory.

### 🛡️ Windows Robustness
The server uses **OS-level stdout hijacking** (`os.dup2`) to prevent communication "pollution". All non-JSON output (logs, native noise) is redirected to `stderr`.

---

## 🏁 Quick Start

### 1. Installation
```powershell
git clone https://github.com/Ja1Denis/Kronos.git
cd Kronos
pip install -r requirements.txt
```

### 2. Configuration 🔑
Add your `GEMINI_API_KEY` to a `.env` file for AI synthesis and embeddings.

### 3. Build Knowledge Graph (v0.6.1)
```powershell
python scripts/build_knowledge_graph.py --path . --project MyProject
```

### 4. Ingestion
```powershell
python .\ingest_everything.py
```

### 5. Usage
Add `@kronos` to your agent query. Each response will include an **Efficiency Report** showing your ROI.

---

## 🛠️ Development & Maintenance

### Reset and Wipe
For a fresh start:
```powershell
# Force wipe without confirmation
.\run.ps1 wipe --force
```

### Testing
```powershell
python -m pytest tests/ -v
```

---

## 📝 License & Credits
Made with ❤️ for advanced AI collaboration by **Denis Sakač**.
Licensed under the **MIT License**.
