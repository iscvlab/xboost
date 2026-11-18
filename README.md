# XBoost - Composable `/x*` Agent Skills Ecosystem & Verification Harness

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-v3.6.0-blue.svg)](https://github.com/iscvlab/xboost)
[![Skills](https://img.shields.io/badge/Suite-15_Composable_%2Fx_Skills-005FB8)](#3-the-15-skill-suite)
[![CLI Engines](https://img.shields.io/badge/CLI_Gates-10_Python_Engines_(100%25_Recall)-059669)](#5-bundled-zero-dependency-cli-engines)
[![Agents](https://img.shields.io/badge/Agents-Any_AI_Agent_(Cloud_•_IDE_•_CLI_•_Local_LLM)-8A2BE2)](#6-universal-installation)
[![Dual-OS](https://img.shields.io/badge/Dual--OS-Windows_•_macOS_•_Linux-success)](#6-universal-installation)
[![Upstream OSS](https://img.shields.io/badge/Upstream_Contributions-24_PRs_%2B_1_Hold_%26_Benchmarks_(4x--1735x_Speedup)-D97706)](#45-empirical-benchmark--token-economics-benchmarksbenchmark_reportmd)

**XBoost** (`iscvlab/xboost` `v3.6.0`; latest remote tag [`v3.5.0`](https://github.com/iscvlab/xboost/releases/tag/v3.5.0)) is a unified, composable **`/x*` skill ecosystem, 4-Tier cross-workspace compound learning framework, and deterministic CLI verification harness** for AI coding agents engineered by **[ISCV | Isocurve Research Lab (`@iscvlab`)](https://github.com/iscvlab)**. Type `/x` in any supported IDE or CLI—or load the portable `SKILL.md` protocols into **any AI coding agent — cloud, IDE, CLI, or local LLM (`Ollama`, `vLLM`, `LM Studio`, `OpenHands`, `Cline`, `Continue`, `Aider`, `Claude Code`, `Codex`, `Cursor`, `Grok`, `Gemini / Antigravity`, or custom agent frameworks)**—to surface all **15 composable skills** (`xboost`, `xbrief`, `xcontext`, `xcreate-skill`, `xdeep-research`, `xkickoff`, `xlaya`, `xlearn`, `xmouse`, `xobsidian`, `xocr`, `xplan`, `xpublish`, `xsync`, `xultra`), the **[Cross-Workspace Compound Learning Playbook `L1` Hub (`docs/COMPOUND_LEARNING_PLAYBOOK.md`)](docs/COMPOUND_LEARNING_PLAYBOOK.md)** (`→` 4 `L2` domain shards `docs/playbooks/PLAYBOOK_1A..1D_*.md`), and **10 bundled Python CLI & MCP engines** (`22,237` LOC) on **Windows, macOS, and Linux**.

Sister toolkits & **24 upstream open-source PRs + 1 Hold (`10 MERGED`)**: **[xlaya](https://github.com/iscvlab/xlaya)** (5-Profile System 1 → System 1.5 Semantic Decision, 4-PC Whitened Code-Graph Sieve, `M_avail` Regime Shield, Conformal `ToolGate`, Ensemble Jury, `vega-U` Triage & Wallacei `v2.7` K-Fold OOF `NSGA-II` MOO `v2.4.0` local; latest remote tag [`v2.3.0 LIVE`](https://github.com/iscvlab/xlaya/releases/tag/v2.3.0)) · **[mcp-bridges](https://github.com/iscvlab/mcp-bridges)** (8 Model Context Protocol automation bridges — `330.75 chars` Mean YAML — for AutoCAD, QGIS, Rhino 3D, Grasshopper, Adobe Illustrator, and Figma with Parallel-Brains Single-Mouse serialization · **Selected for the [XERJ Corpus Hub](https://hub.xerj.org)**) · **[xocr](https://github.com/iscvlab/xocr)** (Hybrid Document AI, Two-Stage LaTeX `booktabs` & HTML Table Surgery, and Local `SCB 10X Typhoon-OCR v1.5` × `Baidu Unlimited-OCR-2` Engine `v2.4.0` local; latest remote tag [`v2.1.0 LIVE`](https://github.com/iscvlab/xocr/releases/tag/v2.1.0) · **[Upstream PR #16 to `scb-10x/typhoon-ocr` (`OPEN`)](https://github.com/scb-10x/typhoon-ocr/pull/16)**) · **[sse-space-syntax](https://github.com/iscvlab/sse-space-syntax)** (High-performance C++/Rust/Python Space Syntax & Isovist Engine `v1.1.1 LIVE`) · **Batch 0 Agent & Document AI Infrastructure** (**[Upstream PRs #2922–#2927 to `xerj-org/xerj`](https://github.com/xerj-org/xerj/pulls?q=is%3Apr+author%3Anapattan)** — [`#2922`](https://github.com/xerj-org/xerj/pull/2922), [`#2923`](https://github.com/xerj-org/xerj/pull/2923), [`#2924`](https://github.com/xerj-org/xerj/pull/2924), [`#2925`](https://github.com/xerj-org/xerj/pull/2925), [`#2926`](https://github.com/xerj-org/xerj/pull/2926), [`#2927`](https://github.com/xerj-org/xerj/pull/2927) `6/6 MERGED`) · **Group A Geospatial & Vision** ([`opengeos/geoai #960`](https://github.com/opengeos/geoai/pull/960) `MERGED`, [`Weecology/DeepForest #1449`](https://github.com/Weecology/DeepForest/pull/1449) `74.4×–421.3×` `MERGED`, [`gboeing/osmnx #1412`](https://github.com/gboeing/osmnx/pull/1412) `40.2×` `MERGED`, [`martibosch/pylandstats #77`](https://github.com/martibosch/pylandstats/pull/77) `4.0×` `OPEN`, [`opengeos/segment-geospatial #569`](https://github.com/opengeos/segment-geospatial/pull/569) CodeRabbit `APPROVED`) · **Group B Climate Risk, ESG & Urban Physics** ([`CLIMADA-project/climada_python #1350`](https://github.com/CLIMADA-project/climada_python/pull/1350) `69.9×` & `11.7×` `MERGED` & [`#1349`](https://github.com/CLIMADA-project/climada_python/pull/1349) `OPEN`, [`ladybug-tools/uwg #292`](https://github.com/ladybug-tools/uwg/pull/292) `1,735.6×` `OPEN`, [`os-climate/physrisk #651`](https://github.com/os-climate/physrisk/pull/651) `32.5×` & `1,669.6×` `OPEN`, [`Deltares/hydromt #1566`](https://github.com/Deltares/hydromt/pull/1566) `27.5×` `OPEN`, [`natcap/invest #2813`](https://github.com/natcap/invest/issues/2813) & [`#2829`](https://github.com/natcap/invest/issues/2829) `23.1×` & `18.1×` `Hold`) · **Group C Developer Tooling** ([`mufeedvh/code2prompt #348`](https://github.com/mufeedvh/code2prompt/pull/348)).

---

## ⚡ TL;DR - Capabilities & Performance at a Glance (`v3.6.0`)

* **Composable 5-Stage Lifecycle (`Stage 1 → Stage 5`) + Dedicated `/xlearn` Compound Learning (`Tier A` / `Tier B`)**: Chain any combination of `/x*` slash skills in a single prompt (`/xbrief /xdeep-research /xboost /xlearn /xsync /xobsidian /xultra /goal`). XBoost automatically normalizes the execution order into `Context → Research → Plan/Build → Learn/Sync/Ratchet` and compounds verified defect/speedup patterns (`24 PAT-*/OPT-*` across `21` families incl. `OPT-MOO-01`, `7 GOV-*`, `13 FALS-01..13`) across the **4-Tier Sharded Playbook Cascade (`L1` Hub + `4 L2` Domain Shards)** via [`/xlearn`](skills/xlearn/SKILL.md) and [`docs/COMPOUND_LEARNING_PLAYBOOK.md`](docs/COMPOUND_LEARNING_PLAYBOOK.md).
* **`-97.06%` Context Noise Reduction + `8.50 MB` Zero-Torch `nano` / `~30 ms` Warm MCP System 1 → 1.5 Triage**: `/xbrief` (`Cap 8` Two-Pass reader + `L1 → Selective L2` Hub-and-Shard Routing) + `/xobsidian` (opt-in `2-Hop` Second Brain router) compresses `1,770,934` raw workspace/vault tokens (`897` files) down to **`52,053` high-authority tokens (`34.0×` compression; `47,436` tok / `97.32%` / `37.3×` Repo-Only)** in **`1.4 ms`** (`1.19 ms` Repo-Only), while `/xlaya` (`v2.4.0` Wallacei `v2.7` K-Fold OOF `NSGA-II` MOO, `6,237 B` LF `sieve_genomes.json`, `laya_triage.py` `7,943` LOC + 6-tool resident `xlaya_mcp_server.py` `1,035` LOC) runs `--profile nano` (`8.50 MB` clean `nano` RSS, `3.74 ms` warm / `274.25 ms/repo` uncontended `v2.4` cold [`3.99 ms` / `255.33 ms` `v2.3`], zero PyTorch/NumPy, `84.05%` disjoint val `31B R@8` / `70.83%` multi-hop / `0.0091` ECE, `65.12%` `E4B R@3` & `79.07%` `31B R@8` Blind `Kaggle 129 R1`, `78.72%` `31B R@8` `SWE-bench_Verified`), chunks & ranks `1,017` fence-safe sections across `28` specs (`154,349` → `997` tok, **`-99.35%`**) in **`147.43 ms`** Stage 0 (`6,898.2` chunks/s) and **`~30 ms` warm MCP inference** (`859.1 q/s` `5.9×`–`6.5×` multilingual & `837.9 q/s` `8.9×` mixed-language batch speedups on `RTX 5060 Ti`, `0.45/0.55` ensemble jury, `--vega-views 1..3` debiasing, `xlaya_fit` persistent `TTTHead` `90.0%` fitted `vega-U` routing accuracy, `100%` 3-Question Joint NLI Triad, and `100.0%` blind accuracy / `0.00%` wrong-and-confident fires on XERJ `#1108`).
* **`100.0%` Red-Team Defect Recall (`25 / 25` in `8.14 ms`)**: `10` bundled Python CLI & MCP engines (`22,237` LOC) enforce 16-pattern secret scanning, Python AST security checks, diff-scoped upstream PR & `CRLF`/`LF` line-ending parity hygiene (`--platform pr`), Qt6/QGIS 4 scoped-enum validation, deep-link URL verification, bidirectional union `L1+L2` SHA-256 mirror parity (`audit_workspace_docs.py` `581` LOC), resident `/xlaya` JSON-RPC 2.0 `stdio` MCP semantic triage (`xlaya_mcp_server.py`), non-intrusive Ghost Mouse UIA/SoM desktop telemetry (`xmouse_cli.py`), and `≤ 400`-char YAML skill budgets (**`370.93 ± 20.15` chars**, `max 392 ≤ 400` across all `15` skills, **`0%` sibling skill truncation**).
* **Which Subscription Quota Tier Should You Pair With XBoost?**
  * **`1×` Base Pro (`Claude Pro`, `Gemini Advanced`, `Cursor Pro`, or Local LLM)**: Best for **Single-Skill Tactical Tasks** (`/xbrief`, `/xdeep-research` Tier 1, localized `/xboost` - `~15.2 steps/turn`).
  * **`5×` High-Throughput (`Claude Max 5×`, `Gemini 5×` - Recommended Minimum)**: Best for **Daily Chained Multi-Skill Sprints** (`/xbrief /xdeep-research /xboost /xlearn /xsync /xobsidian` - `~92.9 steps/turn`, `3.44×` verification depth).
  * **`20×` Ultra (`Gemini Ultra 20×`, `Claude Max 20×`)**: Engineered for **`400+`-Step Autonomous `/goal` Marathons & `/xultra` (`N × K × C × T`) Multi-Agent Swarms** (`~747.3 steps/session`, `~42.82M` cumulative session tokens).

Try it now with a **one-prompt agent install** (copy and paste into any AI coding agent):

```text
Install iscvlab/xboost (https://github.com/iscvlab/xboost): detect my OS and your active global or workspace skills directory, clone the repository, install all 15 /x* skills (Windows: ./scripts/install.ps1 -All; macOS/Linux: ./scripts/install.sh --all; or copy skills/* directly into your active skills folder), run python skills/xpublish/scripts/audit_engine.py skills/xboost --platform skill to verify the CLI harness, and confirm all 15 /x* commands are ready.
```

### Horizontal Bar Comparison (`N = 117` Skills • `897` Docs/Vault Nodes • `25` Red-Team Defects • `1,136` Real IDE Turns)

| Evaluation Dimension | Workflow / Cohort Configuration | Visual Comparison Bar | Measured Result & Delta vs. Baseline |
| :--- | :--- | :--- | :--- |
| **1. Red-Team Defect Catch Rate ↑**<br>*(25 Seeded Defects across 5 Pillars)* | **Level 3: Full 5-Stage + 10 CLI Gates**<br>Level 2: `/xbrief` + `/xdeep-research` + `/xboost`<br>Level 1: `/xboost` Standalone (2 Gates)<br>Level 0: Prompt-Only Baseline (0 Gates) | `████████████████████` **`100.0% (25/25)`**<br>`████████████████░░░░` `80.0% (20/25)`<br>`████████░░░░░░░░░░░░` `40.0% (10/25)`<br>`░░░░░░░░░░░░░░░░░░░░` `0.0% (0/25)` | **`0` False Positives in Median `8.14 ms`** ✨<br>`4` Active CLI Verification Gates<br>`2` Active CLI Verification Gates<br>No Deterministic Pre-LLM Enforcement |
| **2. Context Noise Compression ↑**<br>*(897 Repo + Vault Files, `1.77M` tok)* | **`/xbrief` (`Cap 8`) Repo-Only**<br>**`/xbrief` (`Cap 8`) + `/xobsidian` (`2-Hop`)**<br>Unbounded Repo + Vault Crawl | `████████████████████` **`97.32% Removed (37.3×)`**<br>`████████████████████` **`97.06% Removed (34.0×)`**<br>`░░░░░░░░░░░░░░░░░░░░` `0.0% Removed (1.0×)` | **`47,436` tok in Median `1.19 ms`** ✨<br>**`52,053` tok (`12` files) in `1.4 ms`** ✨<br>`1,770,934` tok (`897` files) in `53.69 ms` |
| **3. System 1 Section Triage ↑**<br>*(28 Specs / 1,017 Chunks, `154.3k` tok)* | **XBoost `/xlaya` Top-5 Shortlist**<br>Unfiltered Full-Corpus Pass-B Read | `████████████████████` **`99.35% Saved (154.8×)`**<br>`░░░░░░░░░░░░░░░░░░░░` `0.0% Saved (1.0×)` | **`997` tok in Median `147.43 ms`** (`6.9k` chunks/s; `~30 ms` warm MCP / `859.1 q/s` GPU) ✨<br>`154,349` tok (Full 28-File Read) |
| **4. Dual-Trigger Budget Guard ↑**<br>*(`Use when` + `Do NOT use` across `N=117`)* | **XBoost `v3.6.0` Suite (`N = 15`)**<br>All Installed Host Skills (`N = 117`)<br>Official Cloud/Vendor Skills (`N = 31`) | `████████████████████` **`100.0% (15/15)`**<br>`██████████████████░░` `90.6%`<br>`█████████████████░░░` `87.1%` | **`370.93 ± 20.15` chars (`0%` Truncation)** ✨<br>`324.41 ± 51.29` chars (`99.1%` `≤500` pass)<br>`331.03 ± 63.51` chars (`96.8%` `≤500` pass) |
| **5. Verification Depth / Turn ↑**<br>*(`N = 1,136` Real IDE Prompt Turns)* | **Chained Multi-Skill `/x*` Turn (`N=289`)**<br>Single `/x*` Skill Turn (`N = 114`)<br>Standard Turn Without `/x*` (`N = 733`) | `████████████████████` **`92.9 Steps (3.44×)`**<br>`███░░░░░░░░░░░░░░░░░` `15.2 Steps`<br>`█████░░░░░░░░░░░░░░░` `27.0 Steps (1.0×)` | **`5.02M` tok/turn (`97.8k` new in, `25.4k` out)** ✨<br>`0.95M` tok/turn (`11.0k` new in, `3.3k` out)<br>`1.56M` tok/turn (`14.8k` new in, `6.4k` out) |
| **6. Compound Learning OSS Speedups ↑**<br>*(`24` Upstream PRs + `1` Hold, `Batch 0 + A + B + C`)* | **`/xlearn` Sharded `L1+L2` Playbooks (`PAT/OPT-*` + `GOV-*` + `FALS-*`)**<br>Unvectorized Upstream Baseline (`HEAD`) | `████████████████████` **`4.0× – 1,735.6× Faster`**<br>`░░░░░░░░░░░░░░░░░░░░` `1.0× Baseline` | **`100%` `assert_allclose` Parity (`10 MERGED`, `9 OPEN PRs`)** ✨<br>Python `np.vectorize`, `O(N²)` scans & OGR disk-seek loops |

---

## 1. Master Ecosystem Architecture

XBoost organizes software engineering, scientific research, spatial/physics simulation, desktop GUI automation, and documentation governance into **five deterministic lifecycle stages** plus **cross-stage System 1 semantic & multi-agent swarm multipliers** across **15 composable `/x*` skills**:

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart LR
    subgraph Canvas [" "]
        S1["Stage 1: Context and Memory - /xbrief + /xobsidian"]
        S2["Stage 2: Research and Proof - /xdeep-research + /xocr"]
        S3["Stage 3: Plan and Execute - /xplan + /xboost + /xultra + /xmouse"]
        S4["Stage 4: Learn, Sync and Release - /xlearn + /xsync + /xcreate-skill + /xpublish"]
        S5["Stage 5: Continuity and Sidecar - /xcontext + /xkickoff + /xlaya"]
        REG["Cloud Skill Registry Sync (coming soon)"]

        S1 --> S2
        S2 --> S3
        S3 --> S4
        S4 --> S5
        S5 -.-> S1
        S4 -.-> REG
    end
    classDef default fill:#ffffff,stroke:#475569,color:#0f172a,stroke-width:1px
    style Canvas fill:#ffffff,stroke:#cbd5e1,stroke-width:1.5px,color:#0f172a
    style REG fill:#ffffff,stroke:#94a3b8,stroke-dasharray: 5 5,color:#64748b
```

---

## 2. Composable `/x*` Slash-Command Grammar & Opt-In Second Brain

Every skill in XBoost is prefixed with `x` so typing `/x` in any IDE autocomplete menu immediately surfaces the entire ecosystem without memorizing individual base names. Every skill works **standalone** or **chained in any order** (automatically normalized into the canonical lifecycle DAG):

```text
[Stage 1: Context]  →  [Stage 2: Research]  →  [Stage 3: Plan / Execute]  →  [Stage 4: Learn & Sync]  +  [Modifiers / Sidecars]
     /xbrief        →    /xdeep-research    →     /xplan  or  /xboost     →     /xlearn + /xsync     +  /xobsidian /xlaya /xultra /xmouse /goal
```

### Strict Opt-In Second Brain Isolation (`/xobsidian`)

By default, all skills operate in **100% Repo-Only Mode** and ignore any directory containing an `.obsidian/` subfolder. The 2-Hop Obsidian Second Brain and Knowledge Ratchet activate **only** when `/xobsidian` is explicitly included in the command chain:

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart LR
    subgraph Canvas [" "]
        Prompt["User Prompt + /x Slash Combination"] --> Gate{"Is /xobsidian in the command?"}
        Gate -->|"NO (Default)"| NoVault["Standard Repo-Only Execution (Zero vault reads or writes)"]
        Gate -->|"YES (Opt-In)"| Resolve["Step 0: Dynamic Vault Resolver (obsidian.json + 00 Index.md)"]
        Resolve -->|"/xbrief /xobsidian"| BriefCombo["/xbrief (Cap 8) + Vault 2-Hop Domain Lookup"]
        Resolve -->|"/xdeep-research /xobsidian"| ResCombo["/xdeep-research + Vault Hop 0 to 2 Cache and Auto-Ratchet"]
        Resolve -->|"/xdeep-research /xboost /xobsidian"| BoostCombo["Full Stack Research to 2D Contract to Build to Vault Ratchet"]
        Resolve -->|"/xlearn /xobsidian or /xsync /xobsidian"| SyncCombo["3-Tier Playbook + Repo + Second Brain Sync (Repo Docs and Vault Hubs)"]
    end
    classDef default fill:#ffffff,stroke:#475569,color:#0f172a,stroke-width:1px
    style Canvas fill:#ffffff,stroke:#cbd5e1,stroke-width:1.5px,color:#0f172a
```

### High-Leverage Command Combinations

| Command Chain | Execution Pipeline | Best Used When |
|:---|:---|:---|
| `/xbrief <task>` | Load up to 8 authoritative repo docs (`Pass A` skeleton → `Pass B` deep read) + Up-Tree `COMPOUND_LEARNING_PLAYBOOK.md` (`L1` Hub → selective `L2` `docs/playbooks/*` shard) → execute `<task>` | Starting a feature or fix inside an unfamiliar or multi-doc repository |
| `/xbrief /xobsidian <task>` | Load repo SSOTs (cap 8) + 2-Hop lookup in active Obsidian vault → execute `<task>` | Pulling cross-project architectural rules or domain constants into the current task |
| `/xdeep-research /xboost <task>` | Adaptive 3-Tier primary-source probe (`Tier 1` inline SDK/DB/AST probe or `Tier 3` 5-wave harvest) → lock 2D Goal Contract → Red-Green-Verify build | Implementing a technical feature or solver that depends on exact API/physics specs |
| `/xdeep-research /xboost /xobsidian` | Vault 2-Hop cache check → probe missing delta → `/xboost` 4-phase build → Auto-Ratchet new specs into Vault | Compounding reusable engineering or scientific knowledge while shipping production code |
| `/xdeep-research /xboost /goal` | 5-wave multi-agent harvest + `verify_evidence.py` audit → full-stack implementation until 100% milestone completion | Long-running, multi-milestone research-to-production engineering sprints |
| `/xboost /xultra <task>` | **Elastic Cognitive Swarm (`N × K × C × T`)** (`Orthogonal K-Vector Tournament`, `Elastic Cognitive-Density Fleet` with Pre-Locked Shared Seam Header, or `Evolutionary Ratchet Loop` across `T` generations) + **Two-Stage Elastic Verification (`Wave 2A` Parallel Critic Shards `C ≥ 1` → `Wave 2B` Serialized Main Checker Gate)** | High-stakes algorithms, solver convergence, multi-module sprints, or parallel UI/diagram candidate tournaments on `5×`/`20×` tiers |
| `/xboost /xmouse <task>` | Non-intrusive background Ghost Mouse (`PostMessageW`) + UIA tree inspection + Set-of-Mark vision capture + Multi-Agent Visual Cursor HUD | Automating or verifying desktop CAD/GIS/IDE windows in the background without hijacking the physical mouse cursor |
| `/xplan <task>` | 2D Plan Contract → Ponytail × Deep Module Vector A/B/C → `implementation_plan.md` with Inline Grilling Matrix & Red → Green table → halt for approval | Stress-testing architectural decisions and edge cases before writing a single line of code |
| `/xlearn` (`/xlearn /xobsidian`, `/xlearn /xultra`) | Distill verified session bug/optimization/governance patterns into the **Sharded `L1+L2` & Tier 2 Compound Learning Playbooks** (`Tier A` auto-ratchet + cross-shard `/xlaya` dedup + `/xsync --federated` closure) or run the **5-Gate Universal Law Falsification Sieve** + Wave 2A Blind Critic (`Tier B` human-consent gate) | Compounding post-session debugging, PR reviews, or benchmark findings without manually remembering to invoke `/xsync` or `/xcreate-skill` |
| `/xsync /xlaya` | Fast System 1 `noul` semantic contradiction triage + `audit_workspace_docs.py` + 5-tier inner-to-outer doc sync | Catching semantic contradictions across markdown/HTML docs alongside deterministic regex/link audits |
| `/xsync /xobsidian` | 5-tier inner-to-outer repo doc sync + Tier A Playbook Ratchet + update matching atomic notes and Hub tables in the Obsidian vault | Keeping repository documentation, compound learning playbooks, and knowledge graphs 100% synchronized |
| `/xpublish` (`/xpublish-audit`, `/xpublish-qgis`) | Run 6-pillar security/AST/Flake8/skill/PR diff audit (`audit_engine.py --platform pr\|github\|qgis\|food4rhino\|skill\|generic`), `CRLF`/`LF` line-ending parity check (`PAT-GIT-01`), Review-Bot convergence (`§6.D`), and Qt6-verified single-root QGIS zip packaging (`package_qgis.py` + `check_qt6.py`) | Shipping upstream PRs and releasing open-source packages to GitHub, `plugins.qgis.org`, or Food4Rhino |
| `/xcontext` → `/xkickoff` | Diagnose transcript compaction health (`check_context.py`) → run pre-handover `/xsync` → generate task-smart fresh session prompt | Transitioning cleanly to a fresh chat window before context degradation or timeouts occur |

---

## 3. The 15-Skill Suite

```text
xboost/skills/
├── /xboost           2D Task × Project goal synthesis, Universal Laws (UL-01..08) & 4-phase red-green solver
├── /xbrief           4-tier authority hierarchy, two-pass reading & selective L1→L2 playbook shard routing
├── /xcontext         transcript compaction diagnostics, cross-platform token telemetry & drift scorecard
├── /xcreate-skill    author, distill & globalize portable SKILL.md files (Modes A & B)
├── /xdeep-research   unified 3-tier primary-source research, live HEAD/collision gate & 5-wave audit
├── /xkickoff         end-of-session sync check, task-smart command selector & handover prompt
├── /xlaya            5-profile System 1 → System 1.5 semantic & code-graph triage, resident MCP & vega-U sidecar
├── /xlearn           post-session compound learning, elastic L1+L2 Playbook ratchet & 5-Gate Universal Law engine
├── /xmouse           non-intrusive Ghost Mouse, Hybrid UIA + Set-of-Mark controller & Visual Multi-Cursor HUD
├── /xobsidian        opt-in 2-hop Obsidian Second Brain router, cross-domain bridges & converged-only ratchet
├── /xocr             single-pass C++ PyMuPDF vector/booktabs table extractor, Thai/EN normalizer & 5-profile OCR ladder
├── /xplan            XBoost architecture planner with Vector A/B/C & inline grilling matrix
├── /xpublish         unified 6-pillar security/AST/PR/CRLF/skill audit gate, GitHub v1.5 & QGIS 4/Qt6 zip packager
├── /xsync            5-tier cross-document sync, L1+L2 playbook/shard federated auditor & SHA-256 mirror gate
└── /xultra           Elastic Cognitive Swarm (N × K × C × T), K-vector tournament, evolutionary ratchet & Wave 2A/2B blind verifier
```

### Stage 1: Context, Triage & Memory

| Skill & Command (Aliases) | Core Architecture & Protocol | Failure Modes Prevented |
|:---|:---|:---|
| **1. XBrief**<br>[`/xbrief`](skills/xbrief/SKILL.md) (`/brief`) | Discovers related markdown in the active repository via a **4-tier authority hierarchy** (hard-capped at 8 files) plus **Bounded Up-Tree `L1 → Selective L2` Playbook Shard Routing** (`v3.6.0`, walking up to `2` ancestor levels under a safe stop-list to read the [`docs/COMPOUND_LEARNING_PLAYBOOK.md`](docs/COMPOUND_LEARNING_PLAYBOOK.md) `L1` Router Hub in Pass A and load **only** task-matched `L2` shards `docs/playbooks/PLAYBOOK_1A..1D_*.md` in Pass B via `L1` dispatch or `/xlaya`), applies **Two-Pass reading**, verifies frozen/deferred boundaries, and executes `/xbrief <task>` in the same turn. | Answering from stale LLM memory, repeating solved cross-workspace bugs, crowding the 8-file window cap with unrelated shards, or modifying frozen modules. |
| **2. XObsidian**<br>[`/xobsidian`](skills/xobsidian/SKILL.md) (`/obsidian-vault`) | **Dynamic Vault Resolver** reads OS `obsidian.json` (`open: true`) or parent directories with zero hardcoded paths. Enforces the **2-Hop Navigation Rule** (`00 Index.md` → `Hub - <Domain>.md` → Atomic Note), **Converged-Only Ratchet & Session Dirty-Note Ledger (`DIRTY_IN_SESSION`)**, **Cross-Domain Bridges**, and **4-Check Graph Verification** (`0` broken wikilinks, `0` orphans, `100%` frontmatter, `0` duplicate neighbor groups). | Dumping 50+ markdown notes into context, hardcoded vault paths breaking across PCs, or ratcheting unverified mid-session experimental parameters into long-term memory. |
| **3. XLaya**<br>[`/xlaya`](skills/xlaya/SKILL.md) (`/laya`) | **5-Profile System 1 → System 1.5 Semantic Decision, 4-PC Whitened Code-Graph Simplex, `M_avail` Regime Shield, Conformal `ToolGate` & Wallacei `v2.7` OOF MOO (`v2.4.0`)** ([`scripts/laya_triage.py`](skills/xlaya/scripts/laya_triage.py) `7,943` LOC + zero-extra-dependency 6-tool AST-reloading JSON-RPC 2.0 `stdio` MCP server [`scripts/xlaya_mcp_server.py`](skills/xlaya/scripts/xlaya_mcp_server.py) `1,035` LOC, standalone repo [`iscvlab/xlaya`](https://github.com/iscvlab/xlaya) `v2.4.0`, latest remote tag `v2.3.0 LIVE`) powered by `--profile nano` (`8.50–10.41 MB` ΔRSS zero-PyTorch/NumPy AST + `resources/sieve_genomes.json` `6,237 B` LF + Top-4 PC `.npz` whitening + `237,386` matched call edges + `M_avail` `gamma_max=1.45` + Slot-1 Platt `T=1.20/1.67`, **`65.12%` `E4B R@3` / `79.07%` `31B R@8` / `0.0568 & 0.0535` `ECE`** blind `Kaggle 129`, **`78.72%` `31B R@8` / `0.0293` `ECE`** blind `SWE-bench_Verified`, **`81.37%` Val / `71.69%` MCQ** `nvidia/When2Call` `ToolGate`, `86.21%` `PLE 29`, `22/22` pytest), [`convaiinnovations/laya`](https://github.com/convaiinnovations/laya) `0.4.31+` & `vegaml 0.16.1+` (`~30 ms` warm MCP inference). Cascades **Stage 0** (`0.15 ms/chunk` fence-safe breadcrumb & Python `ast` + `--pattern web` brace chunker, `-99.35%` Pass-B compression) → **Stage 1** (`ModernBERT`/`mmBERT`/`laya-typed-decisions` with Head-Language Guard, `0.45/0.55` ensemble jury & `disagreement >= 0.15` gate, `859.1 q/s` GPU batch, **3-Question Joint NLI Triad `P_eff`**, `--thorough` 4-facet rubric + `file_summaries`, `predict_tournament` for `>20` labels) → **Stage 2** (`vega-U` conformal `73,728`-tok verifier with `--vega-views 1..3`, `xlaya_fit` persistent `TTTHead` + split-conformal policy, `outbound` OOD guard, and local multimodal `image`/`audio`/`video`, returning **`90.0%` (`18/20`)** `5-fold` fitted routing accuracy & **`100.0%` (`48/48`)** blind fitted accuracy / **`0.00%` wrong-confident** on [`xerj-org/xerj#1108`](https://github.com/xerj-org/xerj/issues/1108)). | Silent 512-token truncation, `docs_src/` alphabetical starvation, `.npz` narrow-cone anisotropy (`0.8518`), `tests/test_*.py` lexical echo distractors, scalarized MOO `val` leakage, cold-start CLI/MCP reloads (`~30 ms` warm MCP), accuracy collapse on `>20` choice labels, or uncalibrated ECE jumps. |

### Stage 2: Research & Proof

| Skill & Command (Aliases) | Core Architecture & Protocol | Failure Modes Prevented |
|:---|:---|:---|
| **4. XDeep-Research**<br>[`/xdeep-research`](skills/xdeep-research/SKILL.md) (`/deep-research`, `/xresearch`) | Unified **3-Tier Primary-Source Research & 5-Wave Adversarial Proof Engine**. Routes dynamically across **Tier 1 (Fast Inline Probe `≤ 2` sources)**, **Tier 2 (Single Isolated Scout)**, and **Tier 3 (5-Wave Multi-Agent Deep Research Swarm)**: (1) 2D `Intent × Domain` contract synthesis, **4-Tier Primary-Source Authority Ladder** (local pinned manifests/SQLite/AST probes first + automatic `/xocr` PDF/table ingestion), and **Up-Tree 4-Tier Sharded Playbook & Live `HEAD` / Open-PR Collision Pre-Gate** (`v3.6.0`: checking `PAT-*/OPT-*`, `GOV-01..07`, and `FALS-01..13` silent `HEAD` fixes, enclosing-method `def` headers, and unlinked open PRs), (2) parallel Harvester scouts with mandatory deep-link scraping, (2.5) **Wave 2.5 Rejected-Candidate Graveyard & Zero-Retrain Counterfactual Ablation Forensics**, (3) **Blind Adversarial Auditor** + deterministic [`scripts/verify_evidence.py`](skills/xdeep-research/scripts/verify_evidence.py) (`286` LOC) CLI gate with **Wave 3.5 Prune & Replace Loop**, (4) `[VERIFIED FACT]` vs `[RECOMMENDED SYNTHESIS]` binding with **Single-SSOT In-Place Upsert & Iterative Delta Routing** (`Turn t > 1`), and (5) `/xboost` handoff. | Secondary-blog guesswork, researching the wrong SDK version, claiming open GitHub issues already silently fixed on `HEAD` (`FALS-01`) or contested by unlinked PRs (`FALS-03`), misattributing enclosing function scopes (`FALS-02`), proposing expensive retraining when existing post-processing dampers throttle valid candidates, and duplicate `RESEARCH_*.md` file forking. |
| **5. XOCR**<br>[`/xocr`](skills/xocr/SKILL.md) (`/ocr`, `/unlimited-ocr`) | **High-Speed Hybrid PDF & CAD/Table Extraction Engine** (`v2.4.0`: [`scripts/ocr_runner.py`](skills/xocr/scripts/ocr_runner.py) `7,455` LOC + [`resources/xocr_genomes.json`](skills/xocr/resources/xocr_genomes.json), standalone repo [`iscvlab/xocr`](https://github.com/iscvlab/xocr), **[Upstream PR #16 to `scb-10x/typhoon-ocr` (`OPEN`)](https://github.com/scb-10x/typhoon-ocr/pull/16)**). Combines **Single-Pass C++ `PyMuPDF` (`fitz`)** coordinate-sorted & faux-bold de-ghosted text (`_extract_clean_text_atoms`, rotated `line["dir"]` callout grouping), **Grid-Bubble Axis Parser & Spatial Join (`extract_grid_axes`, `resolve_grid_ref`)**, **Cross-Sheet Callout Graph & Revision Diff (`extract_sheet_callouts`, `build_callout_graph`, `diff_pdf_drawings`, `--diff-with`)**, **6-Gate Multi-Page Table Continuation Stitching (`stitch_multipage_tables`, `FALS-R2-07` CSV reconciliation)**, **Stage 0 Zero-Hang Composite-Cached Unexplained-Canvas Tile-and-Stitch** (`207.14 ms` probe on `288.57 MB` BMA Master Plan), **Exploded `.SHX` Stroke-CAD Detector** (`short_stroke_ratio >= 0.45`, `< 35` chars), **Frozen 4-Regime 8D Simplex + Platt + Split-Conformal Router** (`100.0%` test acc, `0.0324` ECE, `conformal_q_hat = 0.2046`, `0` manifest leaks), **< 10 ms BM25F ROI Sniper** (`rank_spatial_rois`), **Thai PUA (`U+F700..U+F71A`) / Sara-Am Normalization & Thai Script Guard**, and a **5-Profile (`auto|nano|edge|workstation|max`) Backend Ladder** (`0-torch` CPU `RapidOCR` + local HuggingFace [`typhoon-ai/typhoon-ocr1.5-2b`](https://huggingface.co/typhoon-ai/typhoon-ocr1.5-2b) / [`3b-qat`](https://huggingface.co/typhoon-ai/typhoon-ocr1.5-3b-qat) (`-35.9%` vision token bloat) & [`baidu/Unlimited-OCR-2`](https://github.com/baidu/Unlimited-OCR)). | Zero-table failures without `pdfplumber`, lexicographic grid sort traps, split multi-page table fragments, false revision diffs on jittered CAD sheets, CJK garbage from unguarded `RapidOCR` on Thai sheets, and blind full-sheet VLM waste (`15.0×-3,326×` vector speedup). |

### Stage 3: Planning, Deep Execution & Desktop Automation

| Skill & Command (Aliases) | Core Architecture & Protocol | Failure Modes Prevented |
|:---|:---|:---|
| **6. XPlan**<br>[`/xplan`](skills/xplan/SKILL.md) (`/plan`) | **XBoost Architectural Planner**. Locks a **2D Plan Contract (`Scope × Risk`)**, runs blast-radius & invariant discovery (with **Elastic Red-Team Seam & SSOT Critics `C ≥ 1`** under `/xplan /xultra`), evaluates **Ponytail × Deep Module Vectors A/B/C** (`Vector A (Recommended): Zero-New-File / Stdlib Seam`), embeds an **Inline Grilling Decision Matrix** (`DEC-01..N`) and **Red → Green Verification Matrix** (`UL-05` `A_pos ∧ A_neg` + `UL-08` `Live-Entrypoint Parity`) inside `implementation_plan.md` with zero chat Q&A spam, and halts for user approval. | Jumping straight into code on underspecified requirements, noisy chat Q&A walls, or over-engineered multi-file abstractions. |
| **7. XBoost**<br>[`/xboost`](skills/xboost/SKILL.md) | Flagship **4-Phase Engineering & First-Principles Solver**: (1) **2D `Task × Project` Goal Contract**, **Tri-Track Signal Gate** (with **Bidirectional Counter-Anchors `A_pos ∧ A_neg`, Strict Feasibility Dominance & Goal-Matched Objective/Constraint Polarity, `UL-05`**, plus **Live-Entrypoint Parity & Active-Regime Sensitivity, `UL-08`**), and **Context-Conditioned Single-Layer Universal First-Principles Laws (`UL-01..UL-08`)** ([`references/deep_audit_protocol.md`](skills/xboost/references/deep_audit_protocol.md)), (2) **Ponytail × Deep Module Ladder** (`YAGNI → Reuse → Stdlib → Deep Seam → Shortest Diff`), (3) **Universal Parity** (Dual-OS + OneDrive + IDE/CLI), (4) **3-Tier Verification & Cumulative Monotonic Ratchet (`Pass_Set(t+1) ⊇ Pass_Set(t)`)**. | Speculative blind fixes, cross-cut data leakage (`UL-01`), blocking-`continue` peer-branch drops (`UL-04`), accidental `α²` double-application (`UL-06`), `T(T(x))` cache compounding (`UL-07`), and machine-bound paths. |
| **8. XUltra**<br>[`/xultra`](skills/xultra/SKILL.md) (`/ultra`) | **Elastic Cognitive Swarm (`N × K × C × T`) & Two-Stage Evolutionary Ratchet (`Stage A → Stage B`)**. Normalizes any multi-skill combo into the **Canonical Stage DAG** (`Context → Research → Plan/Build → Learn/Sync/Ratchet`), derives topology via the **4-Law Swarm Sizing Calculus (`N × K × C × T`)** (`Law 1: Code-Over-Swarm Split`, `Law 2: True Orthogonality K-Vectors`, `Law 3: Cognitive-Density N-Sharding` with **Pre-Locked Shared Seam Header**, `Law 4: Two-Stage Elastic Verification — Wave 2A Parallel Critic Shards C ≥ 1 → Wave 2B Serialized Main Checker Gate`), executes the **Two-Stage Evolutionary Ratchet** (**Stage A** zero-retrain post-processing throttle audit `UL-04..UL-07` locking `Floor_StageA ≥ Floor_0` before **Stage B** warm-start generations `1..T` with `Pass_Set(t+1) ⊇ Pass_Set(StageA)`), and enforces the **3-Bucket Numeric Litmus Test** + **Pointer-Not-Payload Return Contract**. | Arbitrary fixed-count subagent quotas, cold-start retraining when post-processing throttles suppress existing models, multi-agent file-write race conditions, cross-shard interface drift, and self-grading inline shortcuts. |
| **9. XMouse**<br>[`/xmouse`](skills/xmouse/SKILL.md) | **Non-Intrusive Multi-Agent Ghost Mouse, Hybrid UIA + Set-of-Mark Controller & Visual Multi-Cursor HUD** ([`scripts/xmouse_cli.py`](skills/xmouse/scripts/xmouse_cli.py) `1,891` LOC). Enforces a **3-Tier Escalation Ladder**: **Tier 1 (`Ghost Mode` Default)** dispatches background Win32 `PostMessageW` (`WM_LBUTTONDOWN/UP`, `WM_CHAR`, `WM_MOUSEWHEEL`) directly to target `HWND` client coordinates (`0 px` physical cursor movement, `0` focus theft); **Tier 2 (`Instant Save/Restore SendInput`)** saves physical cursor state via `GetCursorPos()`, injects hardware input in `< 5 ms`, and restores the user's cursor; **Tier 3 (`60 FPS Click-Through Multi-Agent HUD`)** renders color-coded virtual agent cursors, smooth Bézier trails, click ripples, and target bounding boxes on a transparent overlay (`WS_EX_LAYERED \| WS_EX_TRANSPARENT`). Includes native C++/COM UIA tree inspection (`xmouse_inspect_uia`) and Set-of-Mark (`[1]..[N]`) vision grid capture (`xmouse_som_capture`). | Hijacking the user's physical mouse cursor during long agent runs, stealing active window focus while the user is typing, or guessing blind pixel coordinates when exact UIA bounding rectangles exist. |

### Stage 4: Compound Learning, Synchronization & Release Gates

| Skill & Command (Aliases) | Core Architecture & Protocol | Failure Modes Prevented |
|:---|:---|:---|
| **10. XLearn**<br>[`/xlearn`](skills/xlearn/SKILL.md) (`/learn`) | **Compound Learning Ratchet, Elastic `L1+L2` Playbook Updater & 5-Gate Universal Law Evolution Engine** (`v3.6.0`). Separates post-session compound learning from greenfield skill authoring (`/xcreate-skill`). Routes verified session findings across a **Two-Tier Autonomy Boundary**: **Tier A (`Autonomous Sharded Playbook Ratchet`)** runs cross-shard `/xlaya` dedup (`PAT-*/OPT-*`, `GOV-*`, `FALS-*`), updates the owning `L2` domain shard ([`docs/playbooks/PLAYBOOK_1A..1D_*.md`](docs/playbooks/PLAYBOOK_1A_ALGORITHMS_VECTOR_GPU_CONCURRENCY.md), `< 35 KB` LF each) + compact `L1` Router Hub ([`docs/COMPOUND_LEARNING_PLAYBOOK.md`](docs/COMPOUND_LEARNING_PLAYBOOK.md)) or Tier 2 Domain Playbooks while enforcing Gate 5 Pointer-Over-Paste, and **automatically triggers `/xsync --federated`** so `L1+L2` SHA-256 mirrors stay 100% synchronized; **Tier B (`5-Gate Universal Law Falsification & Human-Consent Skill Evolution`)** enforces the `3-Domain Translation Proof Table` (`Archetypes A × B × C`), `9-Point Mathematical Boundary Table`, and **Wave 2A Blind Counter-Domain Critic** before presenting a `Before → After` proposal for explicit human approval. | Forgetting to run `/xsync` or `/xcreate-skill` after solving hard bugs or PR reviews, bloating playbooks past the `46,080`-byte `read_file` truncation limit, duplicating rows across `L1`/`L2`, or leaking single-project domain math into global `SKILL.md` laws. |
| **11. XSync**<br>[`/xsync`](skills/xsync/SKILL.md) (`/update-doc`, `/doc-sync`, `/audit-docs`) | Exhaustive multi-file and cross-repository synchronizer with bundled [`scripts/audit_workspace_docs.py`](skills/xsync/scripts/audit_workspace_docs.py) (`581` LOC). Applies a **4-Level Conflict Arbitration Hierarchy** (`Level 1: Verified Non-Fallback Code & Runtime Receipts [source != "fallback", N_proc == N_exp, UL-04 Partition Conservation] > Level 2: Canonical SSOT > Level 3: Session User Lock > Level 4: Drafts`), **3-Signal Bounded Up-Tree & Cross-Repo Mirror Federation (`--federated`)** (auto-discovering `L1` Playbook + `L2` `playbooks/*.md` ↔ `docs/playbooks/*.md` bidirectional union mirrors, Tier 2 Domain Playbooks, sibling git repositories, symlink-safe global skill roots incl. `~/.gemini/config/skills`, `GITHUB_PUBLISHING_PROTOCOL.md`, and org/profile READMEs), verifies relative links, Zero-LaTeX compliance, SHA-256 mirror parity, and `--deprecated` sweeps across **Tiers 1-5**, and outputs a verified **Synchronization Ledger**. | Touching 1-2 surface files while leaving stale numbers in sibling repos, missing `L2` shard or `~/.gemini/config/skills` drift, false-positive ghost-skill errors on symlinks/domain repos, or breaking HTML slide/card counters. |
| **12. XCreate-Skill**<br>[`/xcreate-skill`](skills/xcreate-skill/SKILL.md) (`/create-skill`) | **4-Step Cognitive Distillation Protocol (`Modes A & B` — Greenfield Skill Creation, Distillation & Auditing)**: (1) Universal Globalization into `~/.gemini/config/skills/<name>/` and all active agent roots, (2) **Context Budget Guard** (`≤ 400 chars` YAML description with explicit `Use when...` and `Do NOT use for...` triggers so host IDEs never drop sibling skills), (3) **5-Gate Universal Law Falsification Protocol** (`Agent-Process Law vs. Domain-Equation Inversion`, `Global CLI Script Ban` blocking project domain math in `skills/*/scripts/*.py`, `Pruned Project-Specific Ideas` ledger, `3-Domain Translation Proof Table`, and `Gate 5` Pointer-Over-Paste Single-SSOT Reference Rule delegating post-session `Mode C` ratcheting to [`/xlearn`](skills/xlearn/SKILL.md)), and (4) mandatory `--platform skill` audit. | Workspace-siloed skills, bloated frontmatter descriptions (`> 400` chars), duplicating 9-point mathematical tables across multiple skills, and unverified helper scripts. |
| **13. XPublish**<br>[`/xpublish`](skills/xpublish/SKILL.md) (`/xpublish-audit`, `/xpublish-qgis`, `/publish`) | **Unified 6-Pillar Pre-Flight Release Gate, Upstream PR Convergence & QGIS 4 / Qt6 Packager** ([`skills/xpublish/scripts/audit_engine.py`](skills/xpublish/scripts/audit_engine.py) `1,368` LOC, [`check_qt6.py`](skills/xpublish/scripts/check_qt6.py) `422` LOC, and [`package_qgis.py`](skills/xpublish/scripts/package_qgis.py) `587` LOC). Supports `--platform pr\|github\|qgis\|food4rhino\|skill\|generic` (including diff-scoped `audit_pr_diff_invariants` and multi-skill suite root recursion), **Mixed `CRLF` / `LF` Upstream File Line-Ending Parity Guard (`PAT-GIT-01`)**, **Upstream Governance Fingerprint Verification (`GOV-01..07`)**, **Tier B Human-Consent Dispatch Gate**, 16 high-entropy secret patterns (`pat.finditer()` multi-token scan), hardcoded user paths (`C:\Users\...`, `/Users/...` with negative lookbehind), Python AST security risks (`eval`, `shell=True`, `pickle`), Flake8 compliance, **Gate 3 Over-Specific Law Detector (`Check 4B`)**, **`≤ 500`-Line Sprawl Gate (`Check 4C`)**, **Raw LaTeX Macro Scanner (`Check 4D`)**, **Tri-OS Clipboard Protocol (`CF_UNICODETEXT` / `pbcopy` / `wl-copy`)**, **GitHub Repository Publishing Protocol `v1.5` ([`references/github_readme_protocol.md`](skills/xpublish/references/github_readme_protocol.md))**, and **5-Gate Deterministic QGIS Release Packaging ([`references/qgis_release_protocol.md`](skills/xpublish/references/qgis_release_protocol.md))**. | Leaked API keys, placeholder-masked secret leaks on multi-token lines, accidental whole-file `CRLF ↔ LF` diff pollution (`3,956`-line PR diffs), missing DCO/companion changelog files, `> 30 KB` SVG truncation, `> 500`-line `SKILL.md` sprawl, and Qt5 unscoped enum crashes (`QDialog`, `QDialogButtonBox`, `QAbstractItemView`) in QGIS 4. |

### Stage 5: Session Continuity

| Skill & Command (Aliases) | Core Architecture & Protocol | Failure Modes Prevented |
|:---|:---|:---|
| **14. XContext**<br>[`/xcontext`](skills/xcontext/SKILL.md) (`/context`) | Runs [`scripts/check_context.py`](skills/xcontext/scripts/check_context.py) (`669` LOC) against the active IDE conversation transcript (`transcript.jsonl`) and SQLite step logs (`conversations/*.db`), unwrapping `.system_generated/logs` paths to parent `<uuid>`, filtering out isolated subagent logs, reporting **Session & Cross-Platform Token Telemetry** (`--tokens`, `--days N`, `--all-time` across Antigravity 2.0, IDE, and CLI), and evaluating a **2D Health Rubric (`Compaction Round × Active Window Pressure %`)** across strict `CHECKPOINT` boundaries (`🟢 HEALTHY`, `🟡 NOMINAL`, `🟠 CAUTION`, `🔴 CRITICAL`). | Continuing complex edits after multi-pass compactions, subagent transcript hijacking, bytecode `.pyc` pollution, or invisible cross-platform token usage. |
| **15. XKickoff**<br>[`/xkickoff`](skills/xkickoff/SKILL.md) (`/kickoff`) | End-of-session handover protocol. Runs a pre-handover `/xsync` (or `/xlearn` when new session bugs/optimizations were solved) verification check, presents a structured **Next-Step Options Table** (`Option A Recommended`, `Option B`, `Option C`), applies the **Task-Smart Recommended Command Selector** (auto-routing `/xlaya`, `/xlearn`, `/xmouse`, and `/xultra` only when task signals match), and generates a **self-contained copy-pasteable Kickoff Prompt**. | Starting a fresh conversation with vague context, losing mid-session decisions, or leaving unsynchronized documentation behind. |

---

## 4. Deep-Dive Engineering Pillars

### 4.1 2D Goal Contract & Context-Conditioned Single-Layer Universal First-Principles Laws (`UL-01..UL-08` in `/xboost`)

Before touching code on non-trivial tasks, `/xboost` locks a **2D Goal Contract** crossing **6 Task Archetypes** (`DEBUG/RCA`, `BUILD/FEATURE`, `SIMULATE/SOLVER`, `REFACTOR/SIMPLIFY`, `OPTIMIZE/SCALE`, `AUDIT/PLAN/SHIP`) with **5 Universal System Verification Dimensions** (`Continuous Numerical & Physical Solvers`, `Discrete Graph, Partition & Relational Pipelines`, `UI, Visual & Interactive State Machines`, `Distributed, Concurrent & Stateful Services`, `Declarative Schemas, Compilers & CLI Harnesses`) governed by the **8 Context-Conditioned Single-Layer Universal First-Principles Laws (`UL-01..UL-08`)** in [`skills/xboost/references/deep_audit_protocol.md`](skills/xboost/references/deep_audit_protocol.md):
1. **`UL-01` (Bracketed Support, Scale Conditioning & Graph-Cut Isolation)**: Enforces bracketed domain support (`x_left ≤ x ≤ x_right`), explicit scale conditioning, and `0.0` future/cross-cut information leakage.
2. **`UL-02` (Exact-Condition Refinement & Absorbing Failure Precedence)**: Enforces exact predicate refinement (`S_exact = {x ∈ S_cand : P(x)}`) and pessimistic absorbing failure precedence (`Failure > Success` tie-breaking).
3. **`UL-03` (Step-Measure Scaling Convergence & Zero-Forcing Equilibrium Identity)**: Enforces step-measure convergence (`O(Δμ^p)`) and exact zero-forcing equilibrium identity (`Δx = 0 ⇒ Δy = 0.0 / y == y_eq` with `0` `NaN`/`Inf`).
4. **`UL-04` (Extensive Partition, Remainder Conservation & Intended Peer-Branch Routing Completeness)**: Enforces extensive partition conservation (`∑ Child_k + Remainder ≈ Parent`) and peer-branch routing completeness (`K_peer ⊆ K_eval`, `0` blocking-`continue` drops).
5. **`UL-05` (Bidirectional Counter-Anchors, Strict Feasibility Dominance & Goal-Matched Objective/Constraint Polarity)**: Enforces simultaneous counter-anchors (`A_pos ∧ A_neg`), strict feasibility dominance (`J(x_infeas) ≺ J(x_feas)`), non-zero marginal sensitivity (`|∂J/∂M| > 0` on unbounded objectives), goal-matched dispersion (`symmetric MSE/σ` for setpoint tracking vs `one-sided σ_fail` for directional goals), and role-matched `binary / continuous / budgeted` constraints.
6. **`UL-06` (Piece-Wise Codomain Reachability, Marginal Seam Scaling Order & Non-Degeneracy)**: Verifies live reachability of every declared codomain branch (`count(Branch_k) > 0`), interior marginal seam scaling (`|ΔY(α_2)/ΔY(α_1)| ≈ (α_2/α_1)^p_theory` without accidental `α²` double-application), and non-degeneracy.
7. **`UL-07` (Read-Only Feature-Stream Decoupling, Cache Idempotency & Post-Gate Non-Regression)**: Prevents `T(T(x))` cache compounding on shared feature streams and guarantees post-gate non-regression.
8. **`UL-08` (Live-Entrypoint Parity, Active-Regime Sensitivity & Bounded Complexity)**: Requires invoking the live production entrypoint directly (`∃ x ∈ Active_Regime(X) : ΔY ≠ 0`, `N_proc == N_exp`, `source != "fallback"`) under bounded complexity.

### 4.2 Unified 3-Tier Research & 5-Wave Adversarial Fact Auditing (`/xdeep-research`)

Standard LLM web research either spawns heavy subagents for 10-second SDK lookups or hallucinates metrics from search snippets on deep studies. `/xdeep-research` unifies **3-Tier Adaptive Scope Routing** (`Tier 1: Fast Inline Probe`, `Tier 2: Single Isolated Scout`, `Tier 3: 5-Wave Deep Research Swarm`) with **4-Tier Primary-Source Authority** and **Blind Adversarial Verification**:
- **Tier 1-2 (Tactical Primary-Source Probe)**: Checks local pinned manifests (`package.json`, `pyproject.toml`, `*.csproj`, `metadata.txt`) and local SQLite/AST/CLI probes before querying external documentation.
- **Wave 1 (2D Contract & Live `HEAD` / Collision Pre-Gate)**: Locks domain axes, minimum record quotas, disambiguation rules, and upstream governance/collision checks (`GOV-01..07`, `FALS-01..13`).
- **Wave 2 & 2.5 (Harvester Swarm & Rejected-Candidate Graveyard Forensics)**: Parallel scouts scrape full page bodies and deep links under strict capability-aware write-permission rules, while **Wave 2.5** inspects pruning logs, rejected candidate archives, and post-processing dampers via zero-retrain counterfactual ablation before proposing new external architectures or expensive retraining.
- **Wave 3 & 3.5 (Blind Adversarial Audit + Prune & Replace)**: An independent auditor runs `scripts/verify_evidence.py` to reject `[TBD]` placeholders, root-domain URLs, and schema violations, triggering replacement harvesting until the quota is 100% verified.
- **Wave 4 (100%-Proof Synthesis)**: Every claim is explicitly tagged as `[VERIFIED FACT]` (backed by a primary receipt) or `[RECOMMENDED SYNTHESIS]` (engineering inference).

### 4.3 Public Claim Vocabulary (`/xsync` & `/xpublish`)

Both `/xsync` and `/xpublish` enforce five canonical status terms across all public READMEs and portfolios:
- **LIVE**: Publicly installable, downloadable, or accessible via URL right now.
- **REGISTERED**: Registered on an official portal; public version or review pending.
- **PREPARED**: Built and verified locally; public release package ready next.
- **IN PIPELINE**: Scheduled next in the active engineering roadmap.
- **DRAFT**: Internal working specification.

### 4.4 Sharded 4-Tier Cross-Workspace Compound Learning Framework & `/xlearn` Ratchet ([`skills/xlearn/SKILL.md`](skills/xlearn/SKILL.md) & [`docs/COMPOUND_LEARNING_PLAYBOOK.md`](docs/COMPOUND_LEARNING_PLAYBOOK.md))

XBoost `v3.6.0` pairs dedicated compound learning ([`/xlearn`](skills/xlearn/SKILL.md)) with an elastic **`L1` Router Hub + `4` `L2` Domain Shards** architecture inside the **4-Tier Playbook Cascade**, where every file stays strictly **`< 35 KB` UTF-8 LF** (well below the `46,080`-byte single-pass `read_file` truncation ceiling):

```text
[Phase 1: Hub-to-Shard Brief (/xbrief L1→L2 + /xdeep-research)] → [Phase 2: First-Principles Audit (/xboost UL-01..UL-08)] → [Phase 3: Parallel Patch + Blind Critic (/xultra)] → [Phase 4: Pre-Flight PR Gate (/xpublish)] → [Decision Gate: /xlearn Tier A (Cross-Shard /xlaya Dedup + /xsync --federated) vs Tier B (5-Gate Universal Law Sieve + Human Consent)]
```

- **Tier A — Autonomous Sharded Playbook & Federated Doc Ratchet (`/xbrief` ↔ `/xlearn` → `/xsync --federated`)**:
  - **Tier 1 `L1` Core Router Hub ([`docs/COMPOUND_LEARNING_PLAYBOOK.md`](docs/COMPOUND_LEARNING_PLAYBOOK.md), `13.7 KB` LF, `99` lines)** → **`4` `L2` Domain Shards (`5.1–11.3 KB` LF each)**:
    - [`PLAYBOOK_1A_ALGORITHMS_VECTOR_GPU_CONCURRENCY.md`](docs/playbooks/PLAYBOOK_1A_ALGORITHMS_VECTOR_GPU_CONCURRENCY.md): `13` universal code, vectorization, GPU SoA, graph CSR, memory, concurrency & MOO patterns (`PAT-*` + **`OPT-MOO-01`** across `10` prefix families).
    - [`PLAYBOOK_1B_SPATIAL_VISION_OCR_AGENTS.md`](docs/playbooks/PLAYBOOK_1B_SPATIAL_VISION_OCR_AGENTS.md): `5` spatial/GIS, canopy vision, CAD/Thai OCR, botanical `NULL` & SWE agent/container patterns (`PAT-GIS-01`, `PAT-CV-01`, `PAT-OCR-01`, `PAT-DATA-01`, `PAT-AGENT-01`).
    - [`PLAYBOOK_1C_CAD_MCP_WEB_IOT_QUANT.md`](docs/playbooks/PLAYBOOK_1C_CAD_MCP_WEB_IOT_QUANT.md): `6` desktop CAD/GIS, 4D Clifford PBR, MCP/COM IPC, DOM/SQLite, BLE IoT & Walk-Forward Quant patterns (`PAT-CAD-01`, `OPT-PBR-01`, `PAT-MCP-01`, `PAT-WEB-01`, `PAT-IOT-01`, `PAT-QUANT-01`).
    - [`PLAYBOOK_1D_FALSIFICATION_GOVERNANCE_OSS_ROLLUP.md`](docs/playbooks/PLAYBOOK_1D_FALSIFICATION_GOVERNANCE_OSS_ROLLUP.md): `13` Falsification & Mirage Guardrails (`FALS-01..13`), `7` Institutional CI Governance Fingerprints (`GOV-01..07`), and the Master Upstream OSS Rollup (`24` PRs + `1` Hold: `10 MERGED`, `9 OPEN PRs`, `1 Hold`, `5 Closed/Staged`).
  - **Tier 2 & Tier 3 Specialized Domain Playbooks**: Cascades seamlessly into **Tier 2A (`OSS PR & Deep Scan`)**, **Tier 2B (`Plant 3D & Allometry`)**, **Tier 2C (`Quant Trading & Evolution`)**, **Tier 2D + 3A–3C (`Environmental Simulation`: Wind LBM, Acoustics ISO 9613-2, Solar/SVF)**, **Tier 2E (`CanopyGIS`)**, **Tier 2F (`XLaya & SWE Agent Evolution`)**, and **Tier 2G (`SAE-LIM 9D`)**. Running `/xlearn` automatically triages cross-shard via `/xlaya`, updates the owning shard, and invokes `/xsync --federated` (`audit_workspace_docs.py` `581` LOC) so `L1` + `L2` SHA-256 mirrors never drift.
- **Tier B — Report-First Human-Consent Gate (`/xlearn` & `/xpublish`)**: Modifying global agent skills (`skills/*/SKILL.md`, `UL-01..UL-08`, or global `scripts/*.py`) or dispatching public upstream GitHub PRs requires passing the **5-Gate Universal Law Falsification Sieve** (`3-Domain Translation Proof Table` + `9-Point Mathematical Boundary Table`) + **Wave 2A Blind Counter-Domain Critic** and presenting a `Before → After` report for explicit human approval.

### 4.5 Empirical Benchmark & Token Economics ([`benchmarks/BENCHMARK_REPORT.md`](benchmarks/BENCHMARK_REPORT.md))

Reproducible multi-trial measurements (`3` warm-ups + `20-30` timed iterations via [`benchmarks/run_xboost_benchmark.py`](benchmarks/run_xboost_benchmark.py)) across `117` installed skills, `897` repository/vault markdown files (`612`-node Obsidian Second Brain), `25` seeded red-team defects, `484` real IDE sessions (`1,136` prompt turns), and **`24` real-world upstream open-source PRs + `1` Hold (`10 MERGED`)**:

| Benchmark Dimension | Unstructured / Prompt-Only Baseline | `XBoost v3.6.0` Composable `/x*` Suite | Empirical Delta & Receipt |
|:---|:---|:---|:---|
| **1. System-Prompt Discovery Guard** | `96.8%` `≤ 500`-char pass • `87.1%` dual triggers *(Official Cloud/Vendor cohort, `N=31`; All Installed `N=117`: `324.41 ± 51.29`)* | **`370.93 ± 20.15` chars** (`100%` `≤ 400`-char & `≤ 500`-char pass • `100%` `Use when` + `Do NOT use` guards across all `15` `/x*` skills) | **`0%` Sibling Skill Truncation** |
| **2. Briefing & Vault Context Compression** | `897` files (`1,770,934` tokens in Median `53.69 ms`) | **`/xbrief` (`Cap 8`) + `/xobsidian` (`2-Hop = 4` files) = `52,053` tokens** in **`1.4 ms`** (`47,436` tok / `1.19 ms` Repo-Only) | **`-97.06%` Context Noise (`34.0×`; `-97.32%` / `37.3×` Repo-Only)** |
| **3. System 1 → 1.5 `/xlaya` Section & GPU/MCP Triage** | Full-corpus read (`154,349` tokens across `28` specs / `1,017` chunks) | **Top-5 `#L<start>-L<end>` (`997` tok) in Median `147.43 ms`** (`6,898.2` chunks/s) + **`~30 ms` warm MCP** (`859.1 q/s` GPU batch, `8.9×` mixed EN/HI, `90.0%` `vega-U` routing) | **`-99.35%` Pass-B Tokens (`154.8×`) • `100%` Joint NLI Triad • `0.00%` XERJ `#1108`** |
| **4. 25-Defect Red-Team Catch Rate** | `0 / 25` (`0.0%` deterministic pre-LLM enforcement) | **`25 / 25` (`100.0%` Recall • `100.0%` Precision • `0` False Positives)** in **Median `8.14 ms`** | **10 Bundled CLI & MCP Engines (`22,237` LOC)** |
| **5. Real Turn & Session Token Depth** | `27.0` steps/turn (`14.8k` new input • `6.4k` output • `1.56M` total/turn • `1.94M` tok/session) | **`92.9` steps/turn (`3.44×`)** • **`97.8k` new input (`6.61×`)** • **`25.4k` output (`3.97×`)** • **`5.02M` tok/turn** • **`42.82M` tok/session (`22.02×`)** | **Recommended: `5×` Max (Sprints) / `20×` Ultra (Swarms & Marathons)** |
| **6. Hybrid PDF, CAD & VLM Table Extraction (`/xocr` `v2.4.0`)** | `0 / 6` tables without `pdfplumber`; faux-bold dupes; `.SHX` blindspots; CJK-on-Thai noise; split continuation tables | **`100.0%` frozen regime acc (`ECE = 0.0324`, `q_hat = 0.2046`, `21/21 pytest`)** + **Grid-Bubble, Callout Diff (`--diff-with`) & 6-Gate Multi-Page Table Stitch** + **live BMA `Typhoon-OCR v1.5` (`2,539` chars) & `RapidOCR`** | **`100%` Hybrid Vector, CAD & VLM Fidelity ([Upstream PR #16 `OPEN`](https://github.com/scb-10x/typhoon-ocr/pull/16))** |
| **7. Compound Learning & Upstream Bottleneck Acceleration (`24` PRs + `1` Hold)** | Ad-hoc cold-start scanning (`O(N²)` list/label loops, `np.vectorize` wrappers, `CRLF` diff pollution, silent `HEAD` mirages) | **`/xlearn` Sharded `L1+L2` Playbooks (`24 PAT/OPT-*`, `7 GOV-*`, `13 FALS-*`)** + `/xboost` (`UL-01..08`) + `/xpublish --platform pr` across `Batch 0`, `Group A`, `Group B` & `Group C` | **`4.0×` – `1,735.6×` Verified Speedups (`100%` Numerical Parity, `10 MERGED`, `9 OPEN PRs`)** |

#### Empirical Upstream Open-Source Speedup & Correctness Receipts (`Batch 0` + `Group A` + `Group B` + `Group C` — 24 PRs + 1 Hold)

| Upstream Repository & Target | Pattern & Governance Applied | Baseline Bottleneck / Defect | XBoost Vectorized / Surgical Fix | Measured Speedup & Test Receipt |
|:---|:---|:---|:---|:---|
| **[`ladybug-tools/uwg #292`](https://github.com/ladybug-tools/uwg/pull/292)** *(MIT, `OPEN`)* | `PAT-VEC-03`, `PAT-CACHE-01`, `PAT-GIT-01`, `GOV-02` | `sum(soil_temp)` inside `105,120`-step loop (`8.85 s`); hardcoded `[0]` climate zone (`#291`); `windProf` leak | Reuse precomputed `forcIP.deepTemp`; index `[zone_idx]`; reset `windProf` per step; preserve `CRLF` (`38`-line diff) | **`1,735.6×` speedup (`8.85 s → 5.10 ms`)** • `68/68` `pytest` PASS • **`OPEN`** |
| **[`os-climate/physrisk #651`](https://github.com/os-climate/physrisk/pull/651)** *(FINOS / Linux Foundation)* | `PAT-VEC-01..02`, `PAT-NUM-01`, `GOV-01` | `O(N²)` list comprehension in `geocode_in_place` (`541.3 ms`); `np.vectorize` in `get_impact_distrib` (`7.15 s`); caller array mutation & `left = -1` wrap | Direct key iteration (`0.32 ms`); broadcasted `scipy.stats.norm.cdf` (`0.22 s`); non-mutating `np.minimum`; clamp `np.maximum(0, right - 1)` | **`1,669.6×` & `32.5×` speedups** • `11/11` `pytest` PASS (`DCO -s`, reopened & active) |
| **[`Weecology/DeepForest #1449`](https://github.com/Weecology/DeepForest/pull/1449) & [`#1464`](https://github.com/Weecology/DeepForest/pull/1464)** | `PAT-VEC-01`, `PAT-GIS-01`, `GOV-07` | Row-wise `.iterrows()` + `shapely.geometry.box` loops in `utilities.py`, `IoU.py`, `evaluate.py`; `PathLike` rejection (`#1440`) | Vectorized `shapely.box` & `STRtree` (`421.3×` `convert_to_sv_format`, `173.9×` `IoU.match_points`, `74.4×` `utilities.py`); `os.fspath()` | **`74.4× – 421.3×` speedups** • **`#1449 MERGED (a60b890)`** (`#1464 OPEN`) |
| **[`CLIMADA-project/climada_python #1350`](https://github.com/CLIMADA-project/climada_python/pull/1350) & [`#1349`](https://github.com/CLIMADA-project/climada_python/pull/1349)** *(ETH Zürich)* | `PAT-VEC-01`, `PAT-NUM-01`, `GOV-04` | Scalar `box()` loop in `points_to_raster` (`1.49 s`); CSR column-slice loop in `impact_at_reg`; `.nonzero()` explicit-zero drop; ISO/NaN bugs (`#1331`) | Vectorized `shapely.box` (`69.9×` isolated `apply_box`, `2.1×` E2E); `imp_mat @ reg_ind` CSR matmul (`11.7×` E2E); fallback ISO & `isnan` guards | **`69.9×` & `11.7×` speedups** • **`#1350 MERGED (a1f1440)`** (`#1349 OPEN`, `base: develop`) |
| **[`gboeing/osmnx #1412`](https://github.com/gboeing/osmnx/pull/1412), [`#1410`](https://github.com/gboeing/osmnx/issues/1410) & [`#1405`](https://github.com/gboeing/osmnx/issues/1405)** | `PAT-GRAPH-01..02`, `PAT-NUM-01`, `GOV-07` | Zero-length self-loop `ZeroDivisionError` in `stats.circuity_avg` (`#1410`); `pytest-xdist` state collision in `test_simplify_graph` & `test_elevation` (`#1405`) | Guard `edge_length_total == 0` returning `np.float64(0.0)` (`PR #1412` invited by `@gboeing`); `40.2×` vectorization; `xdist_group` marker | **`40.2×` speedup** • **`#1412 MERGED`** (closed `#1410`, `100%` CI PASS) |
| **[`Deltares/hydromt #1566`](https://github.com/Deltares/hydromt/pull/1566)** *(Deltares Netherlands)* | `PAT-VEC-01`, `PAT-GIS-01`, `GOV-03` | Scalar `box()` loop in `create_mesh2d_from_geom` (`897 ms`); dropped `crs` on projected `bbox` (`#1563`); `nodata_ref = None` before warning log | C-vectorized `shapely.box` (`32.6 ms`); pass `crs=self.metadata.crs` & reproject `geom`; log `nodata_ref` before reset | **`27.5×` speedup (`897 ms → 32.6 ms`)** • `114/114` `pytest` PASS (`OPEN`) |
| **[`natcap/invest #2813`](https://github.com/natcap/invest/issues/2813) & [`#2829`](https://github.com/natcap/invest/issues/2829)** *(Stanford NatCap)* | `PAT-VEC-03`, `PAT-GIS-01`, `PAT-GIT-01`, `GOV-05` | Repeated OGR `GetFeature(fid)` + `wkb.loads` inside AOI R-tree loops (`420.2 ms` UCM, `421.6 ms` UFRM); `&` vs `\|` nodata mask | Pass-1 FID geometry cache (`23.1×` UCM `+0.51 MB` RAM) & Inverted AOI R-tree (`18.1×` `O(N)` / `2.0×` `O(M)` `0.18 MB` RAM UFRM); De Morgan `\|` mask | **`23.1×` UCM & `18.1×` UFRM speedups** • Parity verified (`#2829` on hold) |
| **[`martibosch/pylandstats #77`](https://github.com/martibosch/pylandstats/pull/77)** *(`OPEN`)* | `PAT-VEC-02`, `PAT-GIS-01` | Per-label `scipy.ndimage.center_of_mass` scan (`79.85 ms` on `66,496` patches); `landscapemetrics`-style string `edge_depths` (`#69`) | Single-pass vectorized `np.bincount(labels.ravel(), weights=...)` (`19.76 ms`) + string `edge_depths` support (`#69`) | **`4.0×` speedup (`79.85 ms → 19.76 ms`)** • `9/9` `pytest` PASS • **`OPEN`** |
| **[`opengeos/geoai #960`](https://github.com/opengeos/geoai/pull/960) (`MERGED`), [`segment-geospatial #569`](https://github.com/opengeos/segment-geospatial/pull/569) & [`mufeedvh/code2prompt #348`](https://github.com/mufeedvh/code2prompt/pull/348)** | `PAT-PARITY-01`, `PAT-CV-01`, `GOV-06` | Host `PYTHONEXECUTABLE` venv bleed (`#951`); missing `SamGeo` vector attributes (`#543`); Rust glob/token traversal in `code2prompt` | Sanitize `PYTHON*` env vars (`geoai#960` **`MERGED`** as `0b13f11`); `SamGeo` attributes (`10/10` CI, `@coderabbitai` `APPROVED`); `code2prompt#348` (`9/9` `cargo test`) | **`geoai#960 MERGED`** • **`segment-geospatial#569` & `code2prompt#348` OPEN** |
| **[`xerj-org/xerj #2922–#2927`](https://github.com/xerj-org/xerj/pulls?q=is%3Apr+author%3Anapattan) & [`scb-10x/typhoon-ocr #16`](https://github.com/scb-10x/typhoon-ocr/pull/16)** | `PAT-OCR-01`, `PAT-PARITY-01` | Sub-max image upscale (`5.11×` token bloat); legacy Thai PDF PUA junking (`exit 3`); Windows MSVC `#[cfg(unix)]` & spool lock test failures | Downscale-only `resize_if_needed` (`typhoon-ocr#16` `OPEN`, `#15` `Closed`); Rust/Python Thai PUA + Sara-Am normalizer (`xerj#2925` **`MERGED`** `b3c368b`); `.gemini/config/skills` (`#2926` **`MERGED`** `eeb8524`); `#2922–#2927` **`6/6 MERGED`** | **`-35.9%` vision tokens** • **`1,912/1,954` MSVC tests** • **`6 MERGED`** |

> **Transparency on Token Consumption**: XBoost reduces low-value file-scanning noise by **`97.06%`**, then deliberately invests that freed context capacity into **`3.44×` more verification steps** and **`6.61×` more primary-source & CLI telemetry inputs** per chained turn. While single-skill runs work comfortably on `1×` Pro plans (or local LLM endpoints), daily chained workflows (`/xbrief /xdeep-research /xboost /xlearn /xsync /xobsidian`) are best paired with **`5×` High-Throughput tiers** (Claude Max `5×`, Gemini `5×`), and `400+`-step autonomous `/goal` marathons or `/xultra` / `/xdeep-research` multi-agent swarms are engineered for **`20×` Ultra tiers** (Gemini Ultra `20×`, Claude Max `20×`).

<details>
<summary><b>LaTeX (booktabs) Source for Academic Citations — XBoost v3.6.0 Empirical Benchmark Summary</b></summary>

```latex
\begin{table}[htbp]
\centering
\caption{XBoost v3.6.0 Empirical Evaluation across Skill Discovery ($N=117$), Context Compression ($n=30$), Red-Team Recall ($N=25$), Session Telemetry ($N=484$ / $1136$ Turns), and Upstream OSS Contributions ($24$ PRs + $1$ Hold).}
\label{tab:xboost_empirical_summary}
\begin{tabular}{llcc}
\toprule
\textbf{Benchmark Dimension} & \textbf{Unstructured / Vendor Baseline} & \textbf{XBoost v3.6.0 (\texttt{/x*} Suite, $N=15$)} & \textbf{Empirical Delta} \\
\midrule
1. System-Prompt Discovery Guard & $96.8\%$ $\le 500$-char $\cdot$ $87.1\%$ dual guards & \textbf{$370.93 \pm 20.15$ chars} ($100\%$ dual guards) & \textbf{$0\%$ Sibling Truncation} \\
2. Briefing \& 2-Hop Vault Compression & $897$ files ($1,770,934$ tok in $53.69\text{ ms}$) & \textbf{$12$ files ($52,053$ tok in $1.4\text{ ms}$)} & \textbf{$-97.06\%$ Noise ($34.0\times$)} \\
3. System 1 \texttt{/xlaya} Section Triage & $154,349$ tok ($28$ specs / $1,017$ chunks) & \textbf{Top-5 ($997$ tok in $147.43\text{ ms}$; $\sim 30\text{ ms}$ MCP)} & \textbf{$-99.35\%$ Tok ($859.1\text{ q/s}$ GPU)} \\
4. 25-Defect Red-Team Catch Rate & $0 / 25$ ($0.0\%$ pre-LLM enforcement) & \textbf{$25 / 25$ ($100.0\%$ Recall in $8.14\text{ ms}$)} & \textbf{10 CLI/MCP Engines ($22,237$ LOC)} \\
5. Real Turn \& Session Token Depth & $27.0$ steps/turn ($1.94\text{M}$ tok/session) & \textbf{$92.9$ steps/turn ($42.82\text{M}$ tok/session)} & \textbf{$3.44\times$ Verification Depth} \\
6. Hybrid PDF \& Table Engine (\texttt{/xocr}) & $0/6$ tables (no \texttt{pdfplumber}) $\cdot$ raw HTML & \textbf{$19\text{--}97\text{ ms/p}$ vector ($15\text{--}3326\times$) + HTML CSV} & \textbf{$-35.9\%$ Tok / $+9.1\%$ Tab (PR \#16)} \\
7. Compound Learning \& OSS Speedups & Cold-start $O(N^2)$ / \texttt{np.vectorize} loops & \textbf{\texttt{/xlearn} Sharded Playbooks ($24$ PRs + $1$ Hold)} & \textbf{$4.0\times\text{--}1735.6\times$ Speedup ($10$ Merged)} \\
\bottomrule
\end{tabular}
\end{table}
```

</details>

---

## 5. Bundled Zero-Dependency CLI Engines

All ten bundled Python CLI & MCP engines (`22,237` total LOC) run on **Python 3.8+ standard library** (`ast`, `re`, `json`, `zipfile`, `urllib`, `configparser`, `hashlib`, `pathlib`, `ctypes`, with optional `laya` / `vegaml` acceleration in `laya_triage.py` & `xlaya_mcp_server.py` and `PyMuPDF`/`EasyOCR` in `ocr_runner.py`) with UTF-8 stream guards (`sys.stdout.reconfigure(encoding='utf-8')`) and zero bytecode pollution (`sys.dont_write_bytecode = True`):

```bash
# 1. Pre-flight security, secret, AST, Flake8, PR diff, CRLF parity & platform audit (/xpublish)
python skills/xpublish/scripts/audit_engine.py <target_dir> --platform pr --base-ref origin/main
python skills/xpublish/scripts/audit_engine.py <target_dir> --platform github
python skills/xpublish/scripts/audit_engine.py skills/<skill_name> --platform skill

# 2. Repo-agnostic workspace documentation, link, SHA-256 mirror, 4-playbook federated & stale-term auditor (/xsync)
python skills/xsync/scripts/audit_workspace_docs.py <workspace_dir> --federated --deprecated old_term

# 3. Deep-research evidence, deep-link URL & JSON schema verifier (/xdeep-research)
python skills/xdeep-research/scripts/verify_evidence.py <report.md> <dataset.json> --min-items 10 --check-http

# 4. Qt6 / QGIS 4 forward-compatibility AST scanner (/xpublish)
python skills/xpublish/scripts/check_qt6.py <plugin_dir>

# 5. Deterministic single-root QGIS plugin release packager (/xpublish)
python skills/xpublish/scripts/package_qgis.py <plugin_dir> --bump patch

# 6. IDE conversation transcript compaction, context health & cross-platform token telemetry (/xcontext)
python skills/xcontext/scripts/check_context.py
python skills/xcontext/scripts/check_context.py --days 30
python skills/xcontext/scripts/check_context.py --all-time

# 7. 3-stage System 1 -> System 1.5 breadcrumb chunker, Joint NLI contradiction & vega-U conformal triage (/xlaya)
python skills/xlaya/scripts/laya_triage.py <target_dir_or_file> --mode shortlist --query "<topic>"
python skills/xlaya/scripts/laya_triage.py <target_dir_or_file> --mode contradiction --ssot "<canonical truth>" --vega

# 8. High-speed C++ PyMuPDF vector/booktabs table extractor & 4-tier VLM/OCR engine (/xocr)
python skills/xocr/scripts/ocr_runner.py <pdf_or_image> --output ./ocr_out --mode auto --pages "1-10"

# 9. Non-intrusive Ghost Mouse, UIA COM inspector, Set-of-Mark vision capture & Multi-Agent Visual Cursor HUD (/xmouse)
python skills/xmouse/scripts/xmouse_cli.py windows
python skills/xmouse/scripts/xmouse_cli.py uia --hwnd <HWND> --depth 4
python skills/xmouse/scripts/xmouse_cli.py click --hwnd <HWND> --x 420 --y 310 --mode ghost

# 10. Resident XLaya JSON-RPC 2.0 stdio MCP Server (~30 ms warm Laya 0.4.31+ & vega-U inference with idle VRAM auto-unload) (/xlaya)
python skills/xlaya/scripts/xlaya_mcp_server.py
```

---

## 6. Universal Installation

Every XBoost skill uses portable Markdown (`SKILL.md`) with standard YAML frontmatter (`name` + `description`) and pure Python 3.8+ standard-library CLI engines. The exact same files work across **any AI coding agent — cloud, IDE, CLI, or local LLM (`Ollama`, `vLLM`, `LM Studio`, `OpenHands`, `Cline`, `Continue`, `Aider`, `Claude Code`, `Codex`, `Cursor`, `Grok`, `Gemini / Antigravity`, or custom agent frameworks)** on **Windows, macOS, and Linux**:

| Host / Agent Platform | Global Skill Root | Workspace Skill Root | Verification Status |
|:---|:---|:---|:---|
| **Gemini / Antigravity** | `~/.gemini/config/skills` | `<repo>/.agents/skills` | **`tested`** (Live E2E verified on Windows 11 across all 15 `/x*` skills & 10 Python CLI/MCP engines) |
| **Claude Code** | `~/.claude/skills` | `<repo>/.claude/skills` | **`spec-compatible`** (Path & skill schema verified via `scripts/install.ps1` & `scripts/install.sh`; live host PRs welcome) |
| **Cursor / Codex / Windsurf** | `~/.agents/skills` / `~/.codex/skills` | `<repo>/.agents/skills` | **`spec-compatible`** (Path & skill schema verified via `scripts/install.ps1` & `scripts/install.sh`; live host PRs welcome) |
| **Grok** | `$GROK_HOME/skills` or `~/.grok/skills` | `<repo>/.grok/skills` | **`spec-compatible`** (Path & skill schema verified via `scripts/install.ps1` & `scripts/install.sh`; live host PRs welcome) |
| **Local LLM & Custom Agent Frameworks** (`Ollama`, `vLLM`, `LM Studio`, `OpenHands`, `Cline`, `Continue`, `Aider`) | `~/.agents/skills` or `$AGENT_SKILLS_DIR` (`-Target <dir>` / `--target <dir>`) | `<repo>/.agents/skills` | **`spec-compatible`** (Universal Markdown `SKILL.md` + stdlib Python CLI harness; supports custom target directories via `-Target` / `--target`) |

### Option A: One-Prompt Copy-Paste Agent Install (Works with Any AI Agent — Cloud, IDE, CLI, or Local LLM)

Copy and paste this single prompt into **any AI coding agent** (Claude Code, Cursor, Codex, Gemini/Antigravity, Grok, Cline, Continue, OpenHands, or a local LLM agent):

```text
Install iscvlab/xboost (https://github.com/iscvlab/xboost): detect my OS and your active global or workspace skills directory, clone the repository, install all 15 /x* skills (Windows: ./scripts/install.ps1 -All; macOS/Linux: ./scripts/install.sh --all; or copy skills/* directly into your active skills folder), run python skills/xpublish/scripts/audit_engine.py skills/xboost --platform skill to verify the CLI harness, and confirm all 15 /x* commands are ready.
```

### Option B: Automated Multi-Agent Installer (`install.ps1 -All` / `install.sh --all` / `-Target <dir>`)

Both installers automatically remove deprecated legacy (`*x`, `unlimited-ocr`, `xpublish-audit`, `xpublish-qgis`) directories before installing the 15 `/x*` skills across all detected agent roots (or any custom `-Target` / `--target` / `$AGENT_SKILLS_DIR` path).

**Windows (PowerShell):**
```powershell
git clone https://github.com/iscvlab/xboost
cd xboost
./scripts/install.ps1 -All
# Or install into any custom / local LLM agent directory:
./scripts/install.ps1 -Target "$HOME/.continue/skills"
```

**macOS / Linux (Bash / Zsh):**
```bash
git clone https://github.com/iscvlab/xboost
cd xboost
chmod +x scripts/install.sh
./scripts/install.sh --all
# Or install into any custom / local LLM agent directory:
./scripts/install.sh --target ~/.continue/skills
```

### Option C: Direct Copy into Any Agent Skill Root (`~/.agents/skills`, `~/.<agent>/skills`, or `<repo>/.agents/skills`)

```bash
git clone https://github.com/iscvlab/xboost

# Universal .agents root (Cursor, Codex, Windsurf, Cline, OpenHands, Local LLM Agents)
mkdir -p ~/.agents/skills && cp -r xboost/skills/* ~/.agents/skills/

# Claude Code
mkdir -p ~/.claude/skills && cp -r xboost/skills/* ~/.claude/skills/

# Grok
mkdir -p ~/.grok/skills && cp -r xboost/skills/* ~/.grok/skills/

# Google Gemini / Antigravity
mkdir -p ~/.gemini/config/skills && cp -r xboost/skills/* ~/.gemini/config/skills/

# Project-local workspace (.agents/skills)
mkdir -p .agents/skills && cp -r xboost/skills/* .agents/skills/
```

To clone the `main` branch (`v3.6.0` workspace) or latest pushed release tag (`v3.5.0`):
```bash
git clone https://github.com/iscvlab/xboost
# Latest pushed release tag:
git clone --branch v3.5.0 https://github.com/iscvlab/xboost
```

---

## 7. Repository Layout

```text
xboost/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── llms.txt
├── .flake8
├── docs/
│   ├── COMPOUND_LEARNING_PLAYBOOK.md          # L1 Router Hub (~13.7 KB LF)
│   └── playbooks/                             # L2 Domain Shards (< 35 KB LF each)
│       ├── PLAYBOOK_1A_ALGORITHMS_VECTOR_GPU_CONCURRENCY.md
│       ├── PLAYBOOK_1B_SPATIAL_VISION_OCR_AGENTS.md
│       ├── PLAYBOOK_1C_CAD_MCP_WEB_IOT_QUANT.md
│       └── PLAYBOOK_1D_FALSIFICATION_GOVERNANCE_OSS_ROLLUP.md
├── benchmarks/
│   ├── run_xboost_benchmark.py
│   ├── BENCHMARK_REPORT.md
│   └── BENCHMARK_RESULTS.json
├── scripts/
│   ├── install.ps1
│   └── install.sh
└── skills/
    ├── xboost/
    │   ├── SKILL.md
    │   └── references/deep_audit_protocol.md
    ├── xbrief/
    │   └── SKILL.md
    ├── xcontext/
    │   ├── SKILL.md
    │   └── scripts/check_context.py
    ├── xcreate-skill/
    │   └── SKILL.md
    ├── xdeep-research/
    │   ├── SKILL.md
    │   └── scripts/verify_evidence.py
    ├── xkickoff/
    │   └── SKILL.md
    ├── xlaya/
    │   ├── SKILL.md
    │   ├── resources/
    │   │   └── sieve_genomes.json
    │   └── scripts/
    │       ├── laya_triage.py
    │       └── xlaya_mcp_server.py
    ├── xlearn/
    │   └── SKILL.md
    ├── xmouse/
    │   ├── SKILL.md
    │   └── scripts/xmouse_cli.py
    ├── xobsidian/
    │   └── SKILL.md
    ├── xocr/
    │   ├── SKILL.md
    │   ├── resources/
    │   │   └── xocr_genomes.json
    │   └── scripts/ocr_runner.py
    ├── xplan/
    │   └── SKILL.md
    ├── xpublish/
    │   ├── SKILL.md
    │   ├── references/
    │   │   ├── github_readme_protocol.md
    │   │   └── qgis_release_protocol.md
    │   └── scripts/
    │       ├── audit_engine.py
    │       ├── check_qt6.py
    │       └── package_qgis.py
    ├── xsync/
    │   ├── LICENSE
    │   ├── SKILL.md
    │   └── scripts/
    │       ├── README.md
    │       └── audit_workspace_docs.py
    └── xultra/
        └── SKILL.md
```

---

## 8. Related Toolkits & Author

- **[xlaya](https://github.com/iscvlab/xlaya)** (`v2.4.0` Wave 1 Core + Wave 2 Wallacei `v2.7` MOO · latest remote tag [`v2.3.0 LIVE`](https://github.com/iscvlab/xlaya/releases/tag/v2.3.0)): Standalone 5-profile System 1 → System 1.5 semantic decision, AST/brace-code sieve & `vega-U` conformal triage package (`laya 0.4.31+` & `vegaml 0.16.1+`), pairing `--profile nano` zero-PyTorch/NumPy `8.50–10.41 MB` ΔRSS (`255.3 ms` cold repo, `6,237 B` LF `sieve_genomes.json`, `4-PC` `.npz` whitening, smooth `M_avail`, `65.12%` `E4B R@3` / `79.07%` `31B R@8` / `0.0568 & 0.0535` `ECE` blind `Kaggle 129`, `78.72%` `31B R@8` & `0.0293` `ECE` `SWE-bench_Verified`, `71.69%` `When2Call` Test MCQ / `81.37%` Val conformal `ToolGate`, `22/22` pytest) and declarative Container-A ADK bundles with 6-tool AST-reloading JSON-RPC 2.0 `stdio` MCP (`~30 ms`), `859.1 q/s` GPU batch routing (`8.9×` mixed EN/HI), `0.45/0.55` ensemble jury, `TTTHead` calibration (`85%` / `90%` `5-fold`), local multimodal, and `0.00%` `xerj#1108` wrong-and-confident fires (`100%` `48/48`).
- **[xocr](https://github.com/iscvlab/xocr)**: High-speed C++ PyMuPDF CAD/PDF extractor (`v2.4.0` local · latest remote tag [`v2.1.0 LIVE`](https://github.com/iscvlab/xocr/releases/tag/v2.1.0), `7,455` LOC), Grid-Bubble axis parser, Cross-Sheet Callout Graph & jitter-tolerant `--diff-with` revision diff, 6-Gate multi-page Table Stitching (`19-97 ms/page`, `15.0×-3,326×` faster hybrid routing), Thai PUA/Sara-Am normalizer, and 5-Profile local `SCB 10X Typhoon-OCR v1.5` (`Qwen3-VL`) & `baidu/Unlimited-OCR-2` engine (**[Upstream PR #16 to `scb-10x/typhoon-ocr` (`OPEN`)](https://github.com/scb-10x/typhoon-ocr/pull/16)** & **[Upstream PR #2925 to `xerj-org/xerj` (`MERGED`)](https://github.com/xerj-org/xerj/pull/2925)**).
- **[mcp-bridges](https://github.com/iscvlab/mcp-bridges)**: Model Context Protocol (MCP) automation bridges (`8` skills, `330.75 chars` Mean YAML) for **AutoCAD, QGIS, Rhino 3D, Grasshopper, Adobe Illustrator, and Figma** with Parallel-Brains Single-Mouse serialization (**Selected for the [XERJ Corpus Hub](https://hub.xerj.org)**).
- **[sse-space-syntax](https://github.com/iscvlab/sse-space-syntax)**: High-performance Space Syntax, Angular Segment Analysis (ASA), Axial/Stroke topology, Visibility Graph Analysis (VGA), and Ray-Cast Isovist engine (`v1.1.1 LIVE`).
- **[qgis-axonometric-transformer](https://plugins.qgis.org/plugins/axonometric_transformer/)**: Official QGIS plugin (Plugin ID: `6219`, `v1.2.2 LIVE`) for 1-click isometric, dimetric, and oblique axonometric map diagrams.
- **24 Upstream Open-Source PRs + 1 Hold (`10 MERGED` across `Batch 0` + `Group A` + `Group B` + `Group C`)**:
  - **Batch 0 — Agent & Document AI Infrastructure (`8` PRs)**: **[`xerj-org/xerj` (`#2922–#2927`)](https://github.com/xerj-org/xerj/pulls?q=is%3Apr+author%3Anapattan)** ([`#2922`](https://github.com/xerj-org/xerj/pull/2922), [`#2923`](https://github.com/xerj-org/xerj/pull/2923), [`#2924`](https://github.com/xerj-org/xerj/pull/2924), [`#2925`](https://github.com/xerj-org/xerj/pull/2925), [`#2926`](https://github.com/xerj-org/xerj/pull/2926), [`#2927`](https://github.com/xerj-org/xerj/pull/2927) `6/6 MERGED` + [`#1108`](https://github.com/xerj-org/xerj/issues/1108) `/xlaya` boundary benchmark) and **[`scb-10x/typhoon-ocr #16`](https://github.com/scb-10x/typhoon-ocr/pull/16)** (`OPEN`, `-35.9%` vision token reduction & lossless PNG; `#15` `Closed`).
  - **Group A — Geospatial & Vision (`6` PRs)**: **[`opengeos/geoai #960`](https://github.com/opengeos/geoai/pull/960)** (`MERGED` as `0b13f11`, Tri-OS venv isolation, `40/40` `pytest`), **[`Weecology/DeepForest #1449`](https://github.com/Weecology/DeepForest/pull/1449)** (`MERGED` `a60b890`, `74.4×–421.3×` Shapely 2.0 speedups closing [`#1447`](https://github.com/Weecology/DeepForest/issues/1447)) & **[`#1464`](https://github.com/Weecology/DeepForest/pull/1464)** (`OPEN`, `#1440` `os.fspath` `PathLike`), **[`gboeing/osmnx #1412`](https://github.com/gboeing/osmnx/pull/1412)** (`MERGED`, closed `#1410`, `stats.circuity_avg` zero-distance guard + `40.2×` speedup), **[`martibosch/pylandstats #77`](https://github.com/martibosch/pylandstats/pull/77)** (`OPEN`, `4.0×` vectorized `np.bincount` patch centroids + string `edge_depths`, `9/9` `pytest`), and **[`opengeos/segment-geospatial #569`](https://github.com/opengeos/segment-geospatial/pull/569)** (`OPEN`, `SamGeo` attributes & state reset, `10/10` CI, CodeRabbit `APPROVED`).
  - **Group B — Climate Risk, ESG & Urban Physics (`6` PRs + `1` Hold)**: **[`CLIMADA-project/climada_python #1350`](https://github.com/CLIMADA-project/climada_python/pull/1350)** (`MERGED` `a1f1440` into `develop`, `69.9×` `points_to_raster` & `11.7×` `impact_at_reg` CSR matmul speedups) & **[`#1349`](https://github.com/CLIMADA-project/climada_python/pull/1349)** (`OPEN`, `Fixes #1331` finance ISO/GDP, `17/17` tests), **[`ladybug-tools/uwg #292`](https://github.com/ladybug-tools/uwg/pull/292)** (`OPEN`, `Fixes #291` climate zone indexing + `1,735.6×` deep-soil loop speedup + `windProf` leak fix, `68/68` `pytest`), **[`os-climate/physrisk #651`](https://github.com/os-climate/physrisk/pull/651)** (`OPEN`, `32.5×` `norm.cdf` & `1,669.6×` `geocode_in_place` speedups + curve/CDF fixes, `11/11` `pytest`), **[`Deltares/hydromt #1566`](https://github.com/Deltares/hydromt/pull/1566)** (`OPEN`, `Fixes #1563` projected `bbox` CRS + `27.5×` `shapely.box` mesh grid speedup, `114/114` `pytest`), and **[`natcap/invest #2813`](https://github.com/natcap/invest/issues/2813) & [`#2829`](https://github.com/natcap/invest/issues/2829)** (`Hold` — `23.1×` Urban Cooling & `18.1×` Urban Flood; `#2839` `Closed`).
  - **Group C — Urban Climate & Developer Tooling (`4` PRs)**: **[`mufeedvh/code2prompt #348`](https://github.com/mufeedvh/code2prompt/pull/348)** (`OPEN`, Rust glob/token traversal fix, `9/9` `cargo test` PASS) and `UMEP-dev` (`3` Staged split-remediations: **[`UMEP #885`](https://github.com/UMEP-dev/UMEP/pull/885)** `173.0×` UTCI, **[`UMEP-processing #149`](https://github.com/UMEP-dev/UMEP-processing/pull/149)** `799.8×` `load_walls`, **[`umep-solweig #6`](https://github.com/UMEP-dev/umep-solweig/pull/6)**).

**Napat Phasundhiae**  
*Computational Design Technologist | Spatial Analytics • Urban & Environmental Simulation • Workflow Automation*

- GitHub: [@napattan](https://github.com/napattan) · [ISCV | Isocurve Research Lab (@iscvlab)](https://github.com/iscvlab)
- LinkedIn: [linkedin.com/in/napatphas](https://www.linkedin.com/in/napatphas/)

## License

Released under the [MIT License](LICENSE).
