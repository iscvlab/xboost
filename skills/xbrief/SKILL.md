---
name: xbrief
description: >
  Load related workspace markdown, extract structural architecture and locked invariants, then execute the user's task in the same turn (/xbrief, /brief).
  Use when the user runs /xbrief or /brief, or asks to read the docs then or brief then.
  Do NOT use for doc sync (/xsync), planning (/xplan), publishing (/xpublish), skill authoring (/xcreate-skill), or handoff (/xkickoff).
---

# `/xbrief` (Portable Workspace Briefing Engine)

Read a focused, high-authority set of **markdown documents** in the **current workspace**, extract overarching structural architecture and locked invariants, then execute the user's task in the same turn. Portable across any AI coding agent (cloud, IDE, CLI, or local LLM) across Windows, macOS, and Linux.

Do not crawl the entire tree. Do not dump raw file contents back to the user.

Red failure modes to prevent:
1. Suggesting answers, code, or structures from memory that contradict the workspace source of truth.
2. Tunneling into isolated keyword snippets in large documents while missing the overarching structural framework or section count.
3. Hallucinating content inside deferred zones marked for future research (`[RESEARCH FIRST]`, `[DEFERRED]`, `[FROZEN]`).

---

## When Not to Use

| Need | Use Instead |
| :--- | :--- |
| Construct an `implementation_plan.md` with inline grilling options | [`/xplan`](../xplan/SKILL.md) (or chain `/xbrief /xplan`) |
| Execute complex multi-file coding, debugging, or simulations | [`/xboost`](../xboost/SKILL.md) (or chain `/xbrief /xboost`) |
| Primary-source API/SDK lookup or 5-wave precedent harvesting | [`/xdeep-research`](../xdeep-research/SKILL.md) |
| Sync or rewrite documentation across the workspace | [`/xsync`](../xsync/SKILL.md) |
| Pre-flight security checks, upstream PRs, or QGIS plugin packaging | [`/xpublish`](../xpublish/SKILL.md) |
| Check conversation context compaction health | [`/xcontext`](../xcontext/SKILL.md) |
| Author or distill a global agent skill | [`/xcreate-skill`](../xcreate-skill/SKILL.md) |
| Ratchet post-session bug/optimization patterns into Playbooks or evolve universal laws | [`/xlearn`](../xlearn/SKILL.md) |
| Extract text and CSV tables from standalone PDFs or scanned images | [`/xocr`](../xocr/SKILL.md) |
| Non-intrusive desktop GUI automation (`Ghost Click` / `UIA` / `Set-of-Mark`) | [`/xmouse`](../xmouse/SKILL.md) |
| Write an end-of-session kickoff handoff prompt | [`/xkickoff`](../xkickoff/SKILL.md) |

If the task is exclusively one of these standalone workflows without needing a workspace doc briefing first, delegate to that skill and halt.

---

## Standard Operating Procedure (Every Run)

### Step 1: Parse the Task

* Extract slash arguments or the text following `/xbrief` (or `/brief`).
* Attached or explicitly named files serve as direct Tier-1 entry seeds, not the entire corpus.
* **Empty task rule**: If no task is provided, run discovery, display the Briefing Table, and **halt**. Do not invent unrequested work.

### Step 2: Semantic Seed Expansion

Extract core nouns, identifiers, and status words from the prompt, discarding generic stopwords. Expand seeds with first-degree structural and architectural synonyms:
* **Framework & Scaffolding**: `agenda` / `plan` → `framework`, `outline`, `phases`, `acts`, `stages`, `roadmap`, `curriculum`, `architecture`.
* **Authority & Invariants**: `rules` / `specs` → `invariants`, `master`, `ssot`, `constraints`, `guardrails`, `locked`, `frozen`.
* **Scope & Context**: `summary` → `overview`, `table of contents`, `executive summary`, `index`.

### Step 3: Discover & Prioritize Markdown

Search `*.md` in the current workspace, including hidden skill or configuration directories when host permissions allow.

* **Bounded Up-Tree Parent-Umbrella Discovery (Symmetric with [`/xsync`](../xsync/SKILL.md) `--federated` & [`/xlearn`](../xlearn/SKILL.md))**:
  * Inspect outbound relative links (`../`, `../../`) in root Markdown files and check the immediate parent directory (`..`).
  * When `cwd.parent` is a multi-repo umbrella directory (i.e., `cwd.parent != cwd`, `cwd.parent != ~`, and `cwd.parent.name.lower()` is **not** in `{desktop, documents, downloads, users, home, root, tmp, temp, var, etc}`), include top-level parent umbrella SSOTs (`../*PLAYBOOK*.md`, `../*PROTOCOL*.md`, `../*PLAN*.md`, `../*PORTFOLIO*.md` maintained via [`/xlearn`](../xlearn/SKILL.md)) in candidate discovery so shared cross-workspace pattern playbooks and architectural guardrails are automatically inherited.
* **Exclusions**: `.git`, `node_modules`, `dist`, `build`, `__pycache__`, `.venv`, vendor bundles, and **any directory containing an `.obsidian/` subfolder** (so Obsidian Second Brain notes never pollute or consume the 8-file Repository SSOT cap during standard `/xbrief` runs).
* **Strict Opt-In [`/xobsidian`](../xobsidian/SKILL.md) Combinator Rule (`/xbrief /xobsidian`)**:
  * **Default (Without `/xobsidian`)**: Do **not** read or query any Obsidian vault.
  * **Opt-In (`/xbrief /xobsidian`)**: When `/xobsidian` (or `/obsidian-vault`) is explicitly included in the command, keep the 8-file per-window discovery cap strictly for project repository SSOTs, and perform an additional bounded 2-Hop read via [`/xobsidian`](../xobsidian/SKILL.md) (`00 *Index*.md` → target `Hub - *.md` → task-relevant atomic notes) to include reusable domain formulas, precedents, or component specs in the Briefing Table.
* **Opt-In [`/xlaya`](../xlaya/SKILL.md) Sidecar Rule (`/xbrief /xlaya`)**:
  * When invoked alongside `/xlaya` (or `/laya`) in a multi-file unpinned documentation corpus or long specification, use [`/xlaya`](../xlaya/SKILL.md) (`shortlist` / `score`) to semantically rank heading sections before executing Pass B reads.
* **Opt-In [`/xultra`](../xultra/SKILL.md) Elastic Subsystem Scout Rule (`/xbrief /xultra`)**:
  * When invoked alongside `/xultra` across a multi-root workspace or large specification corpus, fan out **Elastic Read-Only Subsystem Scouts** (1 scout per subsystem root or spec cluster, each applying the per-window 8-file Pass-B reading bound) to return **Telegraphic Briefing Table Rows** without bloating the main thread's context window.
* **Discovery & Reading Tools**: Use native file-reading (`read_file` / `view_file`) and platform search (`rg --hidden`, `grep`, or PowerShell `Select-String`). When a user-pinned or canonical workspace specification exists only as a `.pdf` or raster image with no extracted `.md` equivalent yet, automatically invoke [`/xocr`](../xocr/SKILL.md) ([`../xocr/scripts/ocr_runner.py`](../xocr/scripts/ocr_runner.py), using `--pages` for targeted Pass A/B slicing) to extract `extracted_document.md` and `table_p*.csv`.

#### Authority Hierarchy (Cap at 8 Files per Context Window)

Rank discovered documents using this 4-tier authority ladder rather than raw keyword frequency:

1. **Tier 1 (Explicit Intent)**: User-pinned or directly specified file paths.
2. **Tier 2 (Canonical SSOT & Version Leaders)**: Master specifications, architectural roadmaps, and latest version files (e.g. `*_v5` strictly supersedes and suppresses `*_v4` and earlier iterative drafts).
3. **Tier 3 (Active Operational Plans)**: Active sprint plans, handoffs, and implementation trackers.
4. **Tier 4 (Contextual Hits)**: Ranked by search relevance solely as a tiebreaker among equal-tier files.

#### The Two-Pass Reading Protocol for Large Documents (> 200 lines)

Never grep isolated keyword lines without establishing structural context:
* **Pass A (Structural Skeleton & Cardinality)**: Read the document header, Table of Contents, Executive Summary, and Level 1–2 Headings (`#`, `##`) via `read_file`. Determine the exact declared structural count (e.g. number of acts, phases, tiers, or modules).
* **Pass B (Targeted Deep Dive)**: Read only the specific line ranges matching the user's task.
* **Supersession Invariant**: When multiple versioned files exist, inspect only the latest canonical version.

### Step 4: Boundary & HTML Gates

* **Deferred Zone Gate**: Actively scan for explicit boundary markers: `[RESEARCH FIRST]`, `[DO NOT EDIT]`, `[FROZEN]`, `[TBD]`, `[POSTPONE]`. Note any areas marked as out-of-scope or awaiting user research.
* **HTML Gate**: Skip HTML files by default. Open an HTML file only if the task explicitly references an active web page, dashboard, or layout file by name. Never crawl arbitrary web assets.

### Step 5: Briefing Table

Present the structured briefing table before proceeding:

| Source Document | Authority Tier | Structural Framework / Cardinality | Locked Invariants to Obey | Deferred / Do-Not-Touch Zones |
| :--- | :---: | :--- | :--- | :--- |
| `path/to/spec.md` | SSOT (vLatest) | Declared count (e.g. 6 Acts, 4 Phases) | Core rules, performance metrics | Explicitly deferred items |

* If two authoritative documents conflict, state the contradiction explicitly before editing or generating content.
* Public status terms (`LIVE`, `REGISTERED`, `PREPARED`, `IN PIPELINE`, `DRAFT`) belong to [`/xsync`](../xsync/SKILL.md); adhere to that vocabulary without inventing alternate statuses.
* Ensure all user-facing text uses direct Unicode characters (e.g. `→`, `•`, `✓`, `²`) and zero LaTeX delimiters.

### Step 6: Pre-Flight Verification & Composable Execution Handoff

Before generating output, verify alignment against the Briefing Table:
1. **Cardinality Check**: Does the planned outline match the exact number of phases, acts, or sections declared in the SSOT?
2. **Boundary Check**: Does the planned output avoid answering or populating sections marked as "Deferred" or "Research First"?
3. **Alignment Gate**: If the user prompt appears to ask for a structure that contradicts the locked SSOT, highlight the discrepancy and confirm before generating.
4. **Execute or Chain**:
   * **Standalone `/xbrief <task>`**: Complete the parsed task within the validated boundaries in the same turn.
   * **Chained `/xbrief /xplan`**: Pass the Briefing Table invariants directly into [`/xplan`](../xplan/SKILL.md) Phase 1 to construct `implementation_plan.md`.
   * **Chained `/xbrief /xboost`**: Lock the Briefing Table invariants into [`/xboost`](../xboost/SKILL.md) Phase 1 Goal Contract and execute.

---

## Quality Rubric

- [ ] Task parsed cleanly, or empty-task command stopped immediately after the table.
- [ ] Markdown discovered via authority hierarchy (SSOT and latest version precedence over hit count); capped at 8 files per context window (or sharded across [`/xultra`](../xultra/SKILL.md) subsystem scouts).
- [ ] Large documents (> 200 lines) read using Pass A (Structural Skeleton/Cardinality) before Pass B (Section Deep Dive).
- [ ] Deferred zones, frozen markers, and out-of-scope sections identified.
- [ ] Briefing Table rendered with Cardinality, Invariants, and Deferred Zones.
- [ ] Task executed (or chained to `/xplan` / `/xboost`) in strict alignment with discovered scaffolding and boundaries.
