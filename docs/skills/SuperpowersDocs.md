# Skill: Kronos Architect (SuperpowersDocs)

## 🧠 Description
This skill defines the mandatory workflow for all significant changes to the Kronos codebase. It ensures that documentation is treated as a first-class citizen and that every feature is thoughtfully planned before execution.

## 🔄 The Workflow (The "Superpowers" Loop)

### 1. 🌩️ Brainstorm (Ideation)
**Goal:** Capture the raw idea without constraints.
- **Where:** `docs/archive/ideas/YYYY_MM_feature_name.md`
- **Action:** Write down the problem, potential solutions, and "crazy" ideas.
- **Output:** A rough concept note.

### 2. 🗺️ Plan (Architecture)
**Goal:** Define *how* we will build it.
- **Where:** `implementation_plan.md` (Active Task Artifact)
- **Action:**
    - Define the changes.
    - Update `docs/architecture/decision_network.md` if key decisions are made.
    - Create a task checklist.
- **Output:** An approved plan.

### 3. ⚙️ Execute (Coding)
**Goal:** Build the thing.
- **Where:** `src/`
- **Action:** Write code, following the plan.
- **Output:** Working code.

### 4. 🧪 Review (Testing)
**Goal:** Verify it works.
- **Where:** `tests/`
- **Action:** Run unit tests, manual verification.
- **Output:** Passing tests.

### 5. 📚 Document (The "Scribe" Step)
**Goal:** Make it immortal.
- **Where:**
    - **Backend Logic:** `docs/backend/{module_name}.md`
    - **Integration:** `docs/clients/{client_name}.md`
    - **Process:** `docs/process/`
- **Action:** Update the persistent documentation to reflect the new reality.
- **Output:** Updated docs that match the code.

## 🤖 Instructions for AI Agents
When the user invokes this skill (or asks for a new feature):
1.  **Do NOT start coding immediately.**
2.  Check `docs/process` guidelines.
3.  Ask: "Should we brainstorm this first?"
4.  Ensure every PR/Commit includes a documentation update step.
