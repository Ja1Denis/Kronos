# 💡 PicardAi — Docker Sandbox za Autonomni AI Agent

**Datum:** 2026-02-20
**Status:** ✅ Odobreno → U izradi

## Problem
Picard (naš AI asistent) je previše reaktivan — čeka korisnika. OpenClaw nudi autonomne mogućnosti ali radi unutar svog ekosustava.

## Rješenje
Kreirati **PicardAi** — Docker sandbox koji iskorištava OpenClaw koncept (agenti, skillovi, memorija, kanali) ali ga integrira s **Antigravity IDE-om** i **Kronos MCP-om**.

## Ključne Odluke
1. **Docker sandbox** s READ-ONLY workspaceom za sigurnost
2. **Besplatni modeli** (Gemini Flash, MiniMax M2.5, DeepSeek R1 Free, Qwen VL Free, Llama 3.3 Free)
3. **Picard + Data** multi-agent sustav (Commander + Executor)
4. **Kronos MCP** za dugoročnu memoriju (naša prednost nad OpenClaw-om)
5. **TASK_QUEUE.md** kao async komunikacija — agent predlaže, korisnik odobrava

## Formalizirano
- DEC-103 u `decision_network.md`
- DEC-104 u `decision_network.md`
