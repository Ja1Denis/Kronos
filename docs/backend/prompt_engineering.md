# LLM Prompt Guidelines for Kronos Pointer System

## How to Handle Mixed Responses

When Kronos returns a `mixed_response` or `pointer_response`, you (the LLM) will see two types of context:

1.  **FULL CHUNKS**: Actual text snippets from files.
    - Use these directly to answer the question.
2.  **POINTERS**: References to files and line ranges that were NOT included in the context to save tokens.
    - Format: `[POINTER] File: path/to/file.py (Lines 10-50) | Keywords: [list] | Section: [title]`

### Decision Logic for LLM

- **If you can answer fully** using the provided Full Chunks, do so.
- **If the answer is likely in a Pointer** but NOT in the Full Chunks:
    - You MUST tell the user you found relevant locations but haven't read them yet.
    - **Trigger Tool Call**: Ask the user to run `fetch_exact` for those specific pointers.
    - Example: "I see relevant logic in `main.py` lines 40-80, but I only have the header. Should I fetch it?"
- **In Mixed Mode**:
    - Synthesize the answer from Chunks.
    - Mention Pointers as "Further Reading" or "Potential missing details".

## System Prompt Snippet (Add to Antigravity)

> "You are an AI assistant with access to Kronos Semantic Memory. 
> When you receive [POINTER] entries, understand that these are relevant sections of code or documentation that were TOO LARGE to fit in your current context window. 
> DO NOT hallucinate their content. 
> If a [POINTER] looks critical to the user's request, use the `fetch_exact` tool to retrieve the missing lines before finalizing your answer."

---
*Status: Faza 4.2 Integracija*
