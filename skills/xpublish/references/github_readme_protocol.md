# GitHub Repository Publishing, Visual README & Upstream PR Protocol (`v1.5`)

> **Scope**: Canonical specification for authoring open-source GitHub repositories, research/benchmark visuals, Release Notes, and Upstream Pull Requests (`PRs`) across **Agent Skills (`Archetype A`)**, **MCP Server Bridges (`Archetype B`)**, **Desktop GIS/CAD Plugins (`Archetype C`)**, and **CLI / Compute / Solver Engines (`Archetype D`)**.  
> **Governing Invariants**: **Executive Scannability (`< 5 s`)** • **Zero-Iframe `20-Block` Bar Tables (`0 ms` Render)** • **White-Mode Minimalist Mermaid (`< 30 KB` SVG, `0` Lexer Hazards)** • **Publication-Grade Vector-First Static Figures & Pre-Rendered Release Embeds (`§3.D`)** • **Viewport-Safe Table Geometry (`≤ 4` Prose Columns in `840px` PR Boxes)** • **Tri-OS Zero-Mojibake Clipboard (`CF_UNICODETEXT` `UTF-16LE` / `pbcopy` / `wl-copy`)** • **Diff-Scoped Review-Bot Convergence (`--platform pr`)**.  
> **Active Enforcement Engines**: `skills/xpublish/scripts/audit_engine.py` • `skills/xpublish/scripts/package_qgis.py` • `skills/xpublish/scripts/check_qt6.py` • `skills/xsync/scripts/audit_workspace_docs.py`

---

## 1. Document Hierarchy & Archetype-Adaptive Top-of-Repo Design

Every public repository `README.md` follows a clean 6-layer visual hierarchy, adapting its `TL;DR` and comparison metrics to the repository's actual domain (**never force ML/VRAM metrics onto a plugin, MCP bridge, or skill repo**):

1. **Header & Badges Block**:
   - Concise `# Title — 1-Line Value Proposition`
   - Actionable status badges (`Version`, `License`, `Platform / Host Compatibility`, `Test / Audit Status`)
   - 1-paragraph bold summary stating what the project does, who it is for, and its primary improvement over manual or baseline workflows.
2. **`## ⚡ TL;DR — Capabilities & Performance at a Glance`**:
   - **`3–5` Executive Highlights**: Concise bullet points summarizing the core capability and empirical impact.
   - **One-Prompt Universal Agent Install (Mandatory for Archetypes A & B — Agent Skills & MCP Bridges)**:
     Include a copy-pasteable `text` prompt block right in the `TL;DR` (and in `Universal Installation`) so any user on **any AI agent (cloud, IDE, CLI, or local LLM)** can simply paste 1 prompt into their agent to auto-detect their OS/skill directory, install, and verify the suite without manual path hunting, framed with universal **`Any AI Agent (Cloud • IDE • CLI • Local LLM)`** compatibility rather than locking to a fixed vendor list.
   - **Archetype-Adaptive Focus & Routing Guide** *(include a configuration/mode routing guide only if the project offers multiple modes, tools, or profiles)*:

| Repository Archetype | What to Highlight in `TL;DR` Bullets | What to Compare in the Horizontal Bar Table |
| :--- | :--- | :--- |
| **A. Agent Skills & Workflow Suites**<br>*(e.g., `xboost`)* | Composable slash commands, context-window noise reduction, and deterministic verification gates. | `Defect Catch Rate (%)`, `Context Token Compression (%)`, `Triage / Gate Latency (ms)` |
| **B. MCP Bridges & Host Integrations**<br>*(e.g., `mcp-bridges`)* | Connected desktop/cloud hosts, zero-UI-freeze execution safety, and bidirectional sync speed. | `Automated vs. Manual Steps`, `Round-Trip Tool Latency (ms)`, `API / Component Coverage (%)` |
| **C. Desktop GIS / CAD Plugins**<br>*(e.g., QGIS / Rhino / GH plugins)* | Core geometric/spatial transformation, cross-version compatibility (`QGIS 3/4`, `Qt5/Qt6`, `Rhino 7/8`), and 1-click workflow. | `Processing Speed vs. Manual CAD/GIS`, `Feature / Layer Preservation (%)`, `Zero-Dependency Portability` |
| **D. CLI Tools, Solvers & AI Engines**<br>*(e.g., data pipelines, solvers, OCR)* | Speedup vs. baseline, accuracy/fidelity delta, and *when multiple modes/models exist*, which flag to pick for speed vs. accuracy vs. memory. | `End-to-End Speedup (×)`, `Benchmark Accuracy (%)`, `Memory / Resource Footprint` |

3. **`## 1. Architecture & Usage Workflow`**:
   - Maximum **`1–2` White-Mode Mermaid `flowchart` diagrams** (`< 30 KB` SVG each) with minimal text:
     - **Diagram A (System Architecture & Ecosystem)**: How the tool connects inputs, core modules, and host platforms/plugins (marking active modules as `(LIVE)` and planned extensions with a small `(coming soon)` subtitle).
     - **Diagram B (Usage Workflow)**: `1. Trigger / Entry Point` → `2. Core Processing / Selection` → `3. Output / Canvas State`.
   - When the repository or release includes static/publication figures (`docs/figures/*.svg|png`, paper plates, or benchmark charts), follow `§3.D` rather than mixing flowcharts with SaaS metric cards.
4. **`## 2. Quick Start & Installation`**:
   - Copy-pasteable installation and minimal working usage examples (CLI command, slash command, MCP config JSON, or plugin UI steps).
5. **`## 3. Benchmarks, Verification & Deep Reference`**:
   - Clean GFM summary tables on the surface, paired with collapsible `<details>` blocks for deep specifications (e.g., full MCP tool schemas, plugin parameter matrices, or **LaTeX `booktabs`** tables for academic/research repos) so the main page never bloats with text.
6. **`## 4. Citation, License & Contributing`**:
   - Citation block (if applicable) and license link.

---

## 2. Instant-Render Native Markdown Horizontal Bar Charts (`0 ms` Load)

### 2.1 Structural Failure Modes of Mermaid `xychart-beta` (Banned on GitHub)
Mermaid's experimental `xychart-beta` is prohibited across all repository and PR Markdown files due to three deterministic rendering defects:
1. **Coordinate Transpose Defect**: Combining `horizontal` with `bar [...]` and `line [...]` plots `bar` series in `(y, x)` coordinates while evaluating `line` series in `(x, y)` coordinates, projecting lines vertically off the canvas.
2. **Unstripped Quote Literals & Missing Legend DOM**: Axis labels render with literal `"..."` characters and emit `0` legend nodes (`Bar 1`, `Line 1`).
3. **Sandboxed Iframe Payload Penalty (`~2 MB` JS / Block)**: Each Mermaid block spawns an isolated `viewscreen.githubusercontent.com` iframe. Placing `> 2` blocks on a single page triggers multi-second hydration stalls and `Unable to render rich display` timeouts.

### 2.2 Canonical `20-Block` Unicode Bar Formulation (`█` + `░`)
All inline scalar comparisons use a **20-character Native Markdown Horizontal Bar Table** (`0 ms` DOM paint, `0` iframe overhead):
- **Glyph Set**: Filled block `█` (`U+2588`) and light shade track `░` (`U+2591`), satisfying `N_filled + N_empty == 20`.
- **Normalization Rule**:
  - **Higher-is-Better Objectives** (Throughput, Speedup, Recall, Accuracy, Compression): `N_filled = round(20 · x / x_max)`.
  - **Lower-is-Better Objectives** (Latency, Memory, Error, Overhead): Either plot the **Reduction Ratio** (`-97.5% Overhead`) or plot `N_filled = max(1, round(20 · x / x_baseline))` with an explicit `(Lower = Better)` column annotation.

#### Universal Reusable Template
```markdown
### Horizontal Bar Comparison

| Evaluation Dimension | Workflow / Configuration | Visual Comparison Bar | Measured Result & Delta vs. Baseline |
| :--- | :--- | :--- | :--- |
| **1. Workflow Speed / Throughput ↑** | **Automated Engine / Plugin**<br>Manual / Legacy Baseline | `████████████████████` **`15.0× Faster`**<br>`█░░░░░░░░░░░░░░░░░░░` `1.0×` | **`1.2 s`** (`-93%` execution time)<br>`18.0 s` (Baseline) |
| **2. Quality / Verification Recall ↑** | **Full Pipeline (With Guards)**<br>Standard Mode<br>Unchecked Baseline | `████████████████████` **`100.0%`**<br>`████████████████░░░░` `80.0%`<br>`████░░░░░░░░░░░░░░░░` `20.0%` | **`0` Regressions / Errors**<br>Standard Coverage<br>Baseline Reference |
| **3. Context / Overhead Reduction ↓**<br>*(Lower = Better)* | **Bounded / Optimized Mode**<br>Unbounded Baseline | `█░░░░░░░░░░░░░░░░░░░` **`2.5% Overhead`**<br>`████████████████████` `100.0% Overhead` | **`-97.5%` Bloat Removed**<br>Full Unfiltered Load |
```

---

## 3. White-Mode Minimalist Mermaid Diagrams & The 4 Lexer Guardrails

### A. Enforcing Crisp White Mode Across Both Light & Dark GitHub Themes
When a viewer opens GitHub in Dark Mode, default Mermaid diagrams often render with low-contrast dark-gray boxes and invisible arrows between subgraphs. Furthermore, using `theme: 'base'` bloats the SVG payload from `~26 KB` to `> 113 KB`. To guarantee **100% crisp White-Mode diagrams (`< 30 KB` SVG)** on every device and theme:
1. Prepend the **`theme: 'neutral'` Lightweight Init Directive**:
   ```text
   %%{init: {'theme': 'neutral'}}%%
   ```
2. Wrap the entire diagram inside an outer **`subgraph Canvas [" "]`** styled with a pure `#ffffff` fill and explicit `classDef default`:
   ```text
   classDef default fill:#ffffff,stroke:#475569,color:#0f172a,stroke-width:1px
   style Canvas fill:#ffffff,stroke:#cbd5e1,stroke-width:1.5px,color:#0f172a
   style SubGroup fill:#f8fafc,stroke:#94a3b8,color:#0f172a
   ```
   This creates a self-contained **White Card Canvas (`~23-29 KB` SVG)** so arrows connecting inner subgraphs never sit on GitHub Dark Mode's `#0d1117` background.
3. Style roadmap / future-extension nodes (`coming soon`) with dashed slate borders:
   ```text
   style FutureNode fill:#ffffff,stroke:#94a3b8,stroke-dasharray: 5 5,color:#64748b
   ```

### B. The 4 Hard GitHub Mermaid Lexer Guardrails (Mandatory)
To prevent GitHub's `Unable to render rich display` error and keep SVG payloads under `30 KB`:

| # | Forbidden Pattern inside ` ```mermaid ` | Why It Breaks GitHub's Renderer | Mandatory Clean Replacement |
| :---: | :--- | :--- | :--- |
| **1** | **Double-hyphens `--` inside node/edge labels**<br>*(e.g., `Node["--mode auto"]` or `Node["--platform skill"]`)* | Mermaid's lexer parses `--` as an edge token even inside quotes on several GitHub `viewscreen` versions, throwing a fatal parse error. | Use colon or key-value syntax: `Node["mode: auto"]` or `Node["platform: skill"]`. |
| **2** | **HTML tags `<br>`, `<br/>`, `<b>`, `<i>`**<br>*(e.g., `Node["Line 1<br/>Line 2"]`)* | Causes XHTML vs. HTML5 sanitizer mismatches and vertical label clipping inside SVG `<foreignObject>` boxes. | Keep node labels concise on a single line (`≤ 45` chars): `Node["Primary Name (Concise Subtitle)"]`. |
| **3** | **Chained ampersand `&` edges**<br>*(e.g., `A & B --> C & D`)* | Fails when combined with styled subgraphs or edge labels in GitHub's bundled Mermaid version. | Declare one explicit `1-to-1` edge per line (`A --> C`, `B --> C`). |
| **4** | **Multi-codepoint emojis & regional flags**<br>*(e.g., `🇹🇭`, `🇬🇧`, `🏎️`, `⚡`)* | Surrogate-pair and ZWJ emojis inflate Mermaid SVG font-metric calculations (`>110 KB` SVG) and break text centering. | Use clean ASCII text badges inside diagrams: `(LIVE)`, `(Default)`, `(coming soon)`. |

### C. Canonical White-Mode Diagram Templates (Adapt to Repo Archetype)

#### Template 1: Modular System / Bridge / Plugin Architecture (`flowchart LR`)
```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart LR
    subgraph Canvas [" "]
        In["User / Host Trigger"] --> Core{"Core Engine / Router"}

        subgraph Modules ["Supported Modules / Integrations"]
            M1["Integration A (LIVE)"]
            M2["Integration B (LIVE)"]
            M3["Integration C (coming soon)"]
            M4["Integration D (coming soon)"]
        end

        Core --> M1
        Core --> M2
        Core -.-> M3
        Core -.-> M4

        M1 --> Verify["Validation & Output Formatter"]
        M2 --> Verify
        Verify --> Out["Verified Deliverable / Host State"]
    end
    classDef default fill:#ffffff,stroke:#475569,color:#0f172a,stroke-width:1px
    style Canvas fill:#ffffff,stroke:#cbd5e1,stroke-width:1.5px,color:#0f172a
    style Modules fill:#f8fafc,stroke:#94a3b8,color:#0f172a
    style M3 fill:#ffffff,stroke:#94a3b8,stroke-dasharray: 5 5,color:#64748b
    style M4 fill:#ffffff,stroke:#94a3b8,stroke-dasharray: 5 5,color:#64748b
```

#### Template 2: 3-Step Usage Workflow (`flowchart LR`)
```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart LR
    subgraph Canvas [" "]
        subgraph Step1 ["1. Entry Point"]
            UI["Host UI / Plugin Action"]
            CLI["CLI / Agent Command"]
        end

        subgraph Step2 ["2. Execution & Guards"]
            Run["Core Processor / Bridge"]
            Gate["Automated Quality / Safety Gate"]
        end

        subgraph Step3 ["3. Outputs"]
            Out1["Updated Canvas / Layer / Repo"]
            Out2["Structured Report / Manifest"]
        end

        UI --> Run
        CLI --> Run
        Run --> Gate
        Gate --> Out1
        Gate --> Out2
    end
    classDef default fill:#ffffff,stroke:#475569,color:#0f172a,stroke-width:1px
    style Canvas fill:#ffffff,stroke:#cbd5e1,stroke-width:1.5px,color:#0f172a
    style Step1 fill:#f8fafc,stroke:#94a3b8,color:#0f172a
    style Step2 fill:#f8fafc,stroke:#94a3b8,color:#0f172a
    style Step3 fill:#f8fafc,stroke:#94a3b8,color:#0f172a
```

### D. Publication-Grade Vector-First Static Figures & Release Diagrams (`Anti-"AI Dashboard"` Standard)

> **Context-Conditioned Scope**: Governs static conceptual architecture plates, quantitative benchmark charts, academic paper/writeup figures (`docs/figures/`), and visual embeds inside GitHub Release Notes. *(Live host UI screenshots, desktop CAD/GIS viewport captures, and interactive web app previews remain exempt from 2-ink constraints.)*

| Trap ID & Anti-Pattern | Defect Signature | Visual / Rendering Failure Mode | Mandatory Publication Invariant & Fix |
| :--- | :--- | :--- | :--- |
| **`FIG-01` — Hybrid Flowchart + KPI Card Poster** | Bolting SaaS-style metric tiles, summary cards, or prize/track pill badges underneath an architecture diagram | Conflates system topology (`inputs → pipeline → outputs`) with promotional scorecards; signals auto-generated infographic styling to academic/technical reviewers | Separate topology from telemetry: keep `Figure 1` strictly to structural data/control flow; report scalar metrics in XY plots, `20-block` bars (`§2`), or `booktabs` tables (`§5`). |
| **`FIG-02` — Multi-Hue Neon Palette, Shadows & Blanket Monospace** | `> 2` saturated accent hues, drop shadows, glossy gradients, `rounded-2xl` pill badges, or `JetBrains Mono` / `Consolas` on all prose labels | Reduces luminance contrast on print/PDF, creates visual clutter, and obscures typographic hierarchy between prose headers and code tokens | Enforce a pure `#ffffff` canvas, editorial Serif or Neo-Grotesque titles + sans-serif annotations (monospace strictly for code/CLI/path identifiers), hairline `0.5–0.75pt` (`1px`) strokes (`#1f2937` / `#334155`), `0` shadows/pills, and **`≤ 2` muted accent inks** (e.g., Oxford Navy `#1e3a5f` + Crimson/Rust `#b91c1c`). |
| **`FIG-03` — 4-Spine Boxed Plots & Unchecked Label Collisions** | Default 4-sided plot frames, internal legend boxes overlapping trajectories, or uninspected raster exports | Top/right spines add non-data ink (Tufte); dense error bars or pareto frontiers collide with text annotations at target column width | Set `spines['top'].set_visible(False)` and `spines['right'].set_visible(False)`, place direct series/endpoint labels outside dense clusters, and visually inspect the rasterized output at `100%` scale to verify `0` text overlaps. |
| **`FIG-04` — Raw Fenced ` ```mermaid ` in GitHub Release Notes** | Pasting raw ` ```mermaid ` blocks into a GitHub Release description (`releases/tag/v*`) | GitHub Release views, email notification digests, and Atom/RSS feeds frequently fail to hydrate the `viewscreen` Mermaid JS runtime, exposing raw source text | Author figures vector-first (`SVG`/`PDF` via `Matplotlib` or `/diagram-design` `§4`, with optional `/illustrator` finish), export `300 DPI` / `2×` PNG rasters when required, and embed pre-rendered raw `PNG`/`SVG` URLs in Release Notes. |

---

## 4. Viewport-Safe Table Column Geometry (`README.md` vs. Pull Request Box)

GitHub constrains Markdown tables to fixed-width DOM containers (`~890px` in repository `README.md` views and **`~820–840px` inside Pull Request / Issue comment boxes**). Exceeding column or token-width bounds forces horizontal scrollbars or truncates rightmost verification columns.

| Table Context & Type | Max Columns | Column Merging & Token Width Rules |
| :--- | :---: | :--- |
| **1. Explanatory / Bug-Fix / Feature Tables**<br>*(Inside PR Descriptions or `README.md`)* | **`≤ 4` Columns** | • Merge index `#` and `Component / Target` into a single first column: **`# & Target`** (e.g., `**1. func_name** (module.py)`).<br>• Use the 4-column layout: `# & Target` \| `Problem / Baseline` \| `Solution / Mechanism` \| `Impact / Verification`.<br>• Keep individual inline code tokens `≤ 28` characters so the browser can wrap text naturally between words. |
| **2. Numeric Comparison Matrices**<br>*(Compact numbers in columns `3..N`)* | **`≤ 6` Columns** | • Allowed up to `6` columns **only** when columns `3..6` hold compact numeric values (`10.1 ms`, `100.0%`, `25 / 25`).<br>• Keep column headers `≤ 22` characters and use `-` (ASCII hyphen) for empty cells. |

---

## 5. Progressive Disclosure (`<details>` for Deep Specs & Academic `booktabs`)

To preserve top-level scannability (`< 5 s`) while retaining 100% technical and mathematical completeness:
1. **Surface Summary Layer**: Restrict visible tables to `≤ 8` rows with explicit physical/computational units (`ms`, `s`, `%`, `LOC`, `MiB`) and **bolded Pareto-optimal / best results**.
2. **Collapsible Reference Layer (`<details>`)**: Encapsulate exhaustive specification tables inside collapsible `<details>` blocks immediately below the surface table:
   - *For Agent Skills, MCP Bridges & Plugins*: Full JSON-RPC tool schemas, CLI flag matrices, or `Qt5`/`Qt6` enum migration tables.
   - *For Research, Solver & Benchmark Repos*: Complete **LaTeX (`booktabs`)** source tables (`\toprule`, `\midrule`, `\bottomrule`) for direct inclusion in academic manuscripts.

---

## 6. Upstream Pull Request (`PR`), Dual-Credit & Review-Bot Convergence Protocol

### A. Quantitative PR Title Formulation (`55–78` Characters)
- **Viewport Truncation Constraint**: GitHub truncates PR titles exceeding `~80` characters (`...`) across PR index views, email headers, and `git log --oneline`, whereas generic titles (`fix bugs & update code`) omit empirical signal.
- **Canonical Formula (`55–78` chars)**:
  ```text
  <type>(<scope>): <quantified improvement / capability> & <headline feature>
  ```
- **Examples Across Domains**:
  - *Plugin / CAD / GIS*: `feat(qgis): add Qt6 compatibility & 12x faster batch geometry transform` (`71` chars)
  - *MCP / Agent Tooling*: `feat(mcp): add non-blocking socket bridge & 14 deterministic verification gates` (`79` chars)
  - *Compute / AI Pipeline*: `feat(ocr): 1.3x-15x faster pipeline (-35.9% token bloat) & offline local VLM` (`76` chars)

### B. Dual-Credit Fork Strategy (Organization Fork + Personal Author Commit)
To maximize credibility for both the research lab/organization and the individual engineer's career portfolio (CV / graduate applications):
1. **Fork under the Organization**: Create the upstream fork under the lab organization (`https://github.com/<org>/<upstream-repo>`).
2. **Commit with Personal Git Identity**: Author the commits using the engineer's personal GitHub email (`git config user.email "<personal-email>"`).
3. **Resulting Public Header on Upstream Repo**:
   `<personal-username> wants to merge N commits into <upstream>:master from <org>:<branch-name>`
   This permanently records **both** the personal account (as commit author & PR opener) and the organization fork on the upstream repository.

### C. Zero-Mojibake Clipboard & Browser Pre-Fill Automation (Windows / macOS / Linux Tri-OS)
> [!CAUTION]
> **Never Use PowerShell 5.1 `Get-Content | Set-Clipboard` or `clip.exe` for Unicode / Multilingual Markdown**:
> In Windows PowerShell 5.1, pipeline strings default to legacy ANSI codepages (`cp1252` / `cp874`), which silently corrupts non-ASCII characters—turning Unicode arrows/bars (`→`, `█`), Thai tone marks (`่ ้ ๊ ๋`), decomposed vowels (`นํ้า`), bullets (`•`), and em-dashes (`—`) into `` replacement diamonds when pasted into GitHub's editor.

Always use these two rules when automating PR or README pasting:
1. **ASCII Punctuation Hygiene in PR Bodies**: Use standard ASCII hyphens `-` instead of `•` or `—` in section headers and empty table cells.
2. **Tri-OS Zero-Mojibake Clipboard Loader (`CF_UNICODETEXT` / `pbcopy` / `wl-copy`) + Pre-Filled Browser Launch**:
   Since isolated agent browser profiles are not logged into the user's personal GitHub session, pre-fill the PR Title via URL query parameters (`?expand=1&title=...`) in the user's default logged-in browser and load the PR Description directly into the system clipboard with zero encoding loss across Windows (`UTF-16LE` `CF_UNICODETEXT`), macOS (`UTF-8` `pbcopy`), and Linux (`wl-copy` / `xclip`):

```python
import os, sys, ctypes, shutil, urllib.parse, subprocess
sys.dont_write_bytecode = True

def copy_utf16_clipboard(text: str) -> None:
    """Copy Unicode text (bars, symbols, multilingual text) to clipboard with zero mojibake across Windows/macOS/Linux."""
    if sys.platform == "win32":
        CF_UNICODETEXT, GMEM_MOVEABLE = 13, 0x0002
        user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
        kernel32.GlobalAlloc.argtypes = [ctypes.c_uint, ctypes.c_size_t]
        kernel32.GlobalAlloc.restype = ctypes.c_void_p
        kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
        kernel32.GlobalLock.restype = ctypes.c_void_p
        kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
        user32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]

        encoded = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-16le") + b"\x00\x00"
        user32.OpenClipboard(0)
        user32.EmptyClipboard()
        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(encoded))
        ptr = kernel32.GlobalLock(h_mem)
        ctypes.memmove(ptr, encoded, len(encoded))
        kernel32.GlobalUnlock(h_mem)
        user32.SetClipboardData(CF_UNICODETEXT, h_mem)
        user32.CloseClipboard()
    elif sys.platform == "darwin":
        subprocess.run(
            ["pbcopy"],
            input=text.encode("utf-8"),
            env={**os.environ, "LANG": "en_US.UTF-8"},
            check=True,
        )
    else:
        cmd = ["wl-copy"] if shutil.which("wl-copy") else ["xclip", "-selection", "clipboard"]
        subprocess.run(cmd, input=text.encode("utf-8"), check=True)

def launch_prefilled_github_pr(upstream_repo: str, org_fork: str, branch: str, title: str, body: str) -> None:
    copy_utf16_clipboard(body)
    q_title = urllib.parse.quote(title)
    url = f"https://github.com/{upstream_repo}/compare/master...{org_fork}:{branch}?expand=1&title={q_title}"
    if sys.platform == "win32":
        os.startfile(url)
    elif sys.platform == "darwin":
        subprocess.run(["open", url], check=True)
    else:
        subprocess.run(["xdg-open", url], check=True)
```

### D. Upstream PR Etiquette, Closing-Keyword Parity & Review-Bot Convergence (`--platform pr`)

When contributing to external upstream repositories, enforce these four rules before and after opening a PR:

1. **Issue-Claim Etiquette, Live `HEAD` / Feature-Branch Repro & Maintainer Reply Package**:
   - Before opening an upstream PR or posting a public comment, inspect `CONTRIBUTING.md`, `.github/PULL_REQUEST_TEMPLATE*`, `.github/workflows/*`, `.releaserc*`, `AI_POLICY.md`, issue assignees, and linked open PRs via GitHub API/CLI (`Law 1`).
   - **Live `HEAD`, Active Feature-Branch & External Test-Data Pre-Gate**: Before writing code for an older open issue, verify on a fresh clone of the repository's actual default/integration branch (`gh api repos/<owner>/<repo> --jq .default_branch` or `CONTRIBUTING.md` target branch such as `develop` vs. `main`) **and** any active `feature/*` branch referenced in the issue thread (`git log --all -S "<symbol>"`) that the issue has **not** already been resolved. When a test references data files absent from the git tree, inspect `Makefile`, `conftest.py`, and `.github/workflows/*` for external test-data archives pinned by commit hash. Check whether the repo enforces **DCO sign-off (`git commit -s` / `Signed-off-by:`)**, **Conventional Commits** (`fix:` / `feat:` / `perf:`), or an **entry in `docs/changelog.rst` / `CHANGELOG.md`**.
   - **Direct-PR Repos**: If the issue is unassigned, reproducible at `HEAD`, has no competing open PR, and `CONTRIBUTING.md` does not mandate prior approval, implement the fix + regression test on a clean feature branch and open the PR directly.
   - **Discussion-First Repos & High-Signal Maintainer Reply Package (`I`/`my` Voice + Complete Scripts from Draft 1)**: If `CONTRIBUTING.md` or maintainer norms require discussing before opening a PR (or when replying to maintainer feedback on a benchmark/bug issue), prepare and verify the local branch first. Draft comments using first-person singular (**`I` / `my`**, never `"we"` / `"our"`) with **short, scannable top-level prose** (`Summary Table` → `Key Takeaway` → `Summary of Options for the PR` → `Unit Test`) followed immediately in **Draft 1** by collapsible `<details>` blocks containing **100% of proposed code diffs (`git diff`) and the complete self-contained benchmark/verification script reproducing every reported metric** (zero gatekeeping or making the user/maintainer ask for missing scripts later).
   - **Human-Consent Gate for Public Posts**: Always obtain explicit user approval before posting public comments or opening PRs under the user's GitHub identity.
2. **Closing Keyword Parity (`Fixes #N` vs. `Part of #N` / `Addresses #N`)**:
   - Write auto-closing keywords (`Fixes #N`, `Closes #N`, `Resolves #N`) **only** when the PR satisfies `100%` of the issue's stated sub-requirements, acceptance checkboxes, and target platforms.
   - When a PR intentionally addresses a subset of a multi-part issue (or fixes one platform/module while leaving sibling items open), use non-closing references (`Part of #N` or `Addresses #N`) and explicitly state which items are covered vs. remaining so neither maintainers nor review bots flag a scope mismatch.
3. **Diff-Scoped Hygiene (`audit_engine.py --platform pr`)**:
   - Always run `audit_engine.py` (`skills/xpublish/scripts/audit_engine.py`) with `--platform pr` prior to `git push`.
   - Format and lint (`ruff`, `flake8`, `black`, `prettier`) **strictly on touched lines/files** so the PR diff never includes unrelated style churn or fails on pre-existing upstream lint debt.
4. **Automated Review-Bot & Outside-Diff Convergence (`@coderabbitai`, etc.)**:
   - After opening or pushing to a PR on repositories with automated review bots (`@coderabbitai[bot]`, `sourcery-ai`, `sonarcloud`), fetch **both**:
     1. Inline diff comments (`/repos/<owner>/<repo>/pulls/<id>/comments`)
     2. Top-level review bodies (`/repos/<owner>/<repo>/pulls/<id>/reviews`), specifically expanding `<details>` sections for **`Outside diff range comments`** and **`Nitpick comments`** (where assertive bots place findings about callers, sibling state-reset methods, or test assertions outside the modified diff hunk).
   - **In-Scope Relevance Filter**: Implement fixes for bot comments that affect correctness, state lifecycle, security, or test coverage of the touched feature/function; politely decline or defer out-of-scope pre-existing refactoring suggestions to keep the PR atomic.

---

## 7. Cross-Account Profile & Mirror Synchronization Hygiene

When propagating a repository's version badge or empirical metrics across an organization profile (`<org>/.github/profile/README.md`) and personal profile (`<user>/<user>/README.md`):
1. **Rebase Before Push**: Execute `git pull --rebase origin main` prior to pushing profile READMEs to incorporate concurrent remote commits cleanly.
2. **Post-Merge Index Deduplication**: When resolving merge conflicts on numbered portfolio tables, verify `1:1` primary-key uniqueness (`0` duplicate index rows such as two `01 //` entries) prior to pushing.

---

## 8. Pre-Publish Verification Checklist (Automated Gate)

Before pushing any `README.md`, benchmark report, Release body, or Upstream PR to GitHub, run these 9 deterministic checks:

- [ ] **Iframe Budget (`≤ 2` Mermaid Blocks per Page)**: Does `README.md` contain at most `2` `flowchart` blocks and **`0` `xychart-beta` blocks**?
- [ ] **White-Mode Canvas Wrapper**: Does every Mermaid block include `%%{init: {'theme': 'neutral'}}%%` and an outer `subgraph Canvas [" "]` with `style Canvas fill:#ffffff,...`?
- [ ] **4-Guardrail Lexer Scan (`0` Hazards)**:
  - `0` occurrences of `<br>` or `<br/>` inside ` ```mermaid ` blocks
  - `0` occurrences of `--` inside quoted Mermaid labels `["..."]`
  - `0` occurrences of chained `&` edges (`A & B --> C`)
  - `0` multi-byte emojis inside ` ```mermaid ` blocks
- [ ] **Live `mermaid.ink` Compiler Check**: Does every Mermaid block compile via `https://mermaid.ink/svg/pako:...` with `HTTP 200`, `role="flowchart-v2"`, `SyntaxError=False`, and SVG size `< 30 KB`?
- [ ] **Publication-Grade Static Figures (`§3.D`)**: Are static diagrams cleanly separated from KPI metric cards/pill badges, restricted to `#ffffff` + `≤ 2` muted accent inks (`0` shadows), with hidden top/right spines on plots and `0` overlapping labels at `100%` raster scale?
- [ ] **Release Notes Diagram Embed**: Do GitHub Release Notes use pre-rendered raw `PNG`/`SVG` image links (`§3.D.4`) instead of fenced ` ```mermaid ` blocks?
- [ ] **Viewport-Safe Table Width (`≤ 4` Prose Columns)**: Do all explanatory/fix tables have `≤ 4` columns (`# & Target` merged) so the rightmost column never clips inside an `840px` GitHub PR box?
- [ ] **Zero-Mojibake Encoding Check**: Were all clipboard/file writes executed via UTF-8 (`encoding="utf-8"`) or Win32 `CF_UNICODETEXT` (`UTF-16LE`) with `0` replacement characters (`\ufffd`)?
- [ ] **Link, Diff & Mirror Integrity**: Do `audit_workspace_docs.py --allow-latex` and `audit_engine.py --platform <github|pr>` pass with `0` blocking issues and `0` advisory warnings?
