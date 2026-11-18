# XBoost (`v3.5.0`) — Empirical Benchmark & Token Economics Report

> **Reproducible Verification Harness**: Generated deterministically by [`benchmarks/run_xboost_benchmark.py`](./run_xboost_benchmark.py)  
> **Corpus Scope**: `117` Installed Agent Skills • `280` Repository Markdown Specs • `609` Obsidian Second Brain Nodes • `450` Real IDE Sessions (`1093` Prompt Turns) • `22` Upstream Open-Source Contributions (`5 MERGED`)  
> **Statistical Rigor**: Timing benchmarks execute `3` warm-up passes followed by `N = 30` timed iterations (`time.perf_counter_ns()`), reporting **Median (`P50`)**, **Mean ± StdDev**, **IQR (`P25–P75`)**, and **`P95`**.

---

## ⚡ TL;DR - Empirical Scorecard at a Glance (`v3.5.0`)

| Evaluation Dimension | Workflow / Cohort Configuration | Visual Comparison Bar | Measured Result & Delta vs. Baseline |
| :--- | :--- | :--- | :--- |
| **1. Red-Team Defect Catch Rate ↑**<br>*(25 Seeded Defects across 5 Pillars)* | **Level 3: Full 5-Stage + 10 CLI Gates**<br>Level 2: `/xbrief` + `/xdeep-research` + `/xboost`<br>Level 1: `/xboost` Standalone (2 Gates)<br>Level 0: Prompt-Only Baseline (0 Gates) | `████████████████████` **`100.0% (25/25)`**<br>`████████████████░░░░` `80.0% (20/25)`<br>`████████░░░░░░░░░░░░` `40.0% (10/25)`<br>`░░░░░░░░░░░░░░░░░░░░` `0.0% (0.0%)` | **`0` False Positives in Median `8.09 ms`** ✨<br>`4` Active CLI Verification Gates<br>`2` Active CLI Verification Gates<br>No Deterministic Pre-LLM Enforcement |
| **2. Context Noise Compression ↑**<br>*(889 Repo + Vault Files, `1.75M` tok)* | **`/xbrief` (`Cap 8`) Repo-Only**<br>**`/xbrief` (`Cap 8`) + `/xobsidian` (`2-Hop`)**<br>Unbounded Repo + Vault Crawl | `████████████████████` **`96.99% Removed (33.2×)`**<br>`████████████████████` **`96.73% Removed (30.5×)`**<br>`░░░░░░░░░░░░░░░░░░░░` `0.0% Removed (1.0×)` | **`52,761` tok in Median `1.19 ms`** ✨<br>**`57,366` tok (`12` files) in `1.49 ms`** ✨<br>`1,752,358` tok (`889` files) in `54.94 ms` |
| **3. System 1 Section Triage ↑**<br>*(24 Specs / 990 Chunks, `149.3k` tok)* | **XBoost `/xlaya` Top-5 Shortlist**<br>Unfiltered Full-Corpus Pass-B Read | `████████████████████` **`99.33% Saved (149.8×)`**<br>`░░░░░░░░░░░░░░░░░░░░` `0.0% Saved (1.0×)` | **`997` tok in Median `144.12 ms`** (`6.9k` chunks/s) ✨<br>`149,323` tok (Full 24-File Read) |
| **4. Dual-Trigger Budget Guard ↑**<br>*(`Use when` + `Do NOT use` across `N=117`)* | **XBoost `v3.5.0` Suite (`N = 15`)**<br>All Installed Host Skills (`N = 117`)<br>Official Cloud/Vendor Skills (`N = 31`) | `████████████████████` **`100.0% (15/15)`**<br>`██████████████████░░` `90.6%`<br>`█████████████████░░░` `87.1%` | **`371.07 ± 20.14` chars (`0%` Truncation)** ✨<br>`324.53 ± 51.25` chars (`99.1%` `≤500` pass)<br>`331.1 ± 63.41` chars (`96.8%` `≤500` pass) |
| **5. Verification Depth / Turn ↑**<br>*(`N = 1093` Real IDE Prompt Turns)* | **Chained Multi-Skill `/x*` Turn (`N=275`)**<br>Single `/x*` Skill Turn (`N = 112`)<br>Standard Turn Without `/x*` (`N = 706`) | `████████████████████` **`91.2 Steps (3.45×)`**<br>`███░░░░░░░░░░░░░░░░░` `15.3 Steps`<br>`█████░░░░░░░░░░░░░░░` `26.5 Steps (1.0×)` | **`4.71M` tok/turn (`96.6k` new in, `24.6k` out)** ✨<br>`0.97M` tok/turn (`10.8k` new in, `3.3k` out)<br>`1.48M` tok/turn (`14.4k` new in, `6.0k` out) |
| **6. Compound Learning OSS Speedups ↑**<br>*(`22` Upstream Contributions, `Batch 0 + A + B + C`)* | **`/xlearn` 3-Tier Playbooks (`PAT-*` + `GOV-*` + `FALS-*`)**<br>Unvectorized Upstream Baseline (`HEAD`) | `████████████████████` **`4.0× – 1,735.6× Faster`**<br>`░░░░░░░░░░░░░░░░░░░░` `1.0× Baseline` | **`100%` `assert_allclose` Parity (`5 MERGED`, `9 OPEN PRs`)** ✨<br>Python `np.vectorize`, `O(N²)` scans & OGR disk-seek loops |

---

## Executive Findings: High Intelligence via High Compute

1. **System-Prompt Budget Discipline (`100%` Compliance & Dual-Trigger Guards)**: Across all `15` XBoost `/x*` skills, YAML discovery descriptions average **`371.07 ± 20.14 chars`** (Median `374.0` chars, **`100.0%` within the `≤ 500` char `audit_engine.py` budget gate**) with **`100.0%` dual positive + negative (`Use when` / `Do NOT use for`) routing guards**, compared to `87.1%` dual-trigger coverage across `31` official cloud/enterprise skills.
2. **Context Noise Compression (`-96.73%` Scan Reduction)**: When briefing across multi-project repositories and the `609`-node Obsidian Second Brain (`1,752,358` tokens total), `/xbrief` (`Cap 8` Two-Pass) + `/xobsidian` (`2-Hop = 4` vault files) loads only **`57,366` tokens** (**`96.73%` noise reduction** / **`30.5×` compression**) in a median disk read time of **`1.49 ms`** (vs `54.94 ms` unbounded).
3. **System 1 `/xlaya` Triage (`144.12 ms` Median)**: Chunking and ranking `990` fence-safe (`≤ 1,200`-char) heading sections across `24` specs completes in **`144.12 ms`** (`Mean 144.85 ± 3.99 ms`, `6,869.3 chunks/sec`), cutting Pass-B reading tokens by **`99.33%`**.
4. **Deterministic Red-Team Defect Catch Rate (`100.0%` vs `0.0%`)**: Across `25` seeded security, Qt6/QGIS 4, research citation, doc-sync, and skill-packaging defects, the 10 CLI gates (`21,349` LOC) achieve **`25 / 25` (`100.0%` recall)** and **`100.0%` precision** (`0` false positives) in **`8.09 ms`**.
5. **Transparent Token Economics (Why XBoost Recommends `5×`–`20×` Subscriptions)**: While XBoost slashes *garbage file noise* by `96.73%`, it deliberately invests that freed context capacity into **deep multi-gate verification**. Across `1093` real prompt turns, a chained multi-skill XBoost turn executes **`91.19 steps`** (`3.45×` deeper than standard `26.46`-step turns), consuming **`96,597` uncached input tokens (`6.69×`)**, **`24,619` output tokens (`4.09×`)**, and **`4,582,058` KV-cache read tokens** per turn (`~40.69M` total tokens across a full `736`-step marathon session).
6. **3-Tier Compound Learning Playbooks (`4.0×` – `1,735.6×` Real-World Upstream Speedups)**: By distilling verified bug and bottleneck signatures via [`/xlearn`](../skills/xlearn/SKILL.md) into [`docs/COMPOUND_LEARNING_PLAYBOOK.md`](../docs/COMPOUND_LEARNING_PLAYBOOK.md) (`19 PAT-*`, `7 GOV-*`, `11 FALS-*` + 3 specialized domain playbooks), XBoost achieved **`4.0×` to `1,735.6×` measured wall-clock speedups** with **`100%` numerical equivalence** across **22 upstream open-source contributions** (`5 MERGED`, `9 OPEN PRs`, `4 OPEN Issues`, `4 Staged`).

---

## Experiment 1: Skill Discovery & Context Budget Audit (`N = 117` Installed Skills)

| Skill Cohort | Count | YAML Desc Chars (`Mean ± SD` / `Median`) | `≤ 500` Char Gate Pass | Dual Trigger Guard (`Use when` + `Do NOT use`) | Full `SKILL.md` Tokens (`Mean ± SD` / `Median`) | Bundled CLI Scripts (`LOC`) |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|
| **XBoost `v3.5.0` Suite (`/x*` Skills)** | `15` | **`371.07 ± 20.14`** (`374.0`) | **`100.0%`** | **`100.0%`** | `4,723 ± 2,102` (`3,867`) | **`10` (`21,349` LOC)** |
| **Official Cloud & Enterprise Vendor Skills** | `31` | `331.1 ± 63.41` (`324.0`) | `96.8%` | `87.1%` | `2,523 ± 1,689` (`2,468`) | `5` (`2,880` LOC) |
| **All Installed Host Skills Pool** | `117` | `324.53 ± 51.25` (`319.0`) | `99.1%` | `90.6%` | `2,211 ± 1,952` (`1,569`) | `60` (`40,171` LOC) |

---

## Experiment 2: Context Window Compression & 2-Hop Vault Isolation (`3` Warm-Ups + `30` Trials)

| Briefing Regime | Files Read | Lines Read | Context Tokens Loaded | Noise Reduction (`%` / Factor) | Disk Read Latency (`Median` / `Mean ± SD` / `P95`) |
|:---|:---:|:---:|:---:|:---:|:---:|
| **1. Unbounded Repo + Vault Crawl** | `889` | `75,561` | `1,752,358` tok | Baseline (`1.0×`) | `54.94 ms` (`54.63 ± 2.52 ms` / `P95: 58.26 ms`) |
| **2. `/xbrief` Repo-Only (`Cap 8` Two-Pass)** | **`8`** | **`1,158`** | **`52,761` tok** | **`-96.99%` (`33.2×`)** | **`1.19 ms`** (`1.36 ± 0.51 ms` / `P95: 2.13 ms`) |
| **3. `/xbrief /xobsidian` (`Cap 8` + `2-Hop` Vault)** | **`12`** (`8` Repo + `4` Vault) | **`1,327`** | **`57,366` tok** | **`-96.73%` (`30.5×`)** | **`1.49 ms`** (`1.56 ± 0.43 ms` / `P95: 2.35 ms`) |

---

## Experiment 3: `/xlaya` System 1 Section Shortlisting Speed (`3` Warm-Ups + `30` Trials)

| Metric | Measured Value |
|:---|:---|
| **Markdown Specifications Chunked** | `24` files (`990` fence-safe heading chunks `≤ 1,200` chars) |
| **Full Unchunked Corpus Size** | `149,323` tokens |
| **Top-5 Shortlisted Pass-B Size** | **`997` tokens (`-99.33%` token reduction)** |
| **Single-Pass Triage Latency (`N = 30`)** | **Median `144.12 ms`** (`Mean 144.85 ± 3.99 ms` • `IQR 2.97 ms` • `P95 153.25 ms`) |
| **Chunk Evaluation Throughput** | **`6,869.3` chunks / sec** (`deterministic-lexical-stdlib`) |

---

## Experiment 4: 25-Defect Red-Team Injection Suite (`3` Warm-Ups + `20` Trials)

| Defect Category (`5` Seeded Defects Each) | Prompt-Only Skills (No CLI Gate) | XBoost CLI Verification Gate | Defects Caught |
|:---|:---:|:---|:---:|
| **1. Security & Portability** (AWS/GH keys, hardcoded user path, `eval`, `shell=True`, `pickle`) | `0 / 5` | `xpublish/scripts/audit_engine.py` | **`5 / 5` (`100%`)** |
| **2. QGIS 4 / Qt6 & INI Packaging** (`Qt.AlignCenter`, `QDialog.Accepted`, `QMessageBox.Yes`, raw `%`, hook) | `0 / 5` | `xpublish/scripts/check_qt6.py` + `audit_engine.py` | **`5 / 5` (`100%`)** |
| **3. Deep-Research Evidence & Schema** (`[TBD]`, `example.com`, bare root URL, quota, year bounds) | `0 / 5` | `xdeep-research/scripts/verify_evidence.py` | **`5 / 5` (`100%`)** |
| **4. Doc Sync, Links, Zero-LaTeX & Mirrors** (2 broken links, inline LaTeX, deprecated term, SHA-256 drift) | `0 / 5` | `xsync/scripts/audit_workspace_docs.py` | **`5 / 5` (`100%`)** |
| **5. Skill Budget & Hygiene** (`>500` char YAML, naming, broken link, `__pycache__`, `.pyc` binary) | `0 / 5` | `audit_engine.py --platform skill` | **`5 / 5` (`100%`)** |
| **Total Recall / Precision / Latency (`N = 20`)** | **`0 / 25` (`0.0%`)** | **All 10 XBoost CLI Gates (`21,349` LOC)** | **`25 / 25` (`100.0%` Recall • `100.0%` Precision • Median `8.09 ms`)** |

---

## Experiment 5: Composable Workflow Ablation Matrix (`Level 0` → `Level 3`)

| Workflow Level | Command Chain | Briefing Scan Tokens | Vault Nodes Routed | Active CLI Gates | Seeded Defect Catch Rate | Avg Steps / Turn | Recommended Subscription Tier |
|:---|:---|:---:|:---:|:---:|:---:|:---:|:---|
| **Baseline 0: Unstructured Prompting (No Skills)** | `<raw prompt>` | `1,752,358` | `0` | `0` | **`0.0%`** | `26.5` | **Free / 1× Base Tier** |
| **Level 1: Single Core Solver** | `/xboost` | `52,761` | `0` | `2` | **`40.0%`** | `15.3` | **1× Pro / 5× Max Tier** |
| **Level 2: Repo-Briefed + Primary Probe + 2-Hop Vault** | `/xbrief /xdeep-research /xboost /xobsidian` | `57,366` | `609` | `4` | **`80.0%`** | `91.2` | **5× Max Tier (Claude Max 5× / Gemini 5×)** |
| **Level 3: Full 5-Stage Lifecycle + System 1 + 10 CLI Gates + /xlearn** | `/xbrief /xdeep-research /xboost /xultra /xlearn /xsync /xlaya + /xpublish` | `57,366` | `609` | `10` | **`100.0%`** | `736.4` | **20× Ultra Tier (Gemini Ultra 20× / Claude Max 20×)** |

---

## Experiment 6: Real Session Token Economics (`N = 450` Sessions / `1093` Prompt Turns)

### A. Per-Prompt Turn Token Telemetry (`Mean ± StdDev` & `Median [P25–P75]`)

| Execution Mode | Sample Size | Trajectory Depth (`Steps / Turn`) | Uncached New Input (`NewIn`) | KV-Cache Replay (`Cached Input`) | Internal `Thinking` | Model `Output` | **Total Processed / Turn** |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **1. Standard Turn (No `/x*` Skill)** | `706` turns | `26.5` *(Med `6`)* | `14,450` *(Med `1,430`)* | `1,459,358` *(Med `311,753`)* | `1,873` *(Med `649`)* | `6,025` *(Med `1,495`)* | **`1,481,705`** *(Med `323,668`)* |
| **2. Single `/x*` Skill Turn** | `112` turns | `15.3` *(Med `8`)* | `10,830` *(Med `4,316`)* | `951,791` *(Med `519,092`)* | `872` *(Med `434`)* | `3,345` *(Med `1,812`)* | **`966,837`** *(Med `521,402`)* |
| **3. Chained Multi-Skill `/x*` Turn** | `275` turns | **`91.2`** *(Med `48` • `3.45×`)* | **`96,597`** *(Med `68,260` • `6.69×`)* | **`4,582,058`** *(Med `2,166,131`)* | **`5,263`** *(Med `2,657`)* | **`24,619`** *(Med `11,634` • `4.09×`)* | **`4,708,537`** *(Med `2,297,560`)* |

### B. Full Multi-Turn Session Telemetry (`N = 450` Complete Sessions)

| Session Class | Sample Size | Steps / Session (`Mean` / `Median` / `P90`) | Uncached Input (`Mean` / `Median`) | KV-Cache Read (`Mean` / `Median`) | Thinking (`Mean` / `Median`) | Output (`Mean` / `Median`) | **Total Session Throughput (`Mean` / `Median` / `P90`)** |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **Standard Session (No `/x*`)** | `389` | `57.3` / `39` / `119` | `73,558` / `52,689` | `1.75M` / `0.81M` | `4,325` / `1,866` | `12,278` / `6,462` | **`1.84M`** / `0.90M` / `3.96M` |
| **Single-Skill XBoost Session** | `5` | `82.0` / `28` / `199` | `78,471` / `31,024` | `3.56M` / `0.51M` | `3,967` / `1,102` | `13,908` / `3,281` | **`3.65M`** / `0.55M` / `10.12M` |
| **Chained Multi-Skill XBoost Session** | `56` | **`736.4`** / `592` / `1722` | **`640,370`** / `586,207` | **`39.81M`** / `31.97M` | **`47,549`** / `32,558` | **`191,640`** / `149,836` | **`40.69M` (`22.06×`)** / `32.53M` / `93.50M` |

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
