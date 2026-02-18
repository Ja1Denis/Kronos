# Kronos ⏳
**Local Semantic Memory System for AI Agents**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Status: v0.6.1](https://img.shields.io/badge/Status-v0.6.1--Stable-orange.svg)]()

Kronos is an advanced memory system that provides AI agents with long-term memory and deep project context understanding while **drastically reducing costs** through an innovative "Pointer-based" RAG approach.

---

## 🌍 Project Origin & Language Note

Kronos started as a personal internal tool for managing local AI knowledge, primarily documented in **Croatian**. After seeing its massive impact on development efficiency and ROI, I decided to open-source it to the global community.

We are currently in the process of transitioning all codebase comments and internal documentation to **English**. If you encounter sections in Croatian, feel free to contribute by providing translations!

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

## 🏛️ Kronos Architect Protocol

Kronos isn't just a tool; it's a methodology. The **Kronos Architect Protocol** is a standardized workflow for AI agents that ensures every line of code is built upon existing knowledge, maximizing reuse and minimizing token waste.

1.  **STOP & THINK**: Analyze before coding.
2.  **SEARCH**: Find existing patterns.
3.  **QUERY**: Understand the details.
4.  **REUSE**: Adapt, don't invent.
5.  **SYNTHESIS**: Execute with precision.

See [AGENTS.md](AGENTS.md) and [docs/skills/SuperpowersDocs.md](docs/skills/SuperpowersDocs.md) for the full protocol definition.

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

## 🏁 Quick Start Guide

### 1. Prerequisites
- **Python 3.10+** needed.
- **Windows Users**: You might need [Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) for `chromadb`.

### 2. Installation & Setup

#### A. Automated Setup (Recommended for Windows)
Just run the setup script. It will create a virtual environment, install dependencies, and walk you through the language configuration (English/Croatian).

```powershell
./setup.ps1
```

#### B. Manual Installation
If you prefer manual control:

```powershell
# 1. Clone repository & enter
git clone https://github.com/Ja1Denis/Kronos.git
cd Kronos

# 2. Create and activate Virtual Environment
python -m venv venv
.\venv\Scripts\Activate.ps1  # Windows
source venv/bin/activate     # Mac/Linux

# 3. Install Dependencies
pip install -r requirements.txt

# 4. Configure Language (i18n)
python configure.py
```

> **🔍 Verification:** Run `python scripts/check_env.py` to verify everything is installed correctly.

### 3. API Configuration 🔑
Create a `.env` file in the root directory (automatically created if you used `setup.ps1`) and add your API key:
```ini
OPENROUTER_API_KEY=your_key_here
KRONOS_LANG=en  # Or 'hr' for Croatian
```

### 3. Build Knowledge Graph (First Run)
Initialize the project memory:
```powershell
python scripts/build_knowledge_graph.py --path . --project MyProject
```

### 4. Ingestion
Ingest your codebase into the vector database:
```powershell
python .\ingest_everything.py
```

### 5. IDE Integration (MCP)
Add Kronos to your MCP client configuration (e.g., `mcp_config.json` for Antigravity or Claude Desktop).

**Critical:** Point to the python executable *inside your venv*!

```json
{
  "mcpServers": {
    "kronos": {
      "command": "C:/PATH/TO/Kronos/venv/Scripts/python.exe",
      "args": ["-u", "C:/PATH/TO/Kronos/src/mcp_server.py"],
      "env": {
        "PYTHONPATH": "C:/PATH/TO/Kronos",
        "PYTHONUNBUFFERED": "1" 
      }
    }
  }
}
```

### 6. Usage (AI Agents)
Once the server is running (via MCP in your IDE), you can simply mention `@kronos` in your prompt.

**Example:**
> "@kronos How does the `Oracle` module handle context ranking?"

Kronos will intercept the request, search its memory, and inject the relevant code/docs into the context *before* the LLM answers.

### 7. Monitoring & Efficiency 📊
Track your knowledge growth and financial savings at any time:

#### A. Via Terminal (CLI)
```powershell
python -m src.main stats
```

#### B. Via AI Agent (MCP)
If you are using an MCP-compatible IDE (like Cursor or Antigravity), you can simply ask the LLM:
> "@kronos show me `kronos_stats`"

**Example Output (Power User):**
```text
┌──────────────────────────┬───────────────────────────────────────┐
│ Category                 │ Details                               │
├──────────────────────────┼───────────────────────────────────────┤
│ Total Files              │ 12,450                                │
│ Total Chunks             │ 158,200                               │
│ Extracted Knowledge      │ • Code: 45,600                        │
│                          │ • Decision: 842                       │
│                          │ • Problem: 312                        │
│                          │ • Solution: 295                       │
│                          │ • Task: 8,400                         │
│ Database Size            │ 4.82 GB                               │
│ Job Queue                │ Total: 12,500 | OK: 99.9% | Lat: 0.8s │
│ Saved Tokens (30d)       │ 12,450,000                            │
│ Avoided Cost (30d)       │ $124.50                               │
│ Total Savings (All-time) │ $1,450.25                             │
└──────────────────────────┴───────────────────────────────────────┘
```

## ❓ Troubleshooting

### "No module named 'chromadb'" or 'dotenv'
- **Cause:** The MCP server is likely running with the *system* Python instead of your *virtual environment* Python.
- **Fix:** In your `mcp_config.json`, change the `"command": "python"` to the absolute path of your venv python: `"C:/Users/.../Kronos/venv/Scripts/python.exe"`.

### "No module named 'FastMCP'"
- **Cause:** Missing `mcp` package or using an old version.
- **Fix:** Run `pip install -r requirements.txt` and ensure `mcp>=1.0.0` is installed. Note: `FastMCP` is part of the `mcp` package, not a separate `pip install fastmcp`.

### "SQLite version too old" (chromadb error)
- **Cause:** Windows often has an old generic SQLite DLL.
- **Fix:** Install `pysqlite3-binary` and override `sqlite3` in your code, or simply download `sqlite3.dll` from [sqlite.org](https://www.sqlite.org/download.html) and place it in your Python DLLs folder (or strictly use the venv provided one if it's newer).

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
