---
name: xcreate-skill
description: >
  Build, distill, evolve, and audit global agent skills with universal laws (/xcreate-skill, /create-skill).
  Use when running /xcreate-skill or /create-skill, or when creating, distilling, upgrading, evolving, or auditing
  global agent skills. Do NOT use for post-session playbook ratcheting (/xlearn), workspace doc sync (/xsync), or package release checks (/xpublish).
---

# Universal Skill Creator & Law Auditor (`/xcreate-skill`)

Authoring, distilling, evolving, and verifying production-grade global agent skills across **any AI coding agent (cloud, IDE, CLI, or local LLM)** on Windows, macOS, and Linux.

This skill synthesizes four core frameworks:
1. **The [`/xboost`](../xboost/SKILL.md) Protocol**: 4-phase engineering lifecycle (Red Invariant Gate → Ponytail × 5-Gate Universal Law Filter → Dual-OS Surgical Build → Ruthless 3-Tier Verification).
2. **`writing-great-skills` Discipline**: Information hierarchy, progressive disclosure, leading words, single-source-of-truth (`SSOT`) co-location, and context-load vs. cognitive-load optimization.
3. **The 5-Gate Universal Law Falsification Protocol**: Pre-proposal counter-domain stress testing (`Archetypes A × B × C`), Agent-Process vs. Domain-Equation separation, and mathematical boundary auditing so project-specific equations or scripts never leak into global skills.
4. **Universal Cross-Platform Globalization**: Physical directory allocation, dual-OS path normalization (Windows PowerShell + macOS/Linux bash), and zero-breakage cloud synchronization (OneDrive / Google Drive).

---

## 1. Scope & Universal Globalization Policy

Every agent skill authored or upgraded via `/xcreate-skill` **MUST reside in the Global Agent Skills Root (`<GLOBAL_SKILLS_ROOT>`)** so that it is instantly accessible across **every workspace** and synchronized across **every device and AI agent** (Windows, macOS, and Linux workstations):

| Target Path | Physical Cloud Storage / Multi-Agent Link | Behavior Across Workspaces & Devices |
| :--- | :--- | :--- |
| **`<GLOBAL_SKILLS_ROOT>/<skill-name>/`**<br>*(e.g., `~/.agents/skills/<name>/` or `~/.<agent>/skills/<name>/`)* | **Cloud-Synced SSOT (OneDrive / Git)** linked via NTFS Junctions or symlinks across all installed local agent roots (`~/.agents/skills`, `~/.<agent>/skills`, `~/.<agent>/config/skills`) | **Universal Globalization**: Automatically loaded into every workspace across all local & cloud AI agents on all machines. Real-time background sync via cloud storage. |

> [!IMPORTANT]
> **The Universal Globalization Invariant (Zero Project-Local Silos)**:
> Never isolate reusable skills inside a single project's workspace-local `.agents/skills/<name>/` folder. Project-local silos are invisible when opening other repositories and cause version drift between machines. Always write directly to your Global Agent Skills Root (`<GLOBAL_SKILLS_ROOT>/<name>/`).

> [!IMPORTANT]
> **The NTFS Junction & Real Directory Rule**:
> When authoring global skills on Windows where the global agent skills root is an NTFS junction to a cloud-synced folder (`OneDrive`), **always create real directories** inside `skills/<name>/`. Never create nested secondary junctions, as IDE file watchers and Node.js globbers refuse to traverse recursive reparse points.

> [!TIP]
> **Global Git Ledger & Rollback Protection (Dual-OS)**:
> When the global skills root is version-controlled via Git, commit the change after creating or updating a skill:
> ```bash
> git -C "<GLOBAL_SKILLS_ROOT>" add -A && git -C "<GLOBAL_SKILLS_ROOT>" commit -m "feat(skills): update <skill-name>"
> ```

---

## 2. Ingestion Modes (`Mode A`, `Mode B`, `Mode C`)

Operate in one of three distinct modes based on user intent:

### Mode A: Session Workflow Distillation ("Make this a new skill")
* Triggered when the user says *"make this a skill"*, *"package what we just did"*, or *"turn this workflow into a reusable skill"*.
* Reads the active conversation history / transcript (`transcript.jsonl`), extracts the sequence of successful commands, tool calls, and output schemas, strips debugging detours, and synthesizes a repeatable workflow skill.

### Mode B: Greenfield Domain / Tool Architecture ("Create a skill for X")
* Triggered when building a brand-new skill from an API, library documentation, standard, or domain (e.g., QGIS analysis, Grasshopper solver, Docx processing).
* Conducts a focused, non-bloated 3-question interview (`Intent`, `Tools/Inputs/Outputs`, `Edge Cases`).

### Mode C: Post-Session Skill Evolution & Universal Law Ratchet → Delegated to [`/xlearn`](../xlearn/SKILL.md)
* Post-session compound learning (`Tier A` autonomous updates to `COMPOUND_LEARNING_PLAYBOOK.md` and specialized domain Playbooks with built-in [`/xsync`](../xsync/SKILL.md) `--federated` mirror closure) and `Tier B` consent-gated global skill evolution are owned by **[`/xlearn`](../xlearn/SKILL.md)**.
* Whenever the user asks to distill session bug fixes, benchmark speedups, reviewer guardrails (`FALS-*` / `GOV-*`), or candidate universal laws after a task, route directly to **[`/xlearn`](../xlearn/SKILL.md)** (which enforces the mandatory 5-Step Pre-Proposal Falsification Sieve, the 5 Counter-Paradigm Stress Checks, and the Wave 2A Blind Counter-Domain Critic before any global skill edit is proposed).
* When a candidate universal law survives [`/xlearn`](../xlearn/SKILL.md)'s Tier B Blind Critic gate and receives explicit user approval, return to Section 3–4 below to apply the surgical skill edit and run [`/xpublish`](../xpublish/SKILL.md) (`audit_engine.py --platform skill`).

---

## 3. The 4-Phase XBoost Skill Creation & Evolution Lifecycle

```mermaid
flowchart TD
    P1["Phase 1: THE RED INVARIANT & PRE-PROPOSAL GATE\n(Failure Mode, Agent-Process Inversion, 2 Trigger Probes)"] --> P2["Phase 2: PONYTAIL LADDER & 5-GATE UNIVERSAL LAW FALSIFICATION\n(3-Bucket Numerics + 3-Domain Stress Test + 9-Point Math Audit + SSOT Owner)"]
    P2 --> P3["Phase 3: DUAL-OS SURGICAL EXECUTION\n(Front-loaded SKILL.md <= 500 lines, POSIX paths, UTF-8 header)"]
    P3 --> P4["Phase 4: RUTHLESS 3-TIER VERIFICATION\n(Static YAML Lint, Live CLI Counter-Anchor Probe, audit_engine.py)"]
```

---

### Phase 1: The Red Invariant Gate (Pre-Creation / Pre-Upgrade)

Answer these three questions before drafting or proposing edits:

1. **What is the Red Agent Failure Mode?**
   * What does the AI agent get wrong without this skill or rule? (e.g., trusts green linters without calling the live entrypoint, extrapolates outside bracketed bounds, spawns redundant subagents, fails on cross-platform paths).
2. **Invocation Decision (Context Load vs. Cognitive Load)**:
   * **Model-Invoked** (Default): Keeps a rich `description` (`≤ 400` chars target) with leading words, positive triggers, and an explicit `Do NOT use for...` exclusion clause. Contributes context load every turn; agent can trigger it autonomously.
   * **User-Invoked**: Set `disable-model-invocation: true`. Note that `description` is **still mandatory in YAML frontmatter** (write a concise 1-line human-facing summary; positive/negative trigger clauses become optional).
     > [!WARNING]
     > **`disable-model-invocation: true` suppresses prompt context**: In host agent runtimes, setting this flag completely strips the skill from the agent prompt's `<skills>` catalog. Only set this for manual user-typed commands.
3. **Bidirectional Trigger & Behavioral Probes (`A_pos ∧ A_neg`)**:
   * **Positive Probe (`A_pos`)**: A prompt or input fixture that *must* trigger/pass the skill or rule.
   * **Negative Counter-Anchor (`A_neg`)**: A related out-of-scope prompt or counter-domain fixture that *must NOT* falsely trigger or break under the rule.

---

### Phase 2: Ponytail Ladder, 3-Bucket Numeric Rule & 5-Gate Universal Law Falsification

#### A. The Ponytail Senior Dev Filter (Rungs 1–4)
* **Rung 1 (YAGNI / Rule Check)**: Does this actually need a new skill or rule? If the model already obeys it by default (**No-Op** in `writing-great-skills`), delete it.
* **Rung 2 (Tool & SSOT Reuse)**: Do native tools, MCP servers, or an existing owner skill already cover this? If yes, point to the existing owner (`[label](../skill/SKILL.md)`) rather than duplicating prose.
* **Rung 3 (Structure Selection)**: Choose **Workflow Archetype** (ordered steps + completion criteria), **Task Toolkit Archetype** (independent sub-actions), or **Reference Archetype** (flat peer rules).
* **Rung 4 (Code vs. No-Code)**: Default to **Pure Instruction (Zero Code)**. Only add `scripts/<name>.py` for deterministic, 100% domain-agnostic parsing/auditing using Python stdlib (`argparse`, `pathlib`, `json`, `re`, `ast`).

#### B. Core Invariant 1: The 3-Bucket Numeric Litmus Test & Zero-Persona Neutrality
Classify every numeric bound (`≤ N`, `N..M`, `< N`) into one of three buckets:
1. **Bucket 1 — Physical / Platform Constants (Keep & Cite Source)**: Hardware, model, or runtime limits (`512`-token `ModernBERT` window, `< 30s` synchronous tool timeout, `2-Hop` GraphRAG diameter, `≤ 400`-char target / `≤ 500`-char advisory YAML description budget, `≤ 500`-line `SKILL.md` progressive disclosure budget).
2. **Bucket 2 — Per-Window Cognitive Working-Set Bounds (Keep Per Window, Scale via `/xultra` Shards)**: Per-thread reading caps (such as [`/xbrief`](../xbrief/SKILL.md)'s `8`-file Pass-B cap per single context window) paired with horizontal [`/xultra`](../xultra/SKILL.md) shard scaling when corpus size exceeds one window.
3. **Bucket 3 — Arbitrary Task / Subagent Quotas, Snapshot Counts & Persona Leaks (Strictly Forbidden)**: Never hardcode fixed subagent headcounts (`3+2`, `4–12`, `2–4 scouts`), arbitrary output word/line caps (`≤ 150 words`, `1–2 notes`, `< 30 lines`), transient dataset row counts (`14,203 rows`), or personal hardware/persona strings into global skill instructions.

#### C. Core Invariant 2: The 5-Gate Universal Law Falsification Protocol
Whenever Mode A or [`/xlearn`](../xlearn/SKILL.md) distills a rule, mathematical invariant, or verification probe into any global skill, it **MUST pass all 5 gates in order**:

| Gate | Falsification Check | Pass / Conditioning / Removal Criterion |
| :---: | :--- | :--- |
| **Gate 1** | **Domain-Jargon & Vocabulary Strip** | Strip 100% of source-project nouns, domain metrics, and filenames. Express strictly in universal systems primitives: `Input/Control (X)`, `Output/Objective (Y, J)`, `Active_Regime(X)`, `Step Measure (Δμ)`, `Candidate Superset vs. Exact Subset (S_cand ⊇ S_exact)`, `Parent vs. Child + Remainder (P = ∪ C_i ∪ P_rem)`. |
| **Gate 2** | **3-Domain Counter-Paradigm Stress Test (`Archetypes A × B × C`, `∀` vs. `∃`)** | Test against **(A) Continuous/Stateful Numerical or Physics Solver**, **(B) Discrete/Web UI/API/CRUD System**, and **(C) Non-Code Research/Docs/Knowledge Graph**—and explicitly check for conflicts against **Regularization/Pareto trade-offs, Exact Jacobians, Lazy DAGs, `O(1)` Prefix Trees, and Transient Retry**. If falsified on *any* legitimate paradigm, **prune (`REMOVE`)** or prefix an explicit **Context-Conditioned Branch Guard (`When [Condition C] holds: ...`)**. |
| **Gate 3** | **9-Point Mathematical & Regime Boundary Audit** *(Canonical table in [`/xlearn` §3](../xlearn/SKILL.md) & [`deep_audit_protocol.md`](../xboost/references/deep_audit_protocol.md))* | Verify that equations and runtime probes do not fail on affine offsets (`y_eq ≠ 0`), non-zero intercepts (`Y(0) ≠ 0`), intensive measures (means/rates/temps), intentional deadbands/free budget zones (`τ_free`), stateful warmup lookbacks (`W > 1`), IEEE-754 float/serialization reductions (`rtol/atol`), `@decorator` wrappers, exact finite-difference Jacobians (`∂f/∂x`), or regularized `L_data + λ·R_sec` trade-offs. |
| **Gate 4** | **Ponytail YAGNI, No-Op & "Delete-Over-Debug" Filter** | Delete rules that (a) the model obeys by default (`No-Op`), (b) duplicate an existing `UL-01..UL-08` runtime probe, (c) force project-specific ceremony (e.g., mandatory `.bat`+`.sh` launchers) onto repos that don't need them, or (d) clash with standard language idioms or global typography rules. |
| **Gate 5** | **Cross-Skill SSOT Co-Location & Pointer-Over-Paste** | Every universal law has **one canonical owner file** (e.g., `UL-01..UL-08` live in [`../xboost/references/deep_audit_protocol.md`](../xboost/references/deep_audit_protocol.md); `N × K × C × T` swarm sizing lives in [`../xultra/SKILL.md`](../xultra/SKILL.md); the 9-Point Mathematical Boundary Table & 3-Tier Playbook Ratchet live in [`../xlearn/SKILL.md`](../xlearn/SKILL.md)). Never copy-paste 20-line tables across multiple skills; use a 1–2 line summary + relative **Context Pointer**, and keep `SKILL.md ≤ 500` lines. |

---

### Phase 3: Dual-OS Surgical Execution

When authoring or editing skill files, enforce strict cross-platform standards:

#### 1. Structure Blueprint & Progressive Disclosure (`≤ 500` Lines)
```text
skill-name/
├── SKILL.md              ← Required. Frontmatter + Core Steps & Invariants (≤ 500 lines)
├── references/           ← Optional. Deep taxonomies/matrices loaded on-demand via context pointers
└── scripts/              ← Optional. Universal, 100% domain-agnostic CLI helpers (stdlib-first)
```

#### 2. YAML Frontmatter Template (`≤ 400`-Char Target Budget)
```yaml
---
name: [lowercase-hyphenated-name-max-64-chars]
description: >
  [Leading-word summary in 1 sentence].
  Use when [primary triggers, exact slash commands, and distinct branches].
  Do NOT use for [explicit negative exclusions to prevent false triggers].
---
```

> [!NOTE]
> **Universal Skill Schema Standardization**: Universal agent skills standardize on `name` and `description`. Avoid non-standard fields like `argument-hint: "<task>"`, as non-standard keys can break slash autocomplete indexing in some agent runtimes.

#### 3. Dual-OS, Shell Escaping & Portability Invariants
* **POSIX Forward Slashes**: Zero backslashes (`\`) inside markdown links `[...](...)`.
* **No Hardcoded Machine User Paths**: Never hardcode `C:\Users\<User>\...` or `/Users/<username>/...`. Use relative paths (`../<skill>/SKILL.md`) or home-relative `~/` and `$env:USERPROFILE` / `%APPDATA%`.
* **PowerShell & Bash Backtick Safety in One-Liners**: Inside `python -c "..."` double-quoted commands, never write literal backticks `` ` `` (PowerShell treats `` ` `` as an escape character and Bash treats `` `...` `` as command substitution); always use hex escape `\x60` inside regexes.
* **UTF-8 & Bytecode Python Header Standard**: Every helper script in `scripts/*.py` must start with `sys.dont_write_bytecode = True`, `sys.stdout.reconfigure(encoding="utf-8")`, and pass `encoding="utf-8", errors="replace"` to all `subprocess.run(..., text=True)` calls.

---

### Phase 4: Ruthless 3-Tier Verification (The Green Gate)

A skill creation or evolution task is **NOT finished** until it passes all three verification tiers:

```mermaid
flowchart LR
    T1["Tier 1: Static YAML & Budget Linter"] --> T2["Tier 2: 5-Gate Universal Law & Live CLI Probe"] --> T3["Tier 3: Automated audit_engine.py --platform skill"]
```

#### Tier 1: Static Frontmatter & Progressive Disclosure Linter
* `name` matches `^[a-z0-9-]+$` (`≤ 64` chars) and matches folder name.
* `description` is present (`≤ 400` chars target, `≤ 500` chars advisory ceiling, `1024` hard max) and includes both positive triggers and `Do NOT use for...` (unless `disable-model-invocation: true`).
* `SKILL.md` is `≤ 500` lines (disclosing deep reference tables into `references/*.md` when needed) and contains zero raw LaTeX math macros (`\rightarrow`, `\times`, `\approx`).

#### Tier 2: 5-Gate Universal Law, Anti-Hardcode & Live CLI Counter-Anchor Scan
* **Universal Globalization Check**: Confirm the skill lives in the Global Agent Skills Root (`<GLOBAL_SKILLS_ROOT>/<name>/`, never in a single project's workspace `.agents/skills/`).
* **Zero-Hardcode & Secret Audit**: Scan all `.md`, `.py`, `.sh`, `.json` files using the exact case-sensitive boundary patterns enforced by [`audit_engine.py`](../xpublish/scripts/audit_engine.py):
  * **Windows Path**: `(?i)\b([a-z]:[/\\]users[/\\](?!<)[a-zA-Z0-9_\-\.]+)`
  * **macOS Path** *(case-sensitive `/Users/` with trailing `/` so REST routes like `/users/profile` never false-positive)*: `(?:^|[\s"'`=:(])(/Users/(?!<|shared\b|runner\b)[a-zA-Z0-9_\-\.]+/)`
  * **Linux Path**: `(?:^|[\s"'`=:(])(/home/(?!<)[a-z0-9_\-\.]+)`
* **3-Bucket Numeric & 5-Gate Over-Specific Equation Sweep**: Verify zero Bucket 3 magic quotas, zero personal hardware/project strings, and zero unqualified Gate 3 anti-patterns (`x = 0 → y = 0`, `d log|Y|/d log α == p`, memoryless `f(x)[k:] == f(x[k:])`, intensive `sum(Child) == Parent`, or `callable.__module__ == prod_module`).
* **Live CLI Smoke & Bidirectional Counter-Anchor Probe (`scripts/*.py`)**:
  * Never rely on `py_compile` alone (`Anti-"Green-Linter" Gate`). For every modified or created script in `scripts/*.py`:
    1. Run `python -m flake8 --max-line-length=120 <script.py>` (`0` violations) and `python <script.py> --help` (`exit code 0`).
    2. Execute a live **Bidirectional Counter-Anchor Probe (`A_pos ∧ A_neg`)**: verify the script returns `0 Blocking` on valid edge-case inputs (`A_pos`, e.g., bold Markdown links `**[Label](https://...)**`, `$100 to $200` currency, paths with spaces) and accurately flags a synthetic defect (`A_neg`).

#### Tier 3: Automated Pre-Flight Engine Verification (`audit_engine.py --platform skill`)
Execute [`/xpublish`](../xpublish/SKILL.md) with `--platform skill` across all created or modified skills (`<SKILLS_ROOT>` is your active skills directory):

```bash
python "<SKILLS_ROOT>/xpublish/scripts/audit_engine.py" "<SKILLS_ROOT>/<skill-name>" --platform skill
```
Must exit with **`VERDICT: PASS`** (`0` blocking issues, `0` unaddressed advisories) before committing to the global skills git ledger.

---

## 4. Composable XBoost Ecosystem Chaining (`/xcreate-skill` × `/x*`)

| Chained Command | Execution Upgrade |
| :--- | :--- |
| **`/xcreate-skill` + [`/xlearn`](../xlearn/SKILL.md)** | **Tier B Consent-Gated Skill Evolution Handoff**: [`/xlearn`](../xlearn/SKILL.md) executes the 5-Step Pre-Proposal Falsification Sieve and Wave 2A Blind Counter-Domain Critic; once the user approves a universal upgrade, `/xcreate-skill` applies the surgical edit and runs Phase 4 verification. |
| **`/xcreate-skill` + [`/xdeep-research`](../xdeep-research/SKILL.md)** | **Primary-Source Spec & Equation Lock**: Inspects local pinned manifests/SDKs or authoritative literature in Wave 1 before drafting Mode B tool skills or mathematical laws (`0` hallucinated CLI flags or unverified equations). |
| **`/xcreate-skill` + [`/xboost`](../xboost/SKILL.md)** | **4-Phase Red→Green Skill & CLI Engineering**: Applies the 5-Gate Universal Law Falsification Protocol, authors stdlib-first CLI verifiers (`scripts/*.py`), and runs live `A_pos ∧ A_neg` counter-anchor probes in Phase 4. |
| **`/xcreate-skill` + [`/xultra`](../xultra/SKILL.md)** | **3-Wave Adversarial Skill Audit Swarm (`Maker ≠ Checker`)**:<br>• **Wave 1**: Runs Law 1 deterministic `audit_engine.py --platform skill` + 3-Bucket & Gate 3 regex scans.<br>• **Wave 2A (`Blind Counter-Domain Critic Subagent`)**: Spawns an independent Read-Only Critic (`TypeName="research"`) to attack candidate rules across **Archetypes A × B × C** and the 5 Counter-Paradigm Stress Checks, classifying items into **`REMOVE (Ponytail YAGNI / Fixed-Equation / Covered by Existing UL)`** vs. **`SURGICAL FIX`**.<br>• **Wave 2B**: Applies approved surgical edits, verifies cross-skill SSOT pointers, and re-runs `audit_engine.py --platform skill`. |
| **`/xcreate-skill` + [`/xsync`](../xsync/SKILL.md)** | **Cross-Skill Relation-Set Sync**: Sweeps all sibling skills in `<GLOBAL_SKILLS_ROOT>/` sharing modified CLI flags, mode names, regexes, or `UL` law IDs so zero cross-skill contradictions remain. |
| **`/xcreate-skill` + [`/xobsidian`](../xobsidian/SKILL.md)** *(Strict Opt-In)* | Without `/xobsidian`, never touch any Obsidian vault. When `/xobsidian` is included, ratchet converged `#tier/method` or `#tier/package` ecosystem notes into `VAULT_ROOT` after Tier 3 passes (`BROKEN=0`, `ORPHANS=0`, `DUP_NEIGHBOR_GROUPS=0`). |

---

## 5. Post-Creation / Evolution Summary Rubric

When reporting a newly created or upgraded skill to the user, provide:
1. **Pruned Project-Specific Items vs. Approved Universal Laws** *(for Mode C upgrades)*: What session-specific items were filtered out and why.
2. **3-Domain Translation Proof (`Archetypes A × B × C`)**: Concise proof that every added law holds across Continuous Solvers, Discrete Web/API Systems, and Non-Code Research/Docs.
3. **SSOT Location & Changed Files**: Clickable `file://` links to modified `SKILL.md`, `references/*.md`, and `scripts/*.py`.
4. **Verification Scorecard**: Confirmation that `audit_engine.py --platform skill`, `flake8`, live `A_pos ∧ A_neg` CLI probes, and global skills Git commit passed `100% CLEAN`.
