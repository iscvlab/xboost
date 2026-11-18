---
name: xocr
description: >
  Fast PyMuPDF/booktabs/aligned table extractor, 6-gate table stitcher, CAD grid-bubble & callout graph parser, drawing diff, adaptive tiled OCR, A1..D4 sniper & 5-profile VLM engine (/xocr). Use when extracting PDFs, tables, or architectural drawings. Do NOT use for plain CSV/text or native DWG/DXF (/cad).
---

# XOCR Document, Table & Spatial Drawing Engine (`/xocr` v2.4.0)

High-throughput, zero-corruption PDF, table & architectural drawing extraction engine (`/xocr`, aliases `/ocr`, `/unlimited-ocr`) engineered for **zero-hang Stage 0 probing**, **5-profile CPU-safe execution (`nano`/`edge`/`workstation`/`max`)**, **faux-bold & Thai glyph fidelity**, **CAD grid-bubble & callout graphs (`v2.4.0`)**, **drawing revision diffs**, **6-gate multi-page table stitching**, and **canonical `A1..D4` tiled OCR + `<10 ms` ROI sniping**.

---

## 1. Speed × Regime-Aware Hybrid Architecture (`v2.4.0`)

```mermaid
%%{init: {'theme': 'neutral'}}%%
flowchart LR
    subgraph Canvas [" "]
        In["Input: PDF / Image"] --> S0["Stage 0 Zero-Hang Probe (<50 ms, get_images full=False)"]
        S0 --> Reg{"4-Regime Simplex + Platt + Split-Conformal"}
        Reg -->|"DIGITAL_TEXT_TABLE"| Fast["C++ PyMuPDF + Booktabs + Aligned Tables"]
        Reg -->|"VECTOR_CAD_DRAWING"| CAD["A1..D4 Spatial Index + Multi-Scale Views"]
        Reg -->|"RASTER_DRAWING_OR_MAP"| VLM{"5-Profile Gated OCR / VLM"}
        Reg -->|"HYBRID_COMPOSITE_DRAWING"| Hybrid["Aligned Sidebar Tables + Single-Composite Tile Views"]

        subgraph Profiles ["5 Hardware Profiles (--profile)"]
            P1["nano: Pure CPU PyMuPDF+Pillow (zero torch)"]
            P2["edge: CPU + RapidOCR/Tesseract (zero torch)"]
            P3["workstation / max: GPU VLMs (Typhoon v1.5 / Unlimited-OCR-2)"]
        end

        Fast --> Out["Outputs: .md + .csv + .json + spatial_index.json + view PNGs"]
        CAD --> Out
        Hybrid --> Out
        VLM --> Out
    end
    classDef default fill:#ffffff,stroke:#475569,color:#0f172a,stroke-width:1px
    style Canvas fill:#ffffff,stroke:#cbd5e1,stroke-width:1.5px,color:#0f172a
    style Profiles fill:#f8fafc,stroke:#94a3b8,color:#0f172a
```

### Core Engineering Guarantees
1. **5 Hardware Profiles & Zero-PyTorch CPU Guarantees**:
   - `--profile auto|nano|edge|workstation|max` resolves execution caps without loading PyTorch eagerly.
   - Under `nano` and `edge`, `torch` is **never imported** (`"torch" not in sys.modules`): `nano` runs purely on PyMuPDF + Pillow + stdlib; `edge` permits local CPU OCR (`rapidocr_onnxruntime` / `tesseract`) if available. `workstation` and `max` enable CUDA VLMs (`Typhoon-OCR v1.5`, `Unlimited-OCR-2`) lazily only when OCR fallback triggers.
2. **Stage 0 Zero-Hang Multi-Layer Probing (`_fast_page_image_metrics`)**:
   - Probes image counts and pixel bounds exclusively via `page.get_images(full=False)` and single-pass `TextPage` (`TEXTFLAGS_TEXT`).
   - Whenever `image_count > 10`, (`image_count > 4` and `max_img_px >= 4,000,000`), or `sum_img_px >= 40,000,000`, `page.get_image_info()` and `page.get_image_rects()` (and dense `get_drawings()` when `image_count > 20` covers the canvas) are skipped, eliminating ~190 s stalls on 100+ layer composite master plans.
3. **4-Regime 8D Simplex + Platt + Split-Conformal Classifier + `.SHX` Detector**:
   - Classifies each page into `DIGITAL_TEXT_TABLE`, `VECTOR_CAD_DRAWING`, `RASTER_DRAWING_OR_MAP`, or `HYBRID_COMPOSITE_DRAWING` using calibrated 8D L1-simplex weights (`w[7] <= 0`), per-regime Platt `(T, b)` (`test accuracy = 100.0%`, `test ece = 0.0350`, `conformal_coverage = 95.0%`, `conformal_q_hat = 0.2046` across `54` external + `72` synthetic docs via `benchmarks/run_xocr_evolution.py`).
   - `_fast_drawing_metrics` detects exploded `.SHX` stroke-font CAD sheets (`vector_drawing_count >= 400`, `short_stroke_ratio >= 0.45`, `< 35` clean chars) and sets `exploded_glyphs_suspected=True`, `needs_ocr=True`, `needs_vision=True` while preserving `O(1)` bailout on heavy rasters.
4. **Faux-Bold De-Ghosting, Orientation-Aware Callouts, Aligned & 6-Gate Stitched Multi-Page Tables**:
   - `_extract_text_and_dict_fast` strips micro-shifted/duplicate faux-bold spans (`0 <= |dx|, |dy| <= 2.0`, fixing `GG::ParkingParking` → `G : Parking`) while keeping normal non-ghost pages untouched.
   - `_extract_clean_text_atoms` quantizes `line["dir"]` vectors and projects span anchors onto tangential/normal axes `(t, n)` so `90°`/`270°`/`45°` callouts stay ordered without cross-merging parallel strings.
   - Combines `page.find_tables()` grid (`return_meta=True` pre-pruning bounds) + 3-rule `booktabs` (`\toprule`/`\midrule`/`\bottomrule`) with `_extract_aligned_block_tables()`, `_dedup_merge_page_tables`, and `stitch_multipage_tables()` (6-gate cascade with terminal-total & distinct-header `A_neg` shields, bridge carry-row stripping, blank-column recovery, X-IoU `>= 0.80` / center drift `<= 0.025`, 3+ page folding, and disk CSV reconciliation).
5. **Deterministic CAD Grid-Bubble Axes, Cross-Sheet Callout Graph, Drawing Revision Diff & `<10 ms` ROI Sniper**:
   - `extract_grid_axes` + `resolve_grid_ref` parse perimeter circular/octagonal bubbles (`A..Z`, `AA..BZ`, `1..99`, `2.1`, `3a`) with natural sort, top-down/bottom-up Y support, dual `secondary_axes`, keynote/bisector rejection, and bracketed grid lookup (`None` outside `[axis_min - 0.5*Δ_med, axis_max + 0.5*Δ_med]`).
   - `extract_sheet_callouts` + `build_callout_graph` extract `primary_sheet_id`, detail/section/elevation/bisected-circle callouts, and revision clouds/deltas (`Δ1`, `REV 2`, `ADDENDUM`), while `diff_pdf_drawings` (`--diff-with <OLD_PDF>`) matches sheets by `primary_sheet_id`, diffs table cells (`numeric_delta`), tolerance-matches vector atoms (`<= 0.015` norm / `<= 2.0 pt` jitter = `0` diff), and runs `72 DPI` `4x4` tile `MAD > 0.012`.
   - `compute_unexplained_canvas_bbox` + `tile_and_stitch_canvas` tile large composite sheets (`3x2` / `2x2`), `--sniper-query` (`rank_spatial_rois`, `+2.5` grid/callout boost) ranks top-5 `A1..D4` ROIs in `<10 ms`, and `--render-mode` emits PNG views `<= 4.5 MiB`.
6. **Zero-Mojibake Thai/English Normalization, Thai Script Guard & 4-Tier VLM Fallback**:
   - Remaps Windows/Adobe Thai Private Use Area codepoints (`U+F700..U+F71A`), repairs decomposed Sara Am (`\u0e4d([\u0e48-\u0e4b]?)\u0e32` → `\1\u0e33`), guards CPU `edge` runs from RapidOCR Latin gibberish (`has_thai_hint=True` checks Tesseract `tha` first or returns `skipped_thai_guard`), and dispatches SGLang / `Typhoon-OCR v1.5` / `Unlimited-OCR-2` / `EasyOCR` per `--profile`.

---

## 2. Deterministic CLI Execution

Run [`scripts/ocr_runner.py`](scripts/ocr_runner.py) relative to this skill's directory (`<SKILL_DIR>`):

**macOS / Linux**:
```bash
python3 "<SKILL_DIR>/scripts/ocr_runner.py" "<path_to_pdf_or_image>" \
  --output "<output_dir>" \
  --mode auto \
  --profile nano \
  --drawing-index \
  --render-mode overview
```

**Windows (PowerShell)**:
```powershell
python "<SKILL_DIR>/scripts/ocr_runner.py" "<path_to_pdf_or_image>" `
  --output "<output_dir>" `
  --mode auto `
  --profile edge `
  --pages "1-10" `
  --drawing-index
```

### CLI Options
* `<input_path>` or `--input`, `-i <path>`: Target PDF (`.pdf`) or image (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`, `.tif`, `.tiff`).
* `--version`: Print `xocr 2.4.0` and exit `0`.
* `--self-test`: Run deterministic synthetic validation (PUA/Sara-Am cleanup, regime invariants, spatial grid, v2.4 Seam A checks, PNG byte cap, and `"torch" not in sys.modules` under `nano`/`edge`) and exit `0`.
* `--output`, `-o <dir>` (default: `./ocr_output`): Destination directory for all extracted artifacts.
* `--profile auto|nano|edge|workstation|max` (default: `auto`): Hardware execution cap (`nano`/`edge` stay CPU-only with zero PyTorch imports).
* `--genomes-file <path>`: Optional override path to calibrated `xocr_genomes.json`.
* `--mode auto|pdf|vlm` (default: `auto`): `auto` extracts clean pages via C++ and routes `needs_ocr=True` pages per profile; `pdf` stays strictly vector/block-only; `vlm` forces rasterization when allowed by profile.
* `--vlm-backend auto|typhoon-2b|typhoon-3b-qat|typhoon-3b-4bit|unlimited-ocr|sglang` (default: `auto`): Selects VLM backend when profile allows GPU/VLM.
* `--drawing-index`: Emit `spatial_index.json` containing canonical `A1..D4` tiles, `grid_axes`, `primary_sheet_id`, `callouts`, `revision_deltas`, `callout_graph`, and `grid_ref`-tagged blocks/tables.
* `--diff-with <OLD_PDF>`: Compare input PDF revision against `<OLD_PDF>`, emit `drawing_diff.json`, and append a `## Drawing Revision Diff` summary to `extracted_document.md`.
* `--no-stitch-tables`: Disable 6-gate cross-page continuation table stitching (keeps per-page fragment CSVs).
* `--sniper-query "<text>"`: Rank top-5 `A1..D4` spatial ROIs in `<10 ms` (optionally combine with `--xlaya-bridge`) and emit `sniper_rois` in JSON output and `ocr_manifest.json`.
* `--xlaya-bridge`: Fuse optional `xlaya` BM25 lexical scoring inside `--sniper-query` ranking.
* `--render-mode overview|crop|around_text|tile|quadrants`: Render multi-scale inspection PNGs (`<= 4.5 MiB` each) using `--bbox nx0,ny0,nx1,ny1`, `--query TEXT`, `--tile CELL`, `--tile-grid CxR` (default `4x4`), and `--no-grid-overlay`.
* `--pages "<range>"`: Surgically extract only specific 1-based pages (e.g. `"1-5,8"`).
* `--workers <int>` (default: `min(8, cpu_count)`), `--dpi <int>` (default: `300`), `--langs "<codes>"` (default: `"th,en"`).

---

## 3. Verifiable Output Artifacts

Every run emits pure JSON telemetry on `stdout` and writes deterministic artifacts to `--output`:
* `extracted_document.md`: Reading-order Markdown (`## Page N`) with **inline GitHub Flavored Markdown tables** and optional `## Drawing Revision Diff`.
* `extracted_text.txt`: Plain page-delimited text (`--- PAGE N ---`).
* `table_p{page}_{table_id}.csv`: UTF-8 with BOM (`utf-8-sig`) RFC-4180 CSV tables (stitched multi-page tables overwrite `table_p{start_page}_{id}.csv` and remove superseded continuation fragment CSVs unless `--no-stitch-tables` is passed).
* `ocr_manifest.json`: Per-page audit telemetry (`page`, `regime`, `regime_confidence`, `conformal_abstain`, `char_count`, `table_count`, `table_merge_events`, `garble_ratio`, `image_area_ratio`, `exploded_glyphs_suspected`, `short_stroke_ratio`, `tiled_canvas`, `ocr_warning`, `stage0_ms`, `needs_ocr`, `needs_vision`, `engine`, `elapsed_ms`, `profile`, `sniper_rois`, `drawing_diff_summary`).
* `spatial_index.json` *(when `--drawing-index` is set)*: Canonical `A1..D4` spatial CAD index with `grid_axes`, `primary_sheet_id`, `callouts`, `revision_deltas`, `callout_graph`, `tiles`, `grid_ref`-tagged `blocks`/`tables`, and `titleblock_hints`.
* `drawing_diff.json` *(when `--diff-with` is set)*: Sheet-matched vector atom, callout/revision, schedule cell (`numeric_delta`), and `72 DPI` `4x4` tile MAD diff report.
* `view_p{page}_*.png` *(when `--render-mode` is set)*: Multi-scale PNG views guaranteed `<= 4.5 MiB` via adaptive resolution control and single-composite caching on heavy composite sheets.

---

## 4. Automatic Ecosystem Routing (`/xdeep-research`, `/xbrief`, `/xplan`, `/xlaya`, `/xboost`, `/xlearn`, `/xobsidian`, `/xultra`)

Other XBoost `/x*` skills automatically invoke [`scripts/ocr_runner.py`](scripts/ocr_runner.py) whenever they encounter a `.pdf` or raster image table - even when the user does not explicitly type `/xocr`:

| Chained / Calling Skill | Automatic `/xocr` Ingestion & Verification Handoff |
|:---|:---|
| **`/xdeep-research`** | **Primary-Source PDF & Table Harvester (Law 1)**: Automatically runs `ocr_runner.py` (with `--pages` when targeted) on technical PDFs, regulatory filings, and academic papers, citing exact rows from `table_p*.csv` and `extracted_document.md` with `ocr_manifest.json` receipts. |
| **`/xbrief`** | **PDF Specification Briefing**: When a user-pinned or canonical workspace specification exists only as a `.pdf` or image plate, runs `ocr_runner.py` first to load structural headings (`## Page N`) and tables into the Briefing Table. |
| **`/xplan`** | **PDF & Image Specification Planning**: Extracts `extracted_document.md` and `table_p*.csv` from PDF/image specs in Phase 1 before authoring `implementation_plan.md`. |
| **`/xlaya`** | **Sub-Second Section Shortlisting**: Passes `extracted_document.md` headings into `/xlaya` (`shortlist` / `score`) to pinpoint high-signal pages in milliseconds before LLM reading. |
| **`/xboost`** | **Zero-Error Quantitative Verification**: Checks `ocr_manifest.json` (`garble_ratio == 0.0`, `tables_extracted > 0`) and cross-verifies CSV column sums (`df.sum()`) against printed "Total" rows. |
| **`/xlearn`** | **Vision & OCR Pattern Ratchet (`Tier 1B`)**: Distills verified vector `booktabs`, Thai PUA/Sara-Am glyph normalization, and VLM HTML table extraction patterns into `COMPOUND_LEARNING_PLAYBOOK.md` (`Tier 1B`). |
| **`/xobsidian`** | **Clean Second-Brain Distillation**: Runs `ocr_runner.py` before distilling PDF papers or technical reports into atomic vault notes so `0%` glyph/encoding corruption or collapsed tables enter `VAULT_ROOT`. |
| **`/xultra`** | **Sharded Multi-PDF / Page-Range Swarm (`Pointer-Not-Payload`)**: Shards massive PDF corpora or multi-hundred-page volumes across workers by **disjoint PDF files** or **disjoint `--pages` ranges** (`--pages 1-50`, `--pages 51-100`) writing to isolated `--output` folders and returning Compact Pointer Receipts (`ocr_manifest.json` + `table_p*.csv` paths). |
