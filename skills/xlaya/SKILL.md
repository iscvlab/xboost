---
name: xlaya
description: >
  System 1 fast semantic decision, section shortlisting, and conflict triage sidecar (/xlaya, /laya).
  Use when running /xlaya or /laya standalone or chained (/xsync /xlaya, /xbrief /xlaya, /xdeep-research /xlaya, /xpublish /xlaya)
  for local classification (choice), scoring (score), or truth validation (noul).
  Do NOT use for prose generation or code authoring (/xboost).
---

# `/xlaya` (System 1 Decision & Semantic Triage Sidecar)

A lightweight, non-autoregressive **System 1 decision layer** for agent workflows (`/xlaya`, alias `/laya`), powered by the local `laya` Python library (`convaiinnovations/laya` and `convaiinnovations/laya-multilingual`) and the bundled [`laya_triage.py`](scripts/laya_triage.py) CLI engine.

Runs as a standalone decision helper or as a pluggable zero-token accelerator chained with other `/x...` skills (`/xsync /xlaya`, `/xbrief /xlaya`, `/xplan /xlaya`, `/xdeep-research /xlaya`, `/xpublish /xlaya`, `/xlaya /xultra`).

Operates on **Dual-Process Cognitive Architecture**:
- **System 1 (`laya` Python Engine)**: Ultra-fast, zero-LLM-token local semantic triage (`output_tokens: 0`), fence-safe heading chunking (`≤ 1,200` chars / `~300` tokens fitting `ModernBERT-large`'s `512`-token window), section shortlisting (`shortlist`), ordinal scoring (`score`), and calibrated contradiction testing (`noul`).
- **System 2 (Host AI Agent)**: Deep deliberative reasoning, surgical code/doc editing (`edit_file`), tool execution, and strategic synthesis.

> [!IMPORTANT]
> **Does `/xlaya` Need `/goal`? No — It Needs a Question Schema (`--query` / `--ssot` / `questions`)**:
> Unlike System 2 LLMs that iterate across multi-step tool loops (where `/goal` prevents early stopping), `laya` executes a **single deterministic encoder forward pass** (`output_tokens: 0`). However, because its decision head cross-attends your `instructions` and `criteria` against each text chunk, every `/xlaya` call MUST specify an explicit question schema (`--query`, `--ssot`, `--labels`, or `questions={...}`).

---

## 1. When to Use & When NOT to Use

| Need | Action |
|:---|:---|
| **Fast semantic contradiction hunting across docs** | Chain [`/xsync`](../xsync/SKILL.md) `/xlaya` (`laya_triage.py --mode contradiction --ssot "..."`) |
| **Shortlisting relevant `#L<start>-L<end>` sections in a large doc corpus** | Chain [`/xbrief`](../xbrief/SKILL.md) `/xlaya` or [`/xplan`](../xplan/SKILL.md) `/xlaya` (`laya_triage.py --mode shortlist --query "..."`) |
| **Scoring documentation completeness or filtering scraped candidates** | Chain [`/xdeep-research`](../xdeep-research/SKILL.md) `/xlaya` (`laya_triage.py --mode rubric`) |
| **Deduplicating & triaging compound learning Playbook patterns** | Chain [`/xlearn`](../xlearn/SKILL.md) `/xlaya` (`laya_triage.py --mode shortlist` & `contradiction`) |
| **Pre-flight public claim verification (`LIVE` vs `PREPARED`)** | Chain [`/xpublish`](../xpublish/SKILL.md) `/xlaya` (`laya_triage.py --mode contradiction`) |
| **Large-scale bilingual (Thai + English) text classification / scoring** | Run `/xlaya` standalone (`--mode classify` or Python API, auto-routed via `laya.is_english()`) |
| **Text generation, rewriting prose, or authoring code** | Do NOT use `/xlaya` (Delegate to Host Agent System 2 / [`/xboost`](../xboost/SKILL.md)) |
| **Exact keyword, symbol, or regex lookup** | Do NOT use `/xlaya` (Use native grep / `rg` / `Select-String`) |

---

## 2. Bundled CLI Engine (`scripts/laya_triage.py`)

Prefer invoking [`scripts/laya_triage.py`](scripts/laya_triage.py) instead of writing ad-hoc inline Python scripts. It automatically:
1. **Splits `.md` / `.html` / `.txt` files on fence-safe Markdown headings (`≤ 1,200` chars ≈ `300` tokens)** while tracking exact 1-based `#L<start>-L<end>` line numbers so zero text is ever truncated by `ModernBERT-large`'s `512`-token context window (`512` max − `192` head tokens = `320` state tokens).
2. **Auto-routes English vs Multilingual checkpoints** via `laya.is_english()` (`convaiinnovations/laya` for English; `subfolder="multilingual"` for Thai / bilingual text).
3. **Gracefully degrades** to a deterministic pure-Python scorer if `laya` is not installed.

### CLI Execution (`<SKILL_DIR>` = directory containing this `SKILL.md`)
```bash
# 1. Shortlist top-K sections (#L<start>-L<end>) for /xbrief or /xplan
python "<SKILL_DIR>/scripts/laya_triage.py" <path> --mode shortlist --query "<target topic>" --top-k 8

# 2. Hunt semantic contradictions against canonical SSOT for /xsync or /xpublish
python "<SKILL_DIR>/scripts/laya_triage.py" <path> --mode contradiction --ssot "<canonical truth>" --threshold 0.60

# 3. Score technical completeness rubric (0..4) + optional SSOT check
python "<SKILL_DIR>/scripts/laya_triage.py" <path> --mode rubric --ssot "<canonical truth>"

# 4. Classify chunks into caller-defined categories
python "<SKILL_DIR>/scripts/laya_triage.py" <path> --mode classify --labels "arch:Architecture|cli:CLI engines|guide:Workflow guide"
```

---

## 3. Core Primitives Specification (Python API)

When embedding `laya` directly in custom Python pipelines (`v0.3.10+`), every question definition MUST include `"type"` (`"choice"`, `"score"`, or `"noul"`) and `"instructions"`:

```python
import laya

# Auto-detect English vs Thai/Multilingual with zero PyTorch overhead:
model_sub = None if laya.is_english(state_text) else "multilingual"
agent = laya.load("convaiinnovations/laya", subfolder=model_sub)

questions = {
    # 1. choice: Calibrated categorical distribution across caller-defined labels (dict or list)
    "category": {
        "type": "choice",
        "instructions": "Classify the primary software engineering section category.",
        "criteria": {
            "architecture": "System architecture, module seams, dataflow diagrams, and design invariants",
            "runtime_cli": "CLI execution flags, deterministic runners, and runtime performance benchmarks",
            "verification": "Unit test suites, perturbation probes, and regression verification gates",
        },
    },
    # 2. score: Ordinal rubric (criteria is a list of level descriptions, index 0 first)
    "completeness_score": {
        "type": "score",
        "instructions": "Rate the technical completeness and specificity of this documentation.",
        "criteria": [
            "Single-sentence stub lacking concrete versions or CLI scripts",
            "Brief overview with minimal technical detail",
            "Moderate specification with partial architecture details",
            "Detailed specification covering core architecture and versions",
            "Exhaustive production specification with exact versions, CLI engines, and invariants",
        ],
    },
    # 3. noul: Calibrated boolean truth/contradiction hypothesis P(true) in ans["noul"]
    "is_contradicting_ssot": {
        "type": "noul",
        "instructions": "Does this statement contradict the canonical project facts?",
        "criteria": {
            "false": "Consistent with canonical versions, CLI scripts, and architecture.",
            "true": "References deprecated counts, wrong script names, or contradictory status.",
        },
    },
}

# Single state or batched multi-state evaluation:
res = agent.predict(state_text, questions)              # -> res["answers"][qid]
batch_res = agent.predict_batch(state_list, questions)  # -> list of res dicts
```

Built-in high-level integrations in `laya`:
- `laya.is_english(text)` / `laya.lang.analyse(text)`: Pure-Python script detection (`Thai`, `CJK`, `Latin`, etc.).
- `laya.embed_fn_from_agent(agent)` & `laya.predict_shortlist(...)`: Mean-pooled encoder embeddings for `> 20` choice labels.
- `LayaRouter`, `LayaTriage`, `LayaEvaluator`, `LayaGuardrail`: High-level routing, batch scoring, and guardrail wrappers.

---

## 4. SOP: Execution & Graceful Degradation Protocol

Every execution of `/xlaya` MUST adhere to the following sequence:

### Step 1: Run `laya_triage.py` (or Probe Environment)
Invoke [`scripts/laya_triage.py`](scripts/laya_triage.py) on the target file/directory with the appropriate `--mode` (`shortlist`, `contradiction`, `rubric`, or `classify`).

### Step 2: Act on Calibrated Output
1. **Clean / Low-Risk Chunks (`P(contra) < 0.30` or `score < 2.0`)**: Skip without loading into the LLM context window.
2. **High-Signal / Flagged Chunks (`P(contra) ≥ 0.60` or top-K `score`)**: Inspect only the exact `file.md#L<start>-L<end>` ranges reported by `laya_triage.py` using `read_file` (`StartLine` / `EndLine`), then apply surgical edits via `edit_file`.
3. **Graceful Fallback**: If `laya` is not installed (`model=pure-python-fallback`), `laya_triage.py` still outputs deterministic heading chunks and lexical scores with exit code `0` — never halt or crash the session.

---

## 5. Chained Skill Combinations

### 5.1 [`/xsync`](../xsync/SKILL.md) + `/xlaya` (`/xsync /xlaya` — Semantic Contradiction Hunter)
- **Role Division**:
  - `/xlaya` runs `laya_triage.py --mode contradiction --ssot "..."` across `.md` and `.html` heading chunks to spot semantic contradictions against the canonical SSOT that keyword grep misses.
  - `/xsync` manages the 5-Tier Document Matrix and applies surgical fixes via `edit_file`.

### 5.2 [`/xbrief`](../xbrief/SKILL.md) / [`/xplan`](../xplan/SKILL.md) + `/xlaya` (`/xbrief /xlaya` — Large-Corpus Section Shortlisting)
- **Role Division**:
  - When exploring an unfamiliar or multi-file documentation tree, `/xlaya` runs `laya_triage.py --mode shortlist --query "..."` to return exact `file.md#L<start>-L<end>` line ranges.
  - `/xbrief` or `/xplan` then executes Pass B (`read_file`) strictly on those shortlisted line ranges, saving massive context tokens.

### 5.3 [`/xdeep-research`](../xdeep-research/SKILL.md) + `/xlaya` (`/xdeep-research /xlaya` — Candidate Triage)
- **Role Division**:
  - Between Wave 2 (Harvester Swarm) and Wave 3 (Blind Adversarial Auditor), `/xlaya` scores harvested candidates using `--mode rubric` (`score` + `noul`) to prune low-specificity stubs before spawning expensive Auditor subagent turns.

### 5.4 [`/xpublish`](../xpublish/SKILL.md) + `/xlaya` (`/xpublish /xlaya` — Public Claim Verifier)
- **Role Division**:
  - `/xpublish` runs deterministic AST, secret, path, and packaging checks via `audit_engine.py`.
  - `/xlaya` evaluates README and release prose using `--mode contradiction` to verify that public status claims (`LIVE`, `REGISTERED`, `PREPARED`, `IN PIPELINE`) match verifiable receipts.

### 5.5 [`/xultra`](../xultra/SKILL.md) + `/xlaya` (`/xlaya /xultra` — System 1 Gatekeeper Before System 2 Swarm Fan-Out)
- **Role Division**:
  - `/xlaya` executes Law 1 deterministic pre-filtering (`laya_triage.py --mode shortlist`, `contradiction`, or `rubric`) in milliseconds with `0` LLM output tokens, pruning clean or low-signal chunks before any subagent is spawned.
  - `/xultra` then fans out System 2 Builder/Critic shards strictly on the high-signal or flagged `#L<start>-L<end>` targets.

### 5.6 [`/xlearn`](../xlearn/SKILL.md) & [`/xocr`](../xocr/SKILL.md) + `/xlaya` (`/xlearn /xlaya`, `/xocr /xlaya`)
- **Role Division**:
  - Paired with [`/xlearn`](../xlearn/SKILL.md), `/xlaya` shortlists existing `OPT-*`/`FALS-*`/`GOV-*` rows across the 3-Tier Playbooks so session findings merge cleanly without duplicate rows.
  - Paired with [`/xocr`](../xocr/SKILL.md), `/xlaya` shortlists high-signal `## Page N` sections from `extracted_document.md` in milliseconds before System 2 reading.

---

## 6. Formatting & Typography Rules

- **Zero-LaTeX Math Policy**: In all generated outputs and terminal logs, NEVER use LaTeX syntax (`$...$`). ALWAYS use direct Unicode: `→`, `←`, `•`, `✓`, `✨`, `²`, `³`, `°`, `×`, `÷`, `±`, `≈`, `≤`, `≥`.
- **ASCII Dash Convention**: Use standard ASCII hyphens `-` for bullet points and separators.
- **Table Formatting**: Use GitHub Flavored Markdown (GFM) tables with outer pipes (`| Col 1 | Col 2 |`).
