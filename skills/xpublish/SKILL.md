---
name: xpublish
description: >
  Pre-flight security/AST audit, upstream PR & review-bot convergence, QGIS Qt6 zip packaging, and GitHub/Food4Rhino/skill release framework (/xpublish, /xpublish-audit, /xpublish-qgis, /publish).
  Use when running /xpublish, scanning secrets/paths, shipping PRs, packaging QGIS zips, or auditing global skills.
  Do NOT use for workspace doc sync (/xsync) or authoring skills (/xcreate-skill).
---

# Unified Publishing, Pre-Flight Audit & Upstream PR Framework (`/xpublish`)

> **Scope**: Deterministic pre-flight security/AST/privacy auditor, diff-scoped upstream PR verifier, and reproducible release packager across GitHub, Official QGIS Plugin Portal, McNeel Food4Rhino/YAK, and global AI agent skills (`/xpublish`, aliases `/xpublish-audit`, `/xpublish-qgis`, `/publish-audit`, `/publish-qgis`, `/publish`).  
> **Core Invariants**: `0` leaked secrets (`16` high-entropy signatures), `0` hardcoded user paths (`Dual-OS`), `0` unsafe AST calls, diff-isolated `--platform pr` hygiene (`PAT-GIT-01` `LF`/`CRLF` parity), `≤ 400`-char target skill YAML budget (`Check 4B–4D`), publication-grade vector-first figures (`v1.5 §3.D`), and fixed-epoch `(2026, 1, 1)` Qt6-compliant QGIS `.zip` archives.  
> **Active Engine & Reference Files**: [`scripts/audit_engine.py`](scripts/audit_engine.py) • [`scripts/check_qt6.py`](scripts/check_qt6.py) • [`scripts/package_qgis.py`](scripts/package_qgis.py) • [`references/github_readme_protocol.md`](references/github_readme_protocol.md) (`v1.5`) • [`references/qgis_release_protocol.md`](references/qgis_release_protocol.md)

---

## 1. Platform Profiles, Security Gates & End-to-End Actions (`--platform`)

Engine flag `--platform`: `pr` | `github` | `qgis` | `food4rhino` | `skill` | `generic`.

| Profile | Blocking Gates (Must Fix Before Ship) | Advisory Checks | End-to-End Packaging & Shipping Protocol |
| :--- | :--- | :--- | :--- |
| **`pr`**<br>*(Upstream Pull Request)* | **Diff-scoped (`git diff` touched lines/files only)**: leaked secrets/tokens; hardcoded machine user paths (`C:\Users\<user>`, `/Users/<user>/`, `/home/<user>`); Python `SyntaxError` or unsafe AST calls (`eval`, `exec`, `shell=True`, `pickle`) on added lines; Flake8 violations on added lines; accidental `CRLF` injection or `100644 → 100755` file-mode flip; untracked unignored worktree debris (`git status --porcelain`); unconfigured OS placeholder git author (`User`, `Admin`, `root`, `ubuntu`, `runner`, `localhost`) | Upstream `CONTRIBUTING.md` & PR template check; review-bot inline + outside-diff convergence | Follow [`references/github_readme_protocol.md`](references/github_readme_protocol.md) (`§6`): Dual-Credit Fork, Issue-Claim Etiquette, `Fixes #N` vs. `Part of #N` parity, `≤ 4`-col PR tables, `UTF-16LE` zero-mojibake clipboard, and Review-Bot Convergence (`@coderabbitai`). |
| **`github`**<br>*(Public Repository Release)* | Secrets/tokens; hardcoded machine user paths; **missing `LICENSE`**; Python `SyntaxError` or unsafe AST calls; Flake8 violations | Missing `README.md`; packaging debris; `README.md` words `Published` / `LIVE` / `1-click install` without receipt | Follow [`references/github_readme_protocol.md`](references/github_readme_protocol.md) (`v1.5`, `§1–§5`, `§7–§8`): `0 ms` 20-block Unicode bar charts, White-Mode Mermaid (`< 30 KB` SVG), publication-grade vector-first static figures (`§3.D`, pre-rendered image embeds in Release Notes), `<details>` disclosure, and cross-account profile sync. |
| **`qgis`**<br>*(Official QGIS Plugin Repo)* | Secrets/tokens; machine user paths; unescaped `%` in `metadata.txt`; missing required metadata fields; `__init__.py` lacking `def classFactory(iface)`; Qt6/QGIS 4 AST violations ([`scripts/check_qt6.py`](scripts/check_qt6.py)); Flake8 violations; unsafe AST calls | Packaging debris; missing `icon.png`; broad `except Exception: pass` without `# nosec B110` | Run [`scripts/package_qgis.py`](scripts/package_qgis.py) (`--bump patch\|minor\|major`) and follow [`references/qgis_release_protocol.md`](references/qgis_release_protocol.md) for single-root `.zip` build and `plugins.qgis.org` upload. |
| **`food4rhino`**<br>*(Rhino / GH Package)* | Secrets/tokens; machine user paths; **no compiled `.gha` or `.dll`**; unsafe AST calls | Missing sample `.gh` canvas | Verify compiled `.gha`/`.dll` assembly and sample `.gh` canvas before uploading to Food4Rhino / YAK. |
| **`skill`**<br>*(Global Agent Skill)* | Missing/malformed `SKILL.md` frontmatter; invalid `name` (`^[a-z0-9-]+$` or `> 64` chars); `description > 1024` chars; machine user paths; secrets; backslashes `\` in markdown links; recursive self-nesting (`skill/skill`); `SyntaxError` in `scripts/*.py` | Isolated workspace `.agents/skills/` silo instead of Global Agent Skills Root (`<GLOBAL_SKILLS_ROOT>`); `description > 500` chars (`≤ 400` target); `SKILL.md > 500` lines; missing `Do NOT use for...`; `disable-model-invocation: true`; Bucket 3 magic quotas, Gate 3 over-specific equations, raw LaTeX macros outside code spans, or persona strings; missing UTF-8/bytecode header in `scripts/*.py` | Enforce the 5-Gate Universal Law Falsification Protocol in [`/xcreate-skill`](../xcreate-skill/SKILL.md) and [`/xlearn`](../xlearn/SKILL.md) and commit to the global skills git ledger. |
| **`generic`**<br>*(General Deliverable)* | Secrets/tokens; machine user paths; Python `SyntaxError` or unsafe AST calls; Flake8 violations | Packaging debris (`.pyc`, `__pycache__`, `.DS_Store`, `Thumbs.db`); missing `README`/`LICENSE` | Clean all blocking security/path issues and strip temporary scratch debris before handoff. |

Public-claim **vocabulary** (`LIVE`, `REGISTERED`, `PREPARED`, `IN PIPELINE`, `DRAFT`) is owned by [`/xsync`](../xsync/SKILL.md). This skill advises on unverified `Published` / `LIVE` / `1-click install` claims in README files.

---

## 2. 6-Pillar Security, Quality & Packaging Architecture

1. **High-Entropy Secret & Dual-OS Privacy Gate (`0` Leaks)**:
   - Screens `pat.finditer()` multi-token lines against 16 credential signatures: AWS, GitHub Classic & Fine-Grained PATs, OpenAI, Anthropic, Google AI, HuggingFace, PyPI, GitLab, NPM, Stripe, SendGrid, Discord Webhooks, RSA/SSH private keys, and DB URIs.
   - **Dual-OS Path Invariant**: Blocks hardcoded developer home paths (`C:\Users\<user>`, `/Users/<user>/`, `/home/<user>`), enforcing dynamic environment resolution (`%USERPROFILE%`, `%APPDATA%`, `~`, `<SKILL_DIR>`).
2. **Python AST Vulnerability & Bytecode Inspector**:
   - Parses Python ASTs to block arbitrary code execution (`eval()`, `exec()`, `compile()`), shell injection (`os.system()`, `subprocess.*(..., shell=True)`), insecure deserialization (`pickle.load()`, `pickle.loads()`), and race-prone temp files (`tempfile.mktemp()`).
3. **Diff-Scoped PR Gate (`--platform pr`) vs. Full-Tree Audit**:
   - Restricts secret, home-path, AST, and Flake8 checks strictly to **added/modified lines in `git diff`** so pre-existing upstream lint debt never triggers false blocks.
   - Enforces clean worktree state (`git status --porcelain`), upstream line-ending preservation (`LF` vs. `CRLF`, preventing whole-file diff explosions), file mode preservation (`100644`), closing-keyword vs. base-branch parity, and non-placeholder Git author identity.
4. **Agent Skill Invariant Enforcer (`--platform skill`)**:
   - Enforces Universal Globalization (`<GLOBAL_SKILLS_ROOT>`), context-budget discipline (`description ≤ 400` chars target / `≤ 500` advisory, `SKILL.md ≤ 500` lines `Check 4C`), POSIX `/` markdown links, link target existence, zero raw LaTeX macros outside code spans (`Check 4D`), and zero Bucket 3 magic quotas or Gate 3 over-specific domain equations (`Check 4B`).
5. **Deterministic Platform Packagers (`QGIS` / `GitHub` / `Food4Rhino`)**:
   - **QGIS (`--platform qgis`)**: Pairs [`scripts/check_qt6.py`](scripts/check_qt6.py) (1-level & 2-level `qgis.PyQt` scoped enum AST visitor for the **"QGIS 4 Ready"** badge) with [`scripts/package_qgis.py`](scripts/package_qgis.py) (5-rung slug resolver, SemVer bumper, scanner-config stripper, and fixed-epoch `(2026, 1, 1)` single-root `.zip` builder; full spec in [`references/qgis_release_protocol.md`](references/qgis_release_protocol.md)).
   - **GitHub & Upstream PRs (`--platform github` / `--platform pr`)**: Enforces archetype-adaptive `TL;DR` hierarchy, `0 ms` 20-block Unicode bars, White-Mode Mermaid (`< 30 KB` SVG), publication-grade vector-first static figures (`§3.D`, `0` hybrid KPI-card posters, pre-rendered Release image embeds via `/diagram-design` & `/illustrator`), Dual-Credit Fork authorship, and Review-Bot convergence in [`references/github_readme_protocol.md`](references/github_readme_protocol.md).
6. **Build & OS Debris Sanitizer**:
   - Detects and strips non-runtime artifacts (`.pyc`, `__pycache__`, `Thumbs.db`, `.DS_Store`, `.swp`, `.env`, `scratch*`, and portal scanner configs).

---

## 3. Deterministic CLI Execution

Run the bundled scripts relative to this skill's directory (`<SKILL_DIR>`):

### A. Universal Pre-Flight Audit Engine ([`scripts/audit_engine.py`](scripts/audit_engine.py))

```bash
# Audit any target profile (pr | github | qgis | food4rhino | skill | generic):
python "<SKILL_DIR>/scripts/audit_engine.py" <target_dir> --platform <pr|github|qgis|food4rhino|skill|generic>
```

*Optional Flags*:
- `--base-ref <git_ref>`: Explicit base ref for `--platform pr` diff comparison (defaults to staged/unstaged diff if dirty, or `HEAD~1..HEAD` if clean).
- `--skip-flake8`: Bypass Flake8 code quality checks when Flake8 is unavailable.
- `--skip-qt6`: Bypass Qt6 AST forward-compatibility check for `--platform qgis`.

### B. QGIS Qt6 Checker & Deterministic ZIP Packager ([`scripts/check_qt6.py`](scripts/check_qt6.py) & [`scripts/package_qgis.py`](scripts/package_qgis.py))

```bash
python "<SKILL_DIR>/scripts/check_qt6.py" "<plugin_dir>"
python "<SKILL_DIR>/scripts/package_qgis.py" "<plugin_dir>" --bump patch
```
*(See [`references/qgis_release_protocol.md`](references/qgis_release_protocol.md) for the scoped Qt6 enum migration table, 5-rung package slug ladder, and `plugins.qgis.org` upload steps).*

---

## 4. Composable XBoost Skill Combinations (`/xpublish` × `/x*` × `/browser`)

| Chained Command | End-to-End Execution Synergy |
| :--- | :--- |
| **[`/xdeep-research`](../xdeep-research/SKILL.md) [`/xboost`](../xboost/SKILL.md) [`/xultra`](../xultra/SKILL.md) `/xpublish`** *(+ optional `/browser`)* | **End-to-End Upstream PR & Release Pipeline**:<br>1. **Fetch & Triage (`Law 1 API/CLI` + Bounded `/browser`)**: Inspect `CONTRIBUTING.md`, issue comments, and open PRs via GitHub API/CLI (`gh`, `urllib`) in milliseconds; use `/browser` (`< 30s`) only for authenticated user sessions (Gmail notifications, web dashboards) or visual DOM/diagram inspection.<br>2. **Build & Verify ([`/xboost`](../xboost/SKILL.md) [`/xultra`](../xultra/SKILL.md))**: Implement minimal surgical fix on a feature branch (`MPLBACKEND=Agg` for headless tests) + Blind Critic audit.<br>3. **Pre-Flight & Ship (`/xpublish --platform pr`)**: Run `audit_engine.py <repo> --platform pr`, verify `Fixes #N` (100% parity) vs. `Part of #N` (partial scope) in [`references/github_readme_protocol.md`](references/github_readme_protocol.md) (`§6.D`), push branch, and converge all inline + `outside_diff_range_comments` review-bot feedback to `APPROVED`. |
| **`/xpublish` + [`/xlaya`](../xlaya/SKILL.md)** | **System 1 Public Claim Verifier**: Pairs `audit_engine.py` with [`/xlaya`](../xlaya/SKILL.md) (`laya_triage.py --mode contradiction`) to verify that `LIVE` / `REGISTERED` / `PREPARED` claims in READMEs match verifiable receipts. |
| **`/xpublish` + [`/xultra`](../xultra/SKILL.md)** | **Adversarial Release Gatekeeper Swarm (`Maker ≠ Checker`)**: Runs Law 1 `audit_engine.py` first, shards multi-package/skill audits across specialized Audit Scouts (`Secret/Path`, `AST/Portability`, `3-Bucket & Claim Receipt`), and verifies `0` blocking issues via an independent Blind Release Gatekeeper. |
| **`/xpublish` + [`/xlearn`](../xlearn/SKILL.md)** | **Post-PR & Release Playbook Ratchet**: After shipping an upstream PR or package release, distills review-bot lessons (`GOV-*`) and benchmark receipts into `OSS_CONTRIBUTION_AND_DEEP_SCAN_PROTOCOL.md` and `COMPOUND_LEARNING_PLAYBOOK.md` via [`/xlearn`](../xlearn/SKILL.md). |
| **`/qgis /xpublish`** | **Live QGIS → Official Portal Release Handoff**: Transitions from live QGIS MCP plugin testing (`/qgis`) directly to `audit_engine.py --platform qgis` and `package_qgis.py --bump patch`. |

---

## 5. Standard Output Scorecard

```text
======================================================================
PRE-FLIGHT AUDIT SCORECARD
======================================================================
Target:    <target_dir>
Platform:  <pr|github|qgis|food4rhino|skill|generic>
Files:     <count>
Blocking:  0
Advisory:  <count>
----------------------------------------------------------------------
✅ VERDICT: PASS (100% Risk-Proof & Safe to Publish)
```
