# XBoost (`v3.5.0`) — Empirical Benchmark & Token Economics Report

> **Reproducible Verification Harness**: Generated deterministically by [`benchmarks/run_xboost_benchmark.py`](./run_xboost_benchmark.py)  
> **Corpus Scope**: `115` Installed Agent Skills • `232` Repository Markdown Specs • `602` Obsidian Second Brain Nodes • `442` Real IDE Sessions (`810` Prompt Turns) • `22` Upstream Open-Source Contributions (`5 MERGED`)  
> **Statistical Rigor**: Timing benchmarks execute `3` warm-up passes followed by `N = 30` timed iterations (`time.perf_counter_ns()`), reporting **Median (`P50`)**, **Mean ± StdDev**, **IQR (`P25–P75`)**, and **`P95`**.

---

## ⚡ TL;DR - Empirical Scorecard at a Glance (`v3.5.0`)

| Evaluation Dimension | Workflow / Cohort Configuration | Visual Comparison Bar | Measured Result & Delta vs. Baseline |
| :--- | :--- | :--- | :--- |
| **1. Red-Team Defect Catch Rate ↑**<br>*(25 Seeded Defects across 5 Pillars)* | **Level 3: Full 5-Stage + 10 CLI Gates**<br>Level 2: `/xbrief` + `/xdeep-research` + `/xboost`<br>Level 1: `/xboost` Standalone (2 Gates)<br>Level 0: Prompt-Only Baseline (0 Gates) | `████████████████████` **`100.0% (25/25)`**<br>`████████████████░░░░` `80.0% (20/25)`<br>`████████░░░░░░░░░░░░` `40.0% (10/25)`<br>`░░░░░░░░░░░░░░░░░░░░` `0.0% (0.0%)` | **`0` False Positives in Median `8.72 ms`** ✨<br>`4` Active CLI Verification Gates<br>`2` Active CLI Verification Gates<br>No Deterministic Pre-LLM Enforcement |
| **2. Context Noise Compression ↑**<br>*(834 Repo + Vault Files, `1.64M` tok)* | **`/xbrief` (`Cap 8`) Repo-Only**<br>**`/xbrief` (`Cap 8`) + `/xobsidian` (`2-Hop`)**<br>Unbounded Repo + Vault Crawl | `████████████████████` **`97.06% Removed (34.0×)`**<br>`████████████████████` **`96.78% Removed (31.1×)`**<br>`░░░░░░░░░░░░░░░░░░░░` `0.0% Removed (1.0×)` | **`48,249` tok in Median `1.2 ms`** ✨<br>**`52,789` tok (`12` files) in `1.22 ms`** ✨<br>`1,639,692` tok (`834` files) in `50.7 ms` |
| **3. System 1 Section Triage ↑**<br>*(27 Specs / 1170 Chunks, `174.9k` tok)* | **XBoost `/xlaya` Top-5 Shortlist**<br>Unfiltered Full-Corpus Pass-B Read | `████████████████████` **`99.35% Saved (153.8×)`**<br>`░░░░░░░░░░░░░░░░░░░░` `0.0% Saved (1.0×)` | **`1,137` tok in Median `180.0 ms`** (`6.5k` chunks/s) ✨<br>`174,870` tok (Full 27-File Read) |
| **4. Dual-Trigger Budget Guard ↑**<br>*(`Use when` + `Do NOT use` across `N=115`)* | **XBoost `v3.5.0` Suite (`N = 15`)**<br>All Installed Host Skills (`N = 115`)<br>Official Cloud/Vendor Skills (`N = 31`) | `████████████████████` **`100.0% (15/15)`**<br>`██████████████████░░` `91.3%`<br>`█████████████████░░░` `87.1%` | **`374.47 ± 9.95` chars (`0%` Truncation)** ✨<br>`324.78 ± 51.73` chars (`99.1%` `≤500` pass)<br>`331.1 ± 63.41` chars (`96.8%` `≤500` pass) |
| **5. Verification Depth / Turn ↑**<br>*(`N = 810` Real IDE Prompt Turns)* | **Chained Multi-Skill `/x*` Turn (`N=245`)**<br>Single `/x*` Skill Turn (`N = 89`)<br>Standard Turn Without `/x*` (`N = 476`) | `████████████████████` **`90.6 Steps (3.94×)`**<br>`███░░░░░░░░░░░░░░░░░` `12.6 Steps`<br>`█████░░░░░░░░░░░░░░░` `23.0 Steps (1.0×)` | **`4.88M` tok/turn (`93.4k` new in, `24.4k` out)** ✨<br>`0.78M` tok/turn (`9.9k` new in, `2.9k` out)<br>`1.26M` tok/turn (`13.6k` new in, `5.6k` out) |
| **6. Compound Learning OSS Speedups ↑**<br>*(`22` Upstream Contributions, `Batch 0 + A + B + C`)* | **`/xlearn` 3-Tier Playbooks (`PAT-*` + `GOV-*` + `FALS-*`)**<br>Unvectorized Upstream Baseline (`HEAD`) | `████████████████████` **`4.0× – 1,735.6× Faster`**<br>`░░░░░░░░░░░░░░░░░░░░` `1.0× Baseline` | **`100%` `assert_allclose` Parity (`5 MERGED`, `9 OPEN PRs`)** ✨<br>Python `np.vectorize`, `O(N²)` scans & OGR disk-seek loops |

---

## Executive Findings: High Intelligence via High Compute

1. **System-Prompt Budget Discipline (`100%` Compliance & Dual-Trigger Guards)**: Across all `15` XBoost `/x*` skills, YAML discovery descriptions average **`374.47 ± 9.95 chars`** (Median `374.0` chars, **`100.0%` within the `≤ 500` char `audit_engine.py` budget gate**) with **`100.0%` dual positive + negative (`Use when` / `Do NOT use for`) routing guards**, compared to `87.1%` dual-trigger coverage across `31` official cloud/enterprise skills.
2. **Context Noise Compression (`-96.78%` Scan Reduction)**: When briefing across multi-project repositories and the `602`-node Obsidian Second Brain (`1,639,692` tokens total), `/xbrief` (`Cap 8` Two-Pass) + `/xobsidian` (`2-Hop = 4` vault files) loads only **`52,789` tokens** (**`96.78%` noise reduction** / **`31.1×` compression**) in a median disk read time of **`1.22 ms`** (vs `50.7 ms` unbounded).
3. **System 1 `/xlaya` Triage (`180.0 ms` Median)**: Chunking and ranking `1170` fence-safe (`≤ 1,200`-char) heading sections across `27` specs completes in **`180.0 ms`** (`Mean 181.03 ± 5.15 ms`, `6,500.0 chunks/sec`), cutting Pass-B reading tokens by **`99.35%`**.
4. **Deterministic Red-Team Defect Catch Rate (`100.0%` vs `0.0%`)**: Across `25` seeded security, Qt6/QGIS 4, research citation, doc-sync, and skill-packaging defects, the 10 CLI gates (`10,382` LOC) achieve **`25 / 25` (`100.0%` recall)** and **`100.0%` precision** (`0` false positives) in **`8.72 ms`**.
5. **Transparent Token Economics (Why XBoost Recommends `5×`–`20×` Subscriptions)**: While XBoost slashes *garbage file noise* by `96.78%`, it deliberately invests that freed context capacity into **deep multi-gate verification**. Across `810` real prompt turns, a chained multi-skill XBoost turn executes **`90.58 steps`** (`3.94×` deeper than standard `22.97`-step turns), consuming **`93,386` uncached input tokens (`6.88×`)**, **`24,399` output tokens (`4.35×`)**, and **`4,757,425` KV-cache read tokens** per turn (`~39.71M` total tokens across a full `711`-step marathon session).
6. **3-Tier Compound Learning Playbooks (`4.0×` – `1,735.6×` Real-World Upstream Speedups)**: By distilling verified bug and bottleneck signatures via [`/xlearn`](../skills/xlearn/SKILL.md) into [`docs/COMPOUND_LEARNING_PLAYBOOK.md`](../docs/COMPOUND_LEARNING_PLAYBOOK.md) (`19 PAT-*`, `7 GOV-*`, `11 FALS-*` + 3 specialized domain playbooks), XBoost achieved **`4.0×` to `1,735.6×` measured wall-clock speedups** with **`100%` numerical equivalence** across **22 upstream open-source contributions** (`5 MERGED`, `9 OPEN PRs`, `4 OPEN Issues`, `4 Staged`).

---

## Experiment 1: Skill Discovery & Context Budget Audit (`N = 115` Installed Skills)

| Skill Cohort | Count | YAML Desc Chars (`Mean ± SD` / `Median`) | `≤ 500` Char Gate Pass | Dual Trigger Guard (`Use when` + `Do NOT use`) | Full `SKILL.md` Tokens (`Mean ± SD` / `Median`) | Bundled CLI Scripts (`LOC`) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **XBoost `v3.5.0` Suite (`/x*` Skills)** | `15` | **`374.47 ± 9.95`** (`374.0`) | **`100.0%`** | **`100.0%`** | `4,551 ± 2,119` (`3,867`) | **`10` (`10,382` LOC)** |
| **Official Cloud & Enterprise Vendor Skills** | `31` | `331.1 ± 63.41` (`324.0`) | `96.8%` | `87.1%` | `2,518 ± 1,692` (`2,468`) | `5` (`2,880` LOC) |
| **All Installed Host Skills Pool** | `115` | `324.78 ± 51.73` (`319.0`) | `99.1%` | `91.3%` | `2,168 ± 1,938` (`1,511`) | `59` (`28,199` LOC) |

---

## Experiment 2: Context Window Compression & 2-Hop Vault Isolation (`3` Warm-Ups + `30` Trials)

| Briefing Regime | Files Read | Lines Read | Context Tokens Loaded | Noise Reduction (`%` / Factor) | Disk Read Latency (`Median` / `Mean ± SD` / `P95`) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **1. Unbounded Repo + Vault Crawl** | `834` | `71,970` | `1,639,692` tok | Baseline (`1.0×`) | `50.7 ms` (`50.84 ± 3.07 ms` / `P95: 55.11 ms`) |
| **2. `/xbrief` Repo-Only (`Cap 8` Two-Pass)** | **`8`** | **`1,010`** | **`48,249` tok** | **`-97.06%` (`34.0×`)** | **`1.2 ms`** (`1.3 ± 0.45 ms` / `P95: 1.63 ms`) |
| **3. `/xbrief /xobsidian` (`Cap 8` + `2-Hop` Vault)** | **`12`** (`8` Repo + `4` Vault) | **`1,179`** | **`52,789` tok** | **`-96.78%` (`31.1×`)** | **`1.22 ms`** (`1.33 ± 0.3 ms` / `P95: 1.96 ms`) |

---

## Experiment 3: `/xlaya` System 1 Section Shortlisting Speed (`3` Warm-Ups + `30` Trials)

| Metric | Measured Value |
|:---|:---|
| **Markdown Specifications Chunked** | `27` files (`1170` fence-safe heading chunks `≤ 1,200` chars) |
| **Full Unchunked Corpus Size** | `174,870` tokens |
| **Top-5 Shortlisted Pass-B Size** | **`1,137` tokens (`-99.35%` token reduction)** |
| **Single-Pass Triage Latency (`N = 30`)** | **Median `180.0 ms`** (`Mean 181.03 ± 5.15 ms` • `IQR 7.03 ms` • `P95 189.61 ms`) |
| **Chunk Evaluation Throughput** | **`6,500.0` chunks / sec** (`deterministic-lexical-stdlib`) |

---

## Experiment 4: 25-Defect Red-Team Injection Suite (`3` Warm-Ups + `20` Trials)

| Defect Category (`5` Seeded Defects Each) | Prompt-Only Skills (No CLI Gate) | XBoost CLI Verification Gate | Defects Caught |
|:---|:---:|:---|:---:|
| **1. Security & Portability** (AWS/GH keys, hardcoded user path, `eval`, `shell=True`, `pickle`) | `0 / 5` | `xpublish/scripts/audit_engine.py` | **`5 / 5` (`100%`)** |
| **2. QGIS 4 / Qt6 & INI Packaging** (`Qt.AlignCenter`, `QDialog.Accepted`, `QMessageBox.Yes`, raw `%`, hook) | `0 / 5` | `xpublish/scripts/check_qt6.py` + `audit_engine.py` | **`5 / 5` (`100%`)** |
| **3. Deep-Research Evidence & Schema** (`[TBD]`, `example.com`, bare root URL, quota, year bounds) | `0 / 5` | `xdeep-research/scripts/verify_evidence.py` | **`5 / 5` (`100%`)** |
| **4. Doc Sync, Links, Zero-LaTeX & Mirrors** (2 broken links, inline LaTeX, deprecated term, SHA-256 drift) | `0 / 5` | `xsync/scripts/audit_workspace_docs.py` | **`5 / 5` (`100%`)** |
| **5. Skill Budget & Hygiene** (`>500` char YAML, naming, broken link, `__pycache__`, `.pyc` binary) | `0 / 5` | `audit_engine.py --platform skill` | **`5 / 5` (`100%`)** |
| **Total Recall / Precision / Latency (`N = 20`)** | **`0 / 25` (`0.0%`)** | **All 10 XBoost CLI Gates (`10,382` LOC)** | **`25 / 25` (`100.0%` Recall • `100.0%` Precision • Median `8.72 ms`)** |

---

## Experiment 5: Composable Workflow Ablation Matrix (`Level 0` → `Level 3`)

| Workflow Level | Command Chain | Briefing Scan Tokens | Vault Nodes Routed | Active CLI Gates | Seeded Defect Catch Rate | Avg Steps / Turn | Recommended Subscription Tier |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **Baseline 0: Unstructured Prompting (No Skills)** | `<raw prompt>` | `1,639,692` | `0` | `0` | **`0.0%`** | `23.0` | **Free / 1× Base Tier** |
| **Level 1: Single Core Solver** | `/xboost` | `48,249` | `0` | `2` | **`40.0%`** | `12.6` | **1× Pro / 5× Max Tier** |
| **Level 2: Repo-Briefed + Primary Probe + 2-Hop Vault** | `/xbrief /xdeep-research /xboost /xobsidian` | `52,789` | `602` | `4` | **`80.0%`** | `90.6` | **5× Max Tier (Claude Max 5× / Gemini 5×)** |
| **Level 3: Full 5-Stage Lifecycle + System 1 + 10 CLI Gates + /xlearn** | `/xbrief /xdeep-research /xboost /xultra /xlearn /xsync /xlaya + /xpublish` | `52,789` | `602` | `10` | **`100.0%`** | `711.2` | **20× Ultra Tier (Gemini Ultra 20× / Claude Max 20×)** |

---

## Experiment 6: Real Session Token Economics (`N = 442` Sessions / `810` Prompt Turns)

### A. Per-Prompt Turn Token Telemetry (`Mean ± StdDev` & `Median [P25–P75]`)

| Execution Mode | Sample Size | Trajectory Depth (`Steps / Turn`) | Uncached New Input (`NewIn`) | KV-Cache Replay (`Cached Input`) | Internal `Thinking` | Model `Output` | **Total Processed / Turn** |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. Standard Turn (No `/x*` Skill)** | `476` turns | `23.0` *(Med `5`)* | `13,574` *(Med `1,139`)* | `1,241,903` *(Med `227,284`)* | `1,445` *(Med `538`)* | `5,613` *(Med `1,362`)* | **`1,262,534`** *(Med `232,304`)* |
| **2. Single `/x*` Skill Turn** | `89` turns | `12.6` *(Med `7`)* | `9,887` *(Med `3,790`)* | `767,673` *(Med `492,485`)* | `696` *(Med `357`)* | `2,903` *(Med `1,784`)* | **`781,158`** *(Med `494,960`)* |
| **3. Chained Multi-Skill `/x*` Turn** | `245` turns | **`90.6`** *(Med `53` • `3.94×`)* | **`93,386`** *(Med `66,209` • `6.88×`)* | **`4,757,425`** *(Med `2,853,368`)* | **`5,126`** *(Med `2,973`)* | **`24,399`** *(Med `12,937` • `4.35×`)* | **`4,880,336`** *(Med `2,945,503`)* |

### B. Full Multi-Turn Session Telemetry (`N = 442` Complete Sessions)

| Session Class | Sample Size | Steps / Session (`Mean` / `Median` / `P90`) | Uncached Input (`Mean` / `Median`) | KV-Cache Read (`Mean` / `Median`) | Thinking (`Mean` / `Median`) | Output (`Mean` / `Median`) | **Total Session Throughput (`Mean` / `Median` / `P90`)** |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Standard Session (No `/x*`)** | `395` | `49.9` / `34` / `101` | `70,403` / `54,048` | `1.46M` / `0.75M` | `3,463` / `1,507` | `11,519` / `6,648` | **`1.55M`** / `0.83M` / `3.46M` |
| **Single-Skill XBoost Session** | `3` | `110.0` / `15` / `252` | `110,549` / `31,413` | `5.47M` / `0.23M` | `5,573` / `669` | `20,421` / `2,839` | **`5.61M`** / `0.27M` / `13.25M` |
| **Chained Multi-Skill XBoost Session** | `44` | **`711.2`** / `698` / `1393` | **`645,384`** / `601,446` | **`38.84M`** / `40.17M` | **`41,565`** / `33,578` | **`190,359`** / `187,560` | **`39.71M` (`25.7×`)** / `41.03M` / `68.35M` |

### C. Recommended Subscription Tier Sizing Guide

| Subscription Quota Tier | Representative Plans | Optimal XBoost Workload | Empirical Token Budget Justification |
|:---|:---|:---|:---|
| **Tier 1: `1×` Base Pro** | Claude Pro (`1×`), Gemini Advanced, Cursor Pro | **Single-Skill Tactical Tasks** (`/xbrief`, `/xdeep-research` Tier 1, localized `/xboost`) | Handles `~35k` uncached input + `~20k` output tokens (`~44` steps/turn). Multi-wave chains will hit 5-hour rolling caps after 1–2 runs. |
| **Tier 2: `5×` High-Throughput** *(Recommended Minimum)* | **Claude Max `5×`**, **Gemini `5×`**, API Tier 2+ | **Daily Chained Multi-Skill Sprints** (`/xbrief /xdeep-research /xboost /xlearn /xsync /xobsidian`) | Sustains `~70k` uncached input + `~22k` output + `~3.8M` KV-cache replay tokens across `~74` verification steps per turn without throttling. |
| **Tier 3: `20×` Ultra / Marathon** *(Studio Standard)* | **Gemini Ultra `20×`**, **Claude Max `20×`**, Enterprise API | **Autonomous `/goal` Marathons & `/xdeep-research` 5-Wave Swarms** | Engineered for `400+`-step autonomous sessions (`~400k` uncached input, `~153k` output, `~29.0M` cumulative session tokens + parallel subagent swarms). |

---

## Experiment 7: 3-Tier Compound Learning Playbooks & Real-World Upstream Open-Source Speedup Receipts (`22` Contributions)

To evaluate how [`/xlearn`](../skills/xlearn/SKILL.md) and [`docs/COMPOUND_LEARNING_PLAYBOOK.md`](../docs/COMPOUND_LEARNING_PLAYBOOK.md) (`19 PAT-*` Defect & Bottleneck Archetypes across `16` families, `7 GOV-*` Governance Fingerprints, and `11 FALS-*` Mirage Guardrails) compound engineering effectiveness across external codebases, we executed XBoost (`Stage 1 /xbrief + /xdeep-research → Stage 3 /xboost + /xultra → Stage 4 /xlearn + /xpublish --platform pr + /xsync --federated`) across **22 upstream open-source contributions** (`5 MERGED`, `9 OPEN PRs`, `4 OPEN Issues`, `4 Staged`):

| Cohort & Upstream Target | Playbook Patterns & Governance | Baseline Bottleneck / Defect (`HEAD`) | XBoost Patch & Numerical Verification | Measured Wall-Clock Speedup / Receipt |
|:---|:---|:---|:---|:---|
| **`Group B` — [`ladybug-tools/uwg #292`](https://github.com/ladybug-tools/uwg/pull/292)** *(MIT, `MERGED`)* | `PAT-VEC-03`, `PAT-CACHE-01`, `GOV-02` | `sum(soil_temp)` inside `105,120`-step loop (`8.85 s`); hardcoded `[0]` climate zone (`#291`); `windProf` step-buffer leak | Hoisted precomputed `forcIP.deepTemp` (`5.10 ms`); indexed `[zone_idx]`; reset `windProf`; preserved upstream `CRLF` (`38`-line diff) | **`1,735.6×` speedup** (`68/68` `pytest` PASS, **`MERGED`**) |
| **`Group B` — [`os-climate/physrisk #651`](https://github.com/os-climate/physrisk/pull/651)** *(FINOS / Linux Foundation, `Staged`)* | `PAT-VEC-01..02`, `PAT-NUM-01`, `GOV-01` | `O(N²)` list scan in `geocode_in_place` (`541.3 ms`); `np.vectorize` in `get_impact_distrib` (`7.15 s`); caller array mutation & `left = -1` wrap | Direct key iteration (`0.32 ms`); broadcasted `scipy.stats.norm.cdf` (`0.22 s`); non-mutating `np.minimum`; clamped `np.maximum(0, right - 1)` | **`1,669.6×` & `32.5×` speedups** (`11/11` `pytest` PASS, unbundled staged) |
| **`Group A` — [`Weecology/DeepForest #1449`](https://github.com/Weecology/DeepForest/pull/1449) & [`#1440`](https://github.com/Weecology/DeepForest/issues/1440)** | `PAT-VEC-01`, `PAT-GIS-01`, `GOV-07` | Row-wise `.iterrows()` + `shapely.geometry.box` loops in `utilities.py`, `IoU.py`, `evaluate.py`; `PathLike` rejection (`#1440`) | Vectorized `shapely.box` & `STRtree` (`421.3×` `convert_to_sv_format`, `173.9×` `IoU.match_points`, `74.4×` `utilities.py`); `os.fspath()` | **`74.4× – 421.3×` speedups** (`CI 3.12 PASS`, closes [`#1447`](https://github.com/Weecology/DeepForest/issues/1447)) |
| **`Group B` — [`CLIMADA-project/climada_python #1349`](https://github.com/CLIMADA-project/climada_python/pull/1349) & [`#1350`](https://github.com/CLIMADA-project/climada_python/pull/1350)** *(ETH Zürich)* | `PAT-VEC-01`, `PAT-NUM-01`, `GOV-04` | Scalar `box()` loop in `points_to_raster` (`1.49 s`); CSR column-slice loop in `impact_at_reg`; `.nonzero()` explicit-zero drop; ISO/NaN bugs (`#1331`) | C-vectorized `shapely.box` (`69.9×` isolated `apply_box`, `2.1×` E2E); `imp_mat @ reg_ind` CSR matmul (`11.7×` E2E); ISO & `isnan` guards | **`69.9×` & `11.7×` speedups** (`17/17` tests PASS, `base: develop`) |
| **`Group A` — [`gboeing/osmnx #1412`](https://github.com/gboeing/osmnx/pull/1412), [`#1410`](https://github.com/gboeing/osmnx/issues/1410) & [`#1405`](https://github.com/gboeing/osmnx/issues/1405)** | `PAT-GRAPH-01..02`, `PAT-NUM-01`, `GOV-07` | Zero-length self-loop `ZeroDivisionError` in `stats.circuity_avg` (`#1410`); `pytest-xdist` collision (`#1405`) | Guarded `edge_length_total == 0` returning `np.float64(0.0)` (`PR #1412` invited by `@gboeing`); `40.2×` vectorization; `xdist_group` marker | **`40.2×` speedup** • **`PR #1412` LIVE** (`100%` CI PASS) |
| **`Group B` — [`Deltares/hydromt #1566`](https://github.com/Deltares/hydromt/pull/1566)** *(Deltares Netherlands)* | `PAT-VEC-01`, `PAT-GIS-01`, `GOV-03` | Scalar `box()` loop in `create_mesh2d_from_geom` (`897 ms`); dropped `crs` on projected `bbox` (`#1563`); `nodata_ref = None` before warning log | C-vectorized `shapely.box` (`32.6 ms`); passed `crs=self.metadata.crs` & reprojected `geom`; logged `nodata_ref` before reset | **`27.5×` speedup** (`114/114` `pytest` PASS, `docs/changelog.rst`) |
| **`Group B` — [`natcap/invest #2813`](https://github.com/natcap/invest/issues/2813) & [`#2829`](https://github.com/natcap/invest/pull/2829)** *(Stanford NatCap)* | `PAT-VEC-03`, `PAT-GIS-01`, `GOV-05` | Repeated OGR `GetFeature(fid)` + `wkb.loads` inside AOI R-tree loops (`420.2 ms` UCM, `421.6 ms` UFRM); `&` vs `|` nodata mask | Pass-1 FID geometry cache (`23.1×` UCM `+0.51 MB` RAM) & Inverted AOI R-tree (`18.1×` `O(N)` / `2.0×` `O(M)` `0.18 MB` RAM UFRM); De Morgan `|` mask | **`23.1×` UCM & `18.1×` UFRM speedups** (`100%` parity, on hold) |
| **`Group A` — [`martibosch/pylandstats #77`](https://github.com/martibosch/pylandstats/pull/77)** *(`MERGED`)* | `PAT-VEC-02`, `PAT-GIS-01` | Per-label `scipy.ndimage.center_of_mass` scan (`79.85 ms` on `66,496` patches); string `edge_depths` support (`#69`) | Single-pass vectorized `np.bincount(labels.ravel(), weights=...)` (`19.76 ms`) + `landscapemetrics`-style string `edge_depths` | **`4.0×` speedup** (`9/9` `pytest` PASS, **`MERGED`**) |
| **`Group A & C` — [`opengeos/geoai #960`](https://github.com/opengeos/geoai/pull/960) (`MERGED`), [`segment-geospatial #569`](https://github.com/opengeos/segment-geospatial/pull/569) & [`mufeedvh/code2prompt #348`](https://github.com/mufeedvh/code2prompt/pull/348)** | `PAT-PARITY-01`, `PAT-CV-01`, `GOV-06` | Host `PYTHONEXECUTABLE` venv bleed (`#951`); missing `SamGeo` vector attributes (`#543`); Rust glob/token traversal in `code2prompt` | Sanitized `PYTHON*` env vars (`geoai#960` **`MERGED`** as `0b13f11`); `SamGeo` vector attributes (`10/10` CI); `code2prompt#348` (`9/9` `cargo test` PASS) | **`geoai#960 MERGED`** • **`segment-geospatial#569` & `code2prompt#348` LIVE** |
| **`Batch 0` — [`xerj-org/xerj #2922–#2927`](https://github.com/xerj-org/xerj/pulls?q=is%3Apr+author%3Anapattan) & [`scb-10x/typhoon-ocr #15`](https://github.com/scb-10x/typhoon-ocr/pull/15)** *(`MERGED`)* | `PAT-OCR-01`, `PAT-PARITY-01` | Sub-max image upscale (`5.11×` token bloat); legacy Thai PDF PUA junking (`exit 3`); Windows MSVC `#[cfg(unix)]` & spool lock test failures | Downscale-only `resize_if_needed`; Rust/Python Thai PUA + Sara-Am normalizer (`#2925` **`MERGED`**); `typhoon-ocr#15` (**`MERGED`**); Windows MSVC fixes | **`-35.9%` vision tokens** • **`1,912/1,954` MSVC tests** • **`2 MERGED`** |
