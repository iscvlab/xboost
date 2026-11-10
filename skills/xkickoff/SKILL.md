---
name: xkickoff
description: >
  Synthesize end-of-session progress, verify doc sync, present next-step options, and generate a pristine kickoff prompt for a fresh chat (/xkickoff, /kickoff).
  Use when wrapping up a session, starting a fresh chat, transitioning after compaction, or running /xkickoff.
  Do NOT use for context health (/xcontext), mid-session doc sync (/xsync), or skill authoring (/xcreate-skill).
---

# `/xkickoff` (Session Transition & Kickoff Prompt Synthesizer)

Prepare a seamless, zero-loss transition from a compacted or ending conversation into a **pristine fresh conversation**.

This skill performs a three-way bridge:
1. **Doc Sync Verification**: Ensures decisions made in this session are committed to documentation before exiting.
2. **Strategic Options Formulation**: Analyzes active roadmaps to offer orthogonal, roadmap-grounded next-step paths.
3. **Pristine Kickoff Prompt Generation**: Assembles a self-contained prompt block containing locked invariants, active file paths, and task-matched XBoost `/x...` slash commands ([`/xbrief`](../xbrief/SKILL.md), [`/xplan`](../xplan/SKILL.md), [`/xdeep-research`](../xdeep-research/SKILL.md), [`/xlaya`](../xlaya/SKILL.md), [`/xobsidian`](../xobsidian/SKILL.md), [`/xboost`](../xboost/SKILL.md), [`/xlearn`](../xlearn/SKILL.md), [`/xultra`](../xultra/SKILL.md), `/goal`) for the new chat.

Portable across any AI coding agent (cloud, IDE, CLI, or local LLM) across Windows, macOS, and Linux.

Red failure modes to prevent:
1. Leaving uncommitted, unsynchronized facts behind when starting a fresh chat.
2. Giving a vague or underspecified prompt to the new agent, forcing it to guess the context or hallucinate previously resolved decisions.
3. Losing hard-won negative constraints or locked invariants (e.g. structural cardinalities, frozen sections, styling protocols) across the chat boundary.
4. **Accidental In-Chat Execution Trap**: Treating a user's option selection (`"Option A"`, `"Option B"`, `"1"`, etc.) after `/xkickoff` as a command to *execute* that task inside the current exhausted chat, instead of generating/updating the Kickoff Prompt for the new chat.

---

## Strict Terminal-Session Guardrail (Anti-Execution Invariant)

> [!CAUTION]
> **ONCE `/xkickoff` IS INVOKED, THIS CHAT IS IN TERMINAL HANDOFF MODE.**
> - When the user replies to a `/xkickoff` turn with an option choice (e.g., `"Option A"`, `"Option B"`, `"2"`) or a refinement (e.g., `"also mention X"`, `"don't lock Y yet"`), you **MUST NEVER** start executing that task in the current chat.
> - Your **ONLY** action upon receiving the user's selection or refinement is to **write (or rewrite) the Pristine Kickoff Prompt** tailored to that selection so the user can copy-paste it into a fresh conversation.

---

## When Not to Use

| Need | Use Instead |
| :--- | :--- |
| Check current context compaction round or memory health | [`/xcontext`](../xcontext/SKILL.md) |
| Deep multi-file document synchronization sweep | [`/xsync`](../xsync/SKILL.md) |
| Create an implementation plan inside an active session | [`/xplan`](../xplan/SKILL.md) |
| Run primary-source or 5-wave deep research | [`/xdeep-research`](../xdeep-research/SKILL.md) |
| Author or distill a skill | [`/xcreate-skill`](../xcreate-skill/SKILL.md) |
| Ratchet session bug/optimization patterns into Playbooks or evolve universal laws | [`/xlearn`](../xlearn/SKILL.md) |
| Regular task briefing inside an active chat | [`/xbrief`](../xbrief/SKILL.md) |

---

## Standard Operating Procedure (Smart Hybrid 2A Routing)

### Step 1: Pre-Handoff Sync Gate (Zero Stale State)

Before formulating the next session's work, verify that the current conversation's outputs are safely recorded on disk:

1. Check `git status --short` (or recent file edits) to identify modified, untracked, or staged files.
2. Verify that active documentation accurately reflects the latest decisions made in this session (and check for any forked duplicate `RESEARCH_*.md` files in `docs/`).
3. If documents were edited or quantitative metrics/schemas were recalculated, confirm that [`/xsync`](../xsync/SKILL.md) (or [`/xlearn`](../xlearn/SKILL.md) for Playbook updates) verification has been completed (and if [`/xobsidian`](../xobsidian/SKILL.md) was used in the session—or if `<artifactDir>/scratch/xboost_state.md` lists any `DIRTY_IN_SESSION` vault notes—confirm those notes are synced and pass `BROKEN=0, ORPHANS=0, DUP_NEIGHBOR_GROUPS=0`).
4. *Sync Guard*: If uncommitted or unsynced state exists, advise the user or sync it before finalizing handoff.

---

### Step 2: Smart Hybrid 2A Routing (Explicit Topic vs. Bare `/xkickoff`)

Determine which path applies based on how the user invoked `/xkickoff` (or `/kickoff`):

#### Path A — Explicit Topic Provided (e.g. `/xkickoff <task>` or `"write /xkickoff so I can discuss X"`)
- **Zero Redundant Option Prompting**: Because the user has already stated what they want to do in the next chat, do **NOT** stop to ask them to pick an option, and do **NOT** clutter the response with competing options that distract from their chosen focus.
- Proceed **directly to Step 3** and output the **Pristine Kickoff Prompt** for their specified topic in the **same turn** (1-turn completion).
- If the user replies afterward with adjustments or scope tweaks, **rewrite the Kickoff Prompt** with those adjustments (never execute the task in the current chat).

#### Path B — Bare `/xkickoff` Invoked Without a Specific Topic (`Select Option First → Write Kickoff Later`)
1. **Turn 1 (Formulate & Ask Options ONLY — Do NOT Write the Kickoff Prompt Yet)**:
   - Analyze the active workspace roadmap, master plan, or presentation deck to formulate **orthogonal, high-impact next-step options** (sized to genuine roadmap branches, e.g. Options A/B/C) for the next conversation:
     * **Option A (Recommended — Direct Continuation)**: The immediate next logical subsection, slide, module, or task on the active roadmap.
     * **Option B (Technical Deep Dive / Parallel Scope)**: Evidence modeling, script execution, simulation, or multi-module pairing.
     * **Option C (Bookmark Polish / Synthesis)**: Returning to deferred modules/views, visualization polish, or executive review.
   - Present the options concisely (using the `ask_question` tool if available, or a clean numbered/lettered list in chat) and ask: *"Which focus would you like me to write the `/xkickoff` prompt for?"*
   - **STOP and end the turn without generating the long Kickoff Prompt block yet** (saves context tokens and avoids writing the wrong prompt).
2. **Turn 2 (User Selects Option → Write the Pristine Kickoff Prompt)**:
   - Once the user selects `Option A`, `Option B`, `Option C`, or states a custom focus, proceed immediately to **Step 3** and generate the **Pristine Kickoff Prompt** for that exact choice.
   - **Strictly obey the Terminal-Session Guardrail**: Do **NOT** execute the selected option in this chat; only output the Kickoff Prompt for the new chat!

---

### Step 3: Pristine Kickoff Prompt Synthesis & Smart Command Selector

#### A. Task-Smart Recommended Execution Command Selector
Select the exact `/x...` slash command pipeline for the bottom of the Kickoff Prompt based on the next session's workload (avoiding unnecessary PyTorch cold-start when files are already pinned, while activating [`/xlaya`](../xlaya/SKILL.md) whenever semantic triage or contradiction hunting is needed):

| Next Session Task Archetype | Recommended Command Line to Generate |
| :--- | :--- |
| **Standard Build / Debug / Solver / UI** *(Target files already pinned)* | [`/xbrief`](../xbrief/SKILL.md) `"[2-3 Word Title]"` [`/xboost`](../xboost/SKILL.md) `/goal` |
| **Architecture & Design Decision First** *(Needs inline grilling plan)* | [`/xbrief`](../xbrief/SKILL.md) `"[2-3 Word Title]"` [`/xplan`](../xplan/SKILL.md) |
| **Primary-Source API / Formula / DB Lookup → Implementation** | [`/xbrief`](../xbrief/SKILL.md) `"[2-3 Word Title]"` [`/xdeep-research`](../xdeep-research/SKILL.md) [`/xboost`](../xboost/SKILL.md) `/goal` |
| **Multi-File Doc Sync / Semantic Conflict Audit** | [`/xbrief`](../xbrief/SKILL.md) `"[2-3 Word Title]"` [`/xsync`](../xsync/SKILL.md) [`/xlaya`](../xlaya/SKILL.md) |
| **Post-Session Compound Learning / Playbook Ratchet** | [`/xbrief`](../xbrief/SKILL.md) `"[2-3 Word Title]"` [`/xlearn`](../xlearn/SKILL.md) [`/xlaya`](../xlaya/SKILL.md) |
| **Large Unpinned Corpus / Deep Research / Dataset Triage** | [`/xdeep-research`](../xdeep-research/SKILL.md) [`/xlaya`](../xlaya/SKILL.md) `"[2-3 Word Title]"` [`/xboost`](../xboost/SKILL.md) `/goal` *(or `/xbrief /xlaya`)* |
| **Elastic Cognitive Swarm / Orthogonal K-Vector Tournament / Evolutionary Ratchet Loop** | Append [`/xultra`](../xultra/SKILL.md) (e.g., `/xbrief "[2-3 Word Title]" /xboost /xultra /goal` or `/xdeep-research /xboost /xultra /goal`) |
| **Any Task Reading or Ratcheting Second Brain Knowledge** | Append [`/xobsidian`](../xobsidian/SKILL.md) (e.g., `/xbrief "[2-3 Word Title]" /xboost /xobsidian /goal`) |

#### B. Sidebar Title Rule (`2–3 Short Words, ≤ 22 Chars`) & 5-Part Kickoff Prompt Architecture

To prevent IDE conversation sidebars from truncating titles at ~24 characters (`Phase 5 Architecture Plannin...`, `Phase 0 PR Sweep And Bottl...`):
1. **Line 1 (`# [2–3 Short Word Title]`, `≤ 22 chars`)**: Put the **distinguishing subject/module noun first** in **2–3 short words** (`≤ 22 characters`). **NEVER** start Line 1 or `/xbrief "..."` with generic filler prefixes (`Objective:`, `Phase X`, `Architecture Planning`, `Forensic Audit`, `Comprehensive Study`). Good examples: `# DeepForest Walkthrough`, `# Group A Bottlenecks`, `# QuantEngine V6`, `# Ramintra Thesis`.
2. **Line 2 (`**Objective**: ...`)**: Place the full 1-sentence task objective on Line 2 right below the short `#` title.
3. **Bottom Command Sync**: Pass the **exact same 2–3 word title** inside `/xbrief "[2-3 Word Title]"` at the bottom of the prompt so the IDE's title generator locks onto the short name.

Generate a self-contained, copy-pasteable prompt block formatted inside a fenced markdown code block:

````markdown
```markdown
# [2–3 Short Word Title]
**Objective**: [Detailed 1-sentence task objective]

## Role & Operating Protocol
Operate as a Principal [Domain / Systems] Architect & Lead Engineer.
- Language Mode: [Primary Language or Bilingual Mode] (Maintain throughout this entire chat, zero language drift).
- Chat Panel Cleanliness: Strictly NO Mermaid blocks or LaTeX math ($) inside the agent chat bubble (use clean GFM tables/bullets in chat). Mermaid diagrams are supported in .md files and artifacts only.
- Formatting Standards: Native Unicode symbols only (→, •, ✓, ², etc.), GFM tables with outer boundary pipes.

## Scope & Target Files
- `[Primary File]` (Active document or module to edit or review)
- `[Reference Spec]` (SSOT / Master Roadmap)

## Locked Invariants & Session Decisions (DO NOT RE-ARGUE OR DRIFT)
1. [Locked Architecture, Schema & Cardinality Invariants: exact structural counts, API/UI/module contracts, or extensive partition conservation totals where applicable]
2. [Locked Domain & Boundary Guardrails: frozen/deferred zones, styling/design tokens, or mathematical/solver bounds (UL-01..UL-07) where applicable]
3. [Locked Verification & Regression Ratchets: live entrypoint verification commands and pinned regression assertions (UL-08) that the next session must keep 100% Green]

## Immediate Next Task
[Detailed, actionable instructions for what the agent should accomplish first in this new session].

## Recommended Execution Command
[Selected Task-Smart Command from Table 3.A using the exact same 2–3 word title, e.g.: /xbrief "[2-3 Word Title]" /xboost /goal]
```
````

### Step 4: Exit Checklist & User Guidance

Deliver the final instructions to the user:
1. **Copy the Kickoff Prompt**: Highlight the code block above for quick copying.
2. **Start Fresh Chat**: Direct the user to open a new conversation window in the IDE.
3. **Paste & Run**: Paste the block into the new chat and press Enter.
4. **Optional Adjustments**: Remind the user: *"If you want any tweaks to this kickoff prompt, reply here and I will rewrite the prompt block for you."*

---

## Quality Rubric

- [ ] Current session state verified against `git status` and documentation.
- [ ] **Sidebar Title Rule (`2–3 Short Words, ≤ 22 Chars`) enforced**: Line 1 (`# [2–3 Short Word Title]`) and `/xbrief "[2-3 Word Title]"` use 2–3 short words with the domain noun first and zero generic prefixes (`Objective:`, `Phase X...`), while the full sentence sits on Line 2 (`**Objective**: ...`).
- [ ] **Smart Hybrid 2A Routing enforced**:
  - If explicit topic given → wrote Kickoff Prompt immediately in 1 turn without redundant option questioning.
  - If bare `/xkickoff` given → presented Options A/B/C first (`ask_question` or concise list) and waited for selection before generating the Kickoff Prompt.
- [ ] **Strict Terminal-Session Guardrail enforced**: Never executed the chosen option inside the current chat; treated option selection strictly as a directive to write/rewrite the Kickoff Prompt.
- [ ] **Task-Smart Command Selector applied**: Included `/xlaya`, `/xplan`, `/xdeep-research`, `/xultra`, or `/xobsidian` when matched to the next session's workload, while keeping pinned-file build kickoffs lean (`/xbrief "[2-3 Word Title]" /xboost /goal`).
