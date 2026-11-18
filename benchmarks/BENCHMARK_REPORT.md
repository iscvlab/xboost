# XBoost (`v3.6.0`) — Empirical Benchmark & Token Economics Report

> **Reproducible Verification Harness**: Generated deterministically by [`benchmarks/run_xboost_benchmark.py`](./run_xboost_benchmark.py)  
> **Corpus Scope**: `117` Installed Agent Skills • `285` Repository Markdown Specs • `612` Obsidian Second Brain Nodes • `484` Real IDE Sessions (`1136` Prompt Turns) • `24` Upstream Open-Source PRs + `1` Hold (`10 MERGED`)  
> **Statistical Rigor**: Timing benchmarks execute `3` warm-up passes followed by `N = 30` timed iterations (`time.perf_counter_ns()`), reporting **Median (`P50`)**, **Mean ± StdDev**, **IQR (`P25–P75`)**, and **`P95`**.

---

## ⚡ TL;DR - Empirical Scorecard at a Glance (`v3.6.0`)

| Evaluation Dimension | Workflow / Cohort Configuration | Visual Comparison Bar | Measured Result & Delta vs. Baseline |
| :--- | :--- | :--- | :--- |
| **1. Red-Team Defect Catch Rate ↑**<br>*(25 Seeded Defects across 5 Pillars)* | **Level 3: Full 5-Stage + 10 CLI Gates**<br>Level 2: `/xbrief` + `/xdeep-research` + `/xboost`<br>Level 1: `/xboost` Standalone (2 Gates)<br>Level 0: Prompt-Only Baseline (0 Gates) | `████████████████████` **`100.0% (25/25)`**<br>`████████████████░░░░` `80.0% (20/25)`<br>`████████░░░░░░░░░░░░` `40.0% (10/25)`<br>`░░░░░░░░░░░░░░░░░░░░` `0.0% (0.0%)` | **`0` False Positives in Median `8.14 ms`** ✨<br>`4` Active CLI Verification Gates<br>`2` Active CLI Verification Gates<br>No Deterministic Pre-LLM Enforcement |
| **2. Context Noise Compression ↑**<br>*(897 Repo + Vault Files, `1.77M` tok)* | **`/xbrief` (`Cap 8`) Repo-Only**<br>**`/xbrief` (`Cap 8`) + `/xobsidian` (`2-Hop`)**<br>Unbounded Repo + Vault Crawl | `████████████████████` **`97.32% Removed (37.3×)`**<br>`████████████████████` **`97.06% Removed (34.0×)`**<br>`░░░░░░░░░░░░░░░░░░░░` `0.0% Removed (1.0×)` | **`47,436` tok in Median `1.19 ms`** ✨<br>**`52,053` tok (`12` files) in `1.4 ms`** ✨<br>`1,770,934` tok (`897` files) in `53.69 ms` |
| **3. System 1 Section Triage ↑**<br>*(28 Specs / 1017 Chunks, `154.3k` tok)* | **XBoost `/xlaya` Top-5 Shortlist**<br>Unfiltered Full-Corpus Pass-B Read | `████████████████████` **`99.35% Saved (154.8×)`**<br>`░░░░░░░░░░░░░░░░░░░░` `0.0% Saved (1.0×)` | **`997` tok in Median `147.43 ms`** (`6.9k` chunks/s) ✨<br>`154,349` tok (Full 28-File Read) |
| **4. Dual-Trigger Budget Guard ↑**<br>*(`Use when` + `Do NOT use` across `N=117`)* | **XBoost `v3.6.0` Suite (`N = 15`)**<br>All Installed Host Skills (`N = 117`)<br>Official Cloud/Vendor Skills (`N = 31`) | `████████████████████` **`100.0% (15/15)`**<br>`██████████████████░░` `90.6%`<br>`█████████████████░░░` `87.1%` | **`370.93 ± 20.15` chars (`0%` Truncation)** ✨<br>`324.41 ± 51.29` chars (`99.1%` `≤500` pass)<br>`331.03 ± 63.51` chars (`96.8%` `≤500` pass) |
| **5. Verification Depth / Turn ↑**<br>*(`N = 1136` Real IDE Prompt Turns)* | **Chained Multi-Skill `/x*` Turn (`N=289`)**<br>Single `/x*` Skill Turn (`N = 114`)<br>Standard Turn Without `/x*` (`N = 733`) | `████████████████████` **`92.9 Steps (3.44×)`**<br>`███░░░░░░░░░░░░░░░░░` `15.2 Steps`<br>`█████░░░░░░░░░░░░░░░` `27.0 Steps (1.0×)` | **`5.02M` tok/turn (`97.8k` new in, `25.4k` out)** ✨<br>`0.95M` tok/turn (`11.0k` new in, `3.3k` out)<br>`1.56M` tok/turn (`14.8k` new in, `6.4k` out) |
| **6. Compound Learning OSS Speedups ↑**<br>*(`24` PRs + `1` Hold, `Batch 0 + A + B + C`)* | **`/xlearn` 4-Tier Sharded Playbooks (`PAT-*/OPT-*` + `GOV-*` + `FALS-*`)**<br>Unvectorized Upstream Baseline (`HEAD`) | `████████████████████` **`4.0× – 1,735.6× Faster`**<br>`░░░░░░░░░░░░░░░░░░░░` `1.0× Baseline` | **`100%` `assert_allclose` Parity (`10 MERGED`, `9 OPEN PRs`)** ✨<br>Python `np.vectorize`, `O(N²)` scans & OGR disk-seek loops |

---

## Executive Findings: High Intelligence via High Compute

1. **System-Prompt Budget Discipline (`100%` Compliance & Dual-Trigger Guards)**: Across all `15` XBoost `/x*` skills, YAML discovery descriptions average **`370.93 ± 20.15 chars`** (Median `374.0` chars, **`100.0%` within the `≤ 500` char `audit_engine.py` budget gate**) with **`100.0%` dual positive + negative (`Use when` / `Do NOT use for`) routing guards**, compared to `87.1%` dual-trigger coverage across `31` official cloud/enterprise skills.
2. **Context Noise Compression (`-97.06%` Scan Reduction)**: When briefing across multi-project repositories and the `612`-node Obsidian Second Brain (`1,770,934` tokens total), `/xbrief` (`Cap 8` Two-Pass) + `/xobsidian` (`2-Hop = 4` vault files) loads only **`52,053` tokens** (**`97.06%` noise reduction** / **`34.0×` compression**) in a median disk read time of **`1.4 ms`** (vs `53.69 ms` unbounded).
3. **System 1 `/xlaya` Triage (`147.43 ms` Median)**: Chunking and ranking `1017` fence-safe (`≤ 1,200`-char) heading sections across `28` specs completes in **`147.43 ms`** (`Mean 147.93 ± 4.77 ms`, `6,898.2 chunks/sec`), cutting Pass-B reading tokens by **`99.35%`**.
4. **Deterministic Red-Team Defect Catch Rate (`100.0%` vs `0.0%`)**: Across `25` seeded security, Qt6/QGIS 4, research citation, doc-sync, and skill-packaging defects, the 10 CLI gates (`22,237` LOC) achieve **`25 / 25` (`100.0%` recall)** and **`100.0%` precision** (`0` false positives) in **`8.14 ms`**.
5. **Transparent Token Economics (Why XBoost Recommends `5×`–`20×` Subscriptions)**: While XBoost slashes *garbage file noise* by `97.06%`, it deliberately invests that freed context capacity into **deep multi-gate verification**. Across `1136` real prompt turns, a chained multi-skill XBoost turn executes **`92.89 steps`** (`3.44×` deeper than standard `27.0`-step turns), consuming **`97,839` uncached input tokens (`6.61×`)**, **`25,432` output tokens (`3.97×`)**, and **`4,887,567` KV-cache read tokens** per turn (`~42.82M` total tokens across a full `747`-step marathon session).
6. **4-Tier Sharded Compound Learning Playbooks (`4.0×` – `1,735.6×` Real-World Upstream Speedups)**: By distilling verified bug and bottleneck signatures via [`/xlearn`](../skills/xlearn/SKILL.md) into [`docs/COMPOUND_LEARNING_PLAYBOOK.md`](../docs/COMPOUND_LEARNING_PLAYBOOK.md) (`L1` Router Hub → `docs/playbooks/PLAYBOOK_1A..1D_*.md` `L2` Shards: `24 PAT-*/OPT-*` across `21` families incl. `OPT-MOO-01`, `7 GOV-*`, `13 FALS-01..13` + Tier 2/3 domain playbooks), XBoost achieved **`4.0×` to `1,735.6×` measured wall-clock speedups** with **`100%` numerical equivalence** across **24 upstream open-source PRs + 1 Hold** (`10 MERGED`, `9 OPEN PRs`, `1 Hold`, `5 Closed/Staged`).

---

## Experiment 1: Skill Discovery & Context Budget Audit (`N = 117` Installed Skills)

| Skill Cohort | Count | YAML Desc Chars (`Mean ± SD` / `Median`) | `≤ 500` Char Gate Pass | Dual Trigger Guard (`Use when` + `Do NOT use`) | Full `SKILL.md` Tokens (`Mean ± SD` / `Median`) | Bundled CLI Scripts (`LOC`) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **XBoost `v3.6.0` Suite (`/x*` Skills)** | `15` | **`370.93 ± 20.15`** (`374.0`) | **`100.0%`** | **`100.0%`** | `4,771 ± 2,109` (`3,867`) | **`10` (`22,237` LOC)** |
| **Official Cloud & Enterprise Vendor Skills** | `31` | `331.03 ± 63.51` (`324.0`) | `96.8%` | `87.1%` | `2,523 ± 1,689` (`2,468`) | `5` (`2,880` LOC) |
| **All Installed Host Skills Pool** | `117` | `324.41 ± 51.29` (`319.0`) | `99.1%` | `90.6%` | `2,217 ± 1,960` (`1,569`) | `60` (`41,059` LOC) |

---

## Experiment 2: Context Window Compression & 2-Hop Vault Isolation (`3` Warm-Ups + `30` Trials)

| Briefing Regime | Files Read | Lines Read | Context Tokens Loaded | Noise Reduction (`%` / Factor) | Disk Read Latency (`Median` / `Mean ± SD` / `P95`) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **1. Unbounded Repo + Vault Crawl** | `897` | `75,970` | `1,770,934` tok | Baseline (`1.0×`) | `53.69 ms` (`55.74 ± 5.53 ms` / `P95: 68.29 ms`) |
| **2. `/xbrief` Repo-Only (`Cap 8` Two-Pass)** | **`8`** | **`1,110`** | **`47,436` tok** | **`-97.32%` (`37.3×`)** | **`1.19 ms`** (`1.32 ± 0.32 ms` / `P95: 1.74 ms`) |
| **3. `/xbrief /xobsidian` (`Cap 8` + `2-Hop` Vault)** | **`12`** (`8` Repo + `4` Vault) | **`1,279`** | **`52,053` tok** | **`-97.06%` (`34.0×`)** | **`1.4 ms`** (`1.47 ± 0.31 ms` / `P95: 1.99 ms`) |

---

## Experiment 3: `/xlaya` System 1 Section Shortlisting Speed (`3` Warm-Ups + `30` Trials)

| Metric | Measured Value |
|:---|:---|
| **Markdown Specifications Chunked** | `28` files (`1017` fence-safe heading chunks `≤ 1,200` chars) |
| **Full Unchunked Corpus Size** | `154,349` tokens |
| **Top-5 Shortlisted Pass-B Size** | **`997` tokens (`-99.35%` token reduction)** |
| **Single-Pass Triage Latency (`N = 30`)** | **Median `147.43 ms`** (`Mean 147.93 ± 4.77 ms` • `IQR 4.83 ms` • `P95 156.61 ms`) |
| **Chunk Evaluation Throughput** | **`6,898.2` chunks / sec** (`deterministic-lexical-stdlib`) |

---

## Experiment 4: 25-Defect Red-Team Injection Suite (`3` Warm-Ups + `20` Trials)

| Defect Category (`5` Seeded Defects Each) | Prompt-Only Skills (No CLI Gate) | XBoost CLI Verification Gate | Defects Caught |
|:---|:---:|:---|:---:|
| **1. Security & Portability** (AWS/GH keys, hardcoded user path, `eval`, `shell=True`, `pickle`) | `0 / 5` | `xpublish/scripts/audit_engine.py` | **`5 / 5` (`100%`)** |
| **2. QGIS 4 / Qt6 & INI Packaging** (`Qt.AlignCenter`, `QDialog.Accepted`, `QMessageBox.Yes`, raw `%`, hook) | `0 / 5` | `xpublish/scripts/check_qt6.py` + `audit_engine.py` | **`5 / 5` (`100%`)** |
| **3. Deep-Research Evidence & Schema** (`[TBD]`, `example.com`, bare root URL, quota, year bounds) | `0 / 5` | `xdeep-research/scripts/verify_evidence.py` | **`5 / 5` (`100%`)** |
| **4. Doc Sync, Links, Zero-LaTeX & Mirrors** (2 broken links, inline LaTeX, deprecated term, SHA-256 drift) | `0 / 5` | `xsync/scripts/audit_workspace_docs.py` | **`5 / 5` (`100%`)** |
| **5. Skill Budget & Hygiene** (`>500` char YAML, naming, broken link, `__pycache__`, `.pyc` binary) | `0 / 5` | `audit_engine.py --platform skill` | **`5 / 5` (`100%`)** |
| **Total Recall / Precision / Latency (`N = 20`)** | **`0 / 25` (`0.0%`)** | **All 10 XBoost CLI Gates (`22,237` LOC)** | **`25 / 25` (`100.0%` Recall • `100.0%` Precision • Median `8.14 ms`)** |

---

## Experiment 5: Composable Workflow Ablation Matrix (`Level 0` → `Level 3`)

| Workflow Level | Command Chain | Briefing Scan Tokens | Vault Nodes Routed | Active CLI Gates | Seeded Defect Catch Rate | Avg Steps / Turn | Recommended Subscription Tier |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **Baseline 0: Unstructured Prompting (No Skills)** | `<raw prompt>` | `1,770,934` | `0` | `0` | **`0.0%`** | `27.0` | **Free / 1× Base Tier** |
| **Level 1: Single Core Solver** | `/xboost` | `47,436` | `0` | `2` | **`40.0%`** | `15.2` | **1× Pro / 5× Max Tier** |
| **Level 2: Repo-Briefed + Primary Probe + 2-Hop Vault** | `/xbrief /xdeep-research /xboost /xobsidian` | `52,053` | `612` | `4` | **`80.0%`** | `92.9` | **5× Max Tier (Claude Max 5× / Gemini 5×)** |
| **Level 3: Full 5-Stage Lifecycle + System 1 + 10 CLI Gates + /xlearn** | `/xbrief /xdeep-research /xboost /xultra /xlearn /xsync /xlaya + /xpublish` | `52,053` | `612` | `10` | **`100.0%`** | `747.3` | **20× Ultra Tier (Gemini Ultra 20× / Claude Max 20×)** |

---

## Experiment 6: Real Session Token Economics (`N = 484` Sessions / `1136` Prompt Turns)

### A. Per-Prompt Turn Token Telemetry (`Mean ± StdDev` & `Median [P25–P75]`)

| Execution Mode | Sample Size | Trajectory Depth (`Steps / Turn`) | Uncached New Input (`NewIn`) | KV-Cache Replay (`Cached Input`) | Internal `Thinking` | Model `Output` | **Total Processed / Turn** |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. Standard Turn (No `/x*` Skill)** | `733` turns | `27.0` *(Med `6`)* | `14,804` *(Med `1,508`)* | `1,532,253` *(Med `324,263`)* | `1,920` *(Med `652`)* | `6,413` *(Med `1,496`)* | **`1,555,391`** *(Med `332,285`)* |
| **2. Single `/x*` Skill Turn** | `114` turns | `15.2` *(Med `8`)* | `10,976` *(Med `4,549`)* | `938,568` *(Med `513,732`)* | `929` *(Med `462`)* | `3,324` *(Med `1,834`)* | **`953,797`** *(Med `516,120`)* |
| **3. Chained Multi-Skill `/x*` Turn** | `289` turns | **`92.9`** *(Med `48` • `3.44×`)* | **`97,839`** *(Med `68,260` • `6.61×`)* | **`4,887,567`** *(Med `2,278,938`)* | **`5,510`** *(Med `2,662`)* | **`25,432`** *(Med `11,634` • `3.97×`)* | **`5,016,348`** *(Med `2,313,666`)* |

### B. Full Multi-Turn Session Telemetry (`N = 484` Complete Sessions)

| Session Class | Sample Size | Steps / Session (`Mean` / `Median` / `P90`) | Uncached Input (`Mean` / `Median`) | KV-Cache Read (`Mean` / `Median`) | Thinking (`Mean` / `Median`) | Output (`Mean` / `Median`) | **Total Session Throughput (`Mean` / `Median` / `P90`)** |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Standard Session (No `/x*`)** | `420` | `60.2` / `42` / `121` | `80,517` / `53,848` | `1.85M` / `0.87M` | `4,536` / `2,063` | `12,341` / `7,004` | **`1.94M`** / `0.97M` / `4.28M` |
| **Single-Skill XBoost Session** | `5` | `82.0` / `28` / `199` | `78,471` / `31,024` | `3.56M` / `0.51M` | `3,967` / `1,102` | `13,908` / `3,281` | **`3.65M`** / `0.55M` / `10.12M` |
| **Chained Multi-Skill XBoost Session** | `59` | **`747.3`** / `604` / `1752` | **`648,208`** / `605,499` | **`41.92M`** / `32.82M` | **`49,074`** / `35,500` | **`199,257`** / `151,554` | **`42.82M` (`22.02×`)** / `33.26M` / `94.73M` |

### C. Recommended Subscription Tier Sizing Guide

| Subscription Quota Tier | Representative Plans | Optimal XBoost Workload | Empirical Token Budget Justification |
|:---|:---|:---|:---|
| **Tier 1: `1×` Base Pro** | Claude Pro (`1×`), Gemini Advanced, Cursor Pro | **Single-Skill Tactical Tasks** (`/xbrief`, `/xdeep-research` Tier 1, localized `/xboost`) | Handles `~35k` uncached input + `~20k` output tokens (`~44` steps/turn). Multi-wave chains will hit 5-hour rolling caps after 1–2 runs. |
| **Tier 2: `5×` High-Throughput** *(Recommended Minimum)* | **Claude Max `5×`**, **Gemini `5×`**, API Tier 2+ | **Daily Chained Multi-Skill Sprints** (`/xbrief /xdeep-research /xboost /xlearn /xsync /xobsidian`) | Sustains `~70k` uncached input + `~22k` output + `~3.8M` KV-cache replay tokens across `~74` verification steps per turn without throttling. |
| **Tier 3: `20×` Ultra / Marathon** *(Studio Standard)* | **Gemini Ultra `20×`**, **Claude Max `20×`**, Enterprise API | **Autonomous `/goal` Marathons & `/xdeep-research` 5-Wave Swarms** | Engineered for `400+`-step autonomous sessions (`~400k` uncached input, `~153k` output, `~29.0M` cumulative session tokens + parallel subagent swarms). |

---

## Experiment 7: 4-Tier Sharded Compound Learning Playbooks & Real-World Upstream Open-Source Speedup Receipts (`24 PRs + 1 Hold`)

To evaluate how [`/xlearn`](../skills/xlearn/SKILL.md) and [`docs/COMPOUND_LEARNING_PLAYBOOK.md`](../docs/COMPOUND_LEARNING_PLAYBOOK.md) (`L1` Router Hub → `docs/playbooks/PLAYBOOK_1A..1D_*.md` `L2` Shards: `24 PAT-*/OPT-*` across `21` families incl. `OPT-MOO-01`, `7 GOV-*`, and `13 FALS-01..13`) compound engineering effectiveness across external codebases, we executed XBoost (`Stage 1 /xbrief + /xdeep-research → Stage 3 /xboost + /xultra → Stage 4 /xlearn + /xpublish --platform pr + /xsync --federated`) across **24 upstream open-source PRs + 1 Hold** (`10 MERGED`, `9 OPEN PRs`, `1 Hold`, `5 Closed/Staged`):

| Cohort & Upstream Target | Playbook Patterns & Governance | Baseline Bottleneck / Defect (`HEAD`) | XBoost Patch & Numerical Verification | Measured Wall-Clock Speedup / Receipt |
|:---|:---|:---|:---|:---|
| **`Group B` — [`ladybug-tools/uwg #292`](https://github.com/ladybug-tools/uwg/pull/292)** *(MIT, `OPEN`)* | `PAT-VEC-03`, `PAT-CACHE-01`, `GOV-02` | `sum(soil_temp)` inside `105,120`-step loop (`8.85 s`); hardcoded `[0]` climate zone (`#291`); `windProf` step-buffer leak | Hoisted precomputed `forcIP.deepTemp` (`5.10 ms`); indexed `[zone_idx]`; reset `windProf`; preserved upstream `CRLF` (`38`-line diff) | **`1,735.6×` speedup** (`68/68` `pytest` PASS, **`OPEN`**) |
| **`Group B` — [`os-climate/physrisk #651`](https://github.com/os-climate/physrisk/pull/651)** *(FINOS / Linux Foundation, `OPEN`)* | `PAT-VEC-01..02`, `PAT-NUM-01`, `GOV-01` | `O(N²)` list scan in `geocode_in_place` (`541.3 ms`); `np.vectorize` in `get_impact_distrib` (`7.15 s`); caller array mutation & `left = -1` wrap | Direct key iteration (`0.32 ms`); broadcasted `scipy.stats.norm.cdf` (`0.22 s`); non-mutating `np.minimum`; clamped `np.maximum(0, right - 1)` | **`1,669.6×` & `32.5×` speedups** (`11/11` `pytest` PASS, **`OPEN`**) |
| **`Group A` — [`Weecology/DeepForest #1449`](https://github.com/Weecology/DeepForest/pull/1449) & [`#1464`](https://github.com/Weecology/DeepForest/pull/1464)** *(`#1449 MERGED`)* | `PAT-VEC-01`, `PAT-GIS-01`, `GOV-07` | Row-wise `.iterrows()` + `shapely.geometry.box` loops in `utilities.py`, `IoU.py`, `evaluate.py`; `PathLike` rejection (`#1440`) | Vectorized `shapely.box` & `STRtree` (`421.3×` `convert_to_sv_format`, `173.9×` `IoU.match_points`, `74.4×` `utilities.py`); `os.fspath()` (`#1464` `OPEN`) | **`74.4× – 421.3×` speedups** (`#1449` **`MERGED`** `a60b890` + `#1464` `OPEN`) |
| **`Group B` — [`CLIMADA-project/climada_python #1349`](https://github.com/CLIMADA-project/climada_python/pull/1349) & [`#1350`](https://github.com/CLIMADA-project/climada_python/pull/1350)** *(ETH Zürich)* | `PAT-VEC-01`, `PAT-NUM-01`, `GOV-04` | Scalar `box()` loop in `points_to_raster` (`1.49 s`); CSR column-slice loop in `impact_at_reg`; `.nonzero()` explicit-zero drop; ISO/NaN bugs (`#1331`) | C-vectorized `shapely.box` (`69.9×` isolated `apply_box`, `2.1×` E2E); `imp_mat @ reg_ind` CSR matmul (`11.7×` E2E); ISO & `isnan` guards | **`69.9×` & `11.7×` speedups** (`#1350` **`MERGED`** `a1f1440`, `#1349` **`OPEN`**) |
| **`Group A` — [`gboeing/osmnx #1412`](https://github.com/gboeing/osmnx/pull/1412), [`#1410`](https://github.com/gboeing/osmnx/issues/1410) & [`#1405`](https://github.com/gboeing/osmnx/issues/1405)** *(`MERGED`)* | `PAT-CONC-01`, `PAT-NUM-01`, `GOV-07` | Zero-length self-loop `ZeroDivisionError` in `stats.circuity_avg` (`#1410`); `pytest-xdist` collision (`#1405`) | Guarded `edge_length_total == 0` returning `np.float64(0.0)` (`PR #1412` invited by `@gboeing`); `40.2×` vectorization; `xdist_group` marker | **`40.2×` speedup** • **`PR #1412 MERGED`** |
| **`Group B` — [`Deltares/hydromt #1566`](https://github.com/Deltares/hydromt/pull/1566)** *(Deltares Netherlands, `OPEN`)* | `PAT-VEC-01`, `PAT-GIS-01`, `GOV-03` | Scalar `box()` loop in `create_mesh2d_from_geom` (`897 ms`); dropped `crs` on projected `bbox` (`#1563`); `nodata_ref = None` before warning log | C-vectorized `shapely.box` (`32.6 ms`); passed `crs=self.metadata.crs` & reprojected `geom`; logged `nodata_ref` before reset | **`27.5×` speedup** (`114/114` `pytest` PASS, **`OPEN`**) |
| **`Group B` — [`natcap/invest #2813`](https://github.com/natcap/invest/issues/2813), [`#2829`](https://github.com/natcap/invest/issues/2829) & [`#2839`](https://github.com/natcap/invest/pull/2839)** *(Stanford NatCap)* | `PAT-VEC-03`, `PAT-GIS-01`, `GOV-05` | Repeated OGR `GetFeature(fid)` + `wkb.loads` inside AOI R-tree loops (`420.2 ms` UCM, `421.6 ms` UFRM); `&` vs `|` nodata mask | Pass-1 FID geometry cache (`23.1×` UCM `+0.51 MB` RAM) & Inverted AOI R-tree (`18.1×` `O(N)` / `2.0×` `O(M)` `0.18 MB` RAM UFRM); De Morgan `|` mask | **`23.1×` UCM & `O(M)` UFRM** (`#2829 Hold`, `#2839 Closed`) |
| **`Group A` — [`martibosch/pylandstats #77`](https://github.com/martibosch/pylandstats/pull/77)** *(`OPEN`)* | `PAT-VEC-02`, `PAT-GIS-01` | Per-label `scipy.ndimage.center_of_mass` scan (`79.85 ms` on `66,496` patches); string `edge_depths` support (`#69`) | Single-pass vectorized `np.bincount(labels.ravel(), weights=...)` (`19.76 ms`) + `landscapemetrics`-style string `edge_depths` | **`4.0×` speedup** (`9/9` `pytest` PASS, **`OPEN`**) |
| **`Group A & C` — [`opengeos/geoai #960`](https://github.com/opengeos/geoai/pull/960) (`MERGED`), [`segment-geospatial #569`](https://github.com/opengeos/segment-geospatial/pull/569), [`code2prompt #348`](https://github.com/mufeedvh/code2prompt/pull/348) & `UMEP` (`3` Staged)** | `PAT-PARITY-01`, `PAT-CV-01`, `GOV-06` | Host `PYTHONEXECUTABLE` venv bleed (`#951`); missing `SamGeo` vector attrs (`#543`); Rust glob/token tree; `UMEP` `173.0×` UTCI / `799.8×` `load_walls` | Sanitized `PYTHON*` env vars (`geoai#960` **`MERGED`** `0b13f11`); `SamGeo` (`10/10`); `code2prompt#348` (`9/9` `OPEN`); `UMEP#885`/`#149`/`#6` split-staged | **`geoai#960 MERGED`** • **`#569`/`#348` `OPEN`** • **`3` Staged** |
| **`Batch 0` — [`xerj-org/xerj #2922–#2927`](https://github.com/xerj-org/xerj/pulls?q=is%3Apr+author%3Anapattan) & [`scb-10x/typhoon-ocr #16`](https://github.com/scb-10x/typhoon-ocr/pull/16)** | `PAT-OCR-01`, `PAT-PARITY-01` | Sub-max image upscale (`5.11×` token bloat); legacy Thai PDF PUA junking (`exit 3`); Windows MSVC `#[cfg(unix)]` & spool lock test failures | Downscale-only `resize_if_needed` (`#16 OPEN`, `#15 Closed`); Thai PUA + Sara-Am (`#2925 MERGED`); `#2922..#2927` **`6/6 MERGED`** | **`6 MERGED` + `1 OPEN PR`** (`-35.9%` vision tokens, `1,912/1,954` MSVC tests) |
