# LLM Prompt Guidelines for Kronos Agentic Pointers

## The "Late Retrieval" Concept

When Kronos returns contexts, it prioritizes **Agentic Pointers** over full source code to save context window space and reduce hallucinations.

You (the LLM) will often receive a "Menu" of available snippets rather than the full code.
Example of a Pointer:
`--- POINTER (src/auth.py) ---`
`FILE: src/auth.py`
`SECTION: def verify_user_token(token: str) -> bool:`
`MATCH: token, security, verify`

### Decision Logic for the Agent (YOU)

1.  **Analyze the Menu:** Read the `SECTION` and `MATCH` keywords of the provided Pointers.
2.  **Determine Relevance:** Does the user's question require the exact code inside one of these pointers?
    *   **NO:** Answer the user's question directly if you already know the answer.
    *   **YES:** You **MUST** use the `fetch_exact` tool to read the exact lines of code. Do not hallucinate the contents of the file.
3.  **Using `fetch_exact`**: 
    - The tool requires `file_path`, `start_line`, and `end_line`.
    - However, since Kronos pointers might only give you the file path in the menu, you should supply the `file_path` and a wide range (e.g. `start_line: 1`, `end_line: 500`) to fetch the requested file chunk.

## System Prompt Snippet (Add to Antigravity)

> "You are an autonomous AI Agent equipped with Kronos Semantic Memory.
> You operate on a "Late Retrieval" architecture. Kronos will give you a list of [POINTERS], which act as a menu of available files and sections.
> YOUR JOB is to read the menu and decide what to open. 
> DO NOT hallucinate code. If a [POINTER] looks relevant, you MUST independently use the `fetch_exact` tool to read the file before answering the user."

---
*Status: V2 Agentic Integration*
