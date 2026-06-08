# Idea: Antigravity Agent Mode (OpenClaw Style)

**Date:** 2026-02-20
**Status:** Approved (Brainstorming Phase)

## Problem
Antigravity (Picard) is currently reactive. It only works when the user prompts it. This is a "System 1" behavior that limits the effectiveness of the AI as a true "Senior Architect".

## Proposed Solution (The "OpenClaw" model)
Transition to a proactive agent that uses the IDE's Heartbeat and the file system as a "Blackboard" for communication.

### Key Components
1. **Heartbeat Proactivity:** Use periodic polling to check for errors, TODOs, and task queue updates.
2. **Task Queue:** A `TASK_QUEUE.md` file where the user can delegate tasks asynchonously.
3. **Internal/External Soul:** Connecting the agent to external messaging (WhatsApp/Telegram/Discord) for remote status reporting.
4. **Kronos System 2:** Using Kronos for deeper reflection and context retrieval during proactive cycles.

## Decisions
- [x] Use `docs/` as the immortal source of truth.
- [x] Implement the Superpowers workflow for all changes.
- [x] Prioritize documentation and planning over immediate coding (User preference).
