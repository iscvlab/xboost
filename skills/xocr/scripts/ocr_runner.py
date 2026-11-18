#!/usr/bin/env python3
"""High-speed, zero-corruption PDF, CAD Drawing & Image OCR engine for /xocr (v2.4.0).

Features:
1. 5-Profile Hardware Architecture (`--profile auto|nano|edge|workstation|max`)
   with strict zero-PyTorch lazy imports under `nano` and `edge`.
2. Zero-Hang Stage 0 Image Probe (`page.get_images(full=False)`) + 4-Regime
   8D Simplex + Platt + Split-Conformal Page Classifier (`xocr_genomes.json`)
   with exploded `.SHX` stroke-CAD detection (`short_stroke_ratio`).
3. Single-pass C++ PyMuPDF (`fitz`) coordinate-sorted text (`sort=True`) with
   surgical faux-bold de-ghosting, orientation-aware callout assembly (`0/90/270/angle`),
   Two-Stage Grid + LaTeX `booktabs` table surgery, Borderless Coordinate-Aligned
   Table Recovery (`_extract_aligned_block_tables`), and 6-Gate Multi-Page Table
   Continuation Stitching (`stitch_multipage_tables`).
4. Deterministic Grid-Bubble Axis Parser (`extract_grid_axes` / `resolve_grid_ref`),
   Cross-Sheet Callout Graph (`extract_sheet_callouts` / `build_callout_graph`),
   Drawing Revision Diff (`diff_pdf_drawings`), Canonical `A1..D4` Spatial CAD Index
   (`extract_spatial_cad_index`), `< 10 ms` ROI Sniper (`rank_spatial_rois`),
   adaptive tiling (`tile_and_stitch_canvas`), and Multi-Scale View Renderer (`render_drawing_view`).
5. Deterministic Thai/English glyph normalization (`U+F700..U+F71A` PUA,
   decomposed Sara Am, zero-width stripping), Thai CPU script guard, and
   4-Tier VLM/CPU OCR ladder (`SGLang`, `Typhoon-OCR v1.5`, `Unlimited-OCR-2`,
   `RapidOCR`/`EasyOCR`/`pytesseract`).
"""

import argparse
from collections import Counter, OrderedDict
import contextlib
import copy
import csv
import difflib
import gc
import html.parser
import importlib.util
import io
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor

__version__ = "2.4.0"

sys.dont_write_bytecode = True
warnings.filterwarnings("ignore", category=UserWarning)

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

XOCR_PROFILES = ("auto", "nano", "edge", "workstation", "max")
XOCR_REGIMES = (
    "DIGITAL_TEXT_TABLE",
    "VECTOR_CAD_DRAWING",
    "RASTER_DRAWING_OR_MAP",
    "HYBRID_COMPOSITE_DRAWING",
)
XOCR_FEATURE_NAMES = (
    "garble_cid_density",
    "vector_drawing_density",
    "max_raster_resolution",
    "sheet_aspect_scale",
    "unexplained_canvas_ratio",
    "callout_spatial_entropy",
    "table_rule_density",
    "text_sufficiency_penalty",
)
XOCR_NEG_INDICES = frozenset({7})

SEAM_A_SYMBOLS = (
    "__version__",
    "XOCR_PROFILES",
    "XOCR_REGIMES",
    "XOCR_FEATURE_NAMES",
    "DEFAULT_XOCR_GENOMES",
    "normalize_text",
    "normalize_thai_text",
    "resolve_hardware_profile",
    "evaluate_page_quality",
    "load_xocr_genomes",
    "classify_page_regime",
    "extract_spatial_cad_index",
    "render_drawing_view",
    "extract_tables_from_page",
    "extract_html_tables_from_text",
    "ocr_image_local",
    "run_vlm_engine",
    "extract_pdf",
    "extract_standalone_image",
    "run_self_test",
    "_fast_page_image_metrics",
    "_fast_drawing_metrics",
    "_extract_aligned_block_tables",
    "_get_or_build_composite",
    "compute_unexplained_canvas_bbox",
    "tile_and_stitch_canvas",
    "rank_spatial_rois",
    "_extract_text_and_dict_fast",
    "_extract_clean_text_atoms",
    "extract_grid_axes",
    "resolve_grid_ref",
    "extract_sheet_callouts",
    "build_callout_graph",
    "stitch_multipage_tables",
    "diff_pdf_drawings",
)

DEFAULT_XOCR_GENOMES = {
    "version": "2.3.0",
    "feature_names": list(XOCR_FEATURE_NAMES),
    "regimes": list(XOCR_REGIMES),
    "alpha": 0.10,
    "conformal_q_hat": 0.2046,
    "weights": {
        "DIGITAL_TEXT_TABLE": [0.0013, -0.0141, -0.0861, -0.2436, -0.0903, 0.1815, 0.0086, -0.3745],
        "VECTOR_CAD_DRAWING": [-0.0154, -0.0195, -0.3885, 0.3138, 0.0753, 0.1807, -0.0015, -0.0053],
        "RASTER_DRAWING_OR_MAP": [0.0687, -0.0341, 0.2492, -0.0663, 0.1797, -0.2847, -0.038, -0.0793],
        "HYBRID_COMPOSITE_DRAWING": [-0.0385, -0.2027, 0.0435, 0.3146, 0.0814, -0.0659, -0.0193, -0.2341],
    },
    "platt": {
        "DIGITAL_TEXT_TABLE": {"T": 19.4, "b": 4.0},
        "VECTOR_CAD_DRAWING": {"T": 18.125, "b": -8.0},
        "RASTER_DRAWING_OR_MAP": {"T": 25.8, "b": -7.85},
        "HYBRID_COMPOSITE_DRAWING": {"T": 32.0, "b": -6.4},
    },
}

# Legacy Windows / Adobe Thai Private Use Area (PUA) glyph remapping table
THAI_PUA_MAP = {
    "\uf700": "\u0e10",  # Tho Than (baseless)
    "\uf701": "\u0e34",  # Sara I (shifted left)
    "\uf702": "\u0e35",  # Sara Ii (shifted left)
    "\uf703": "\u0e36",  # Sara Ue (shifted left)
    "\uf704": "\u0e37",  # Sara Uee (shifted left)
    "\uf705": "\u0e48",  # Mai Ek (low left)
    "\uf706": "\u0e49",  # Mai Tho (low left)
    "\uf707": "\u0e4a",  # Mai Tri (low left)
    "\uf708": "\u0e4b",  # Mai Chattawa (low left)
    "\uf709": "\u0e4c",  # Thanthakhat (low left)
    "\uf70a": "\u0e48",  # Mai Ek (low)
    "\uf70b": "\u0e49",  # Mai Tho (low)
    "\uf70c": "\u0e4a",  # Mai Tri (low)
    "\uf70d": "\u0e4b",  # Mai Chattawa (low)
    "\uf70e": "\u0e4c",  # Thanthakhat (low)
    "\uf70f": "\u0e0d",  # Yo Ying (baseless)
    "\uf710": "\u0e31",  # Mai Han-Akat (shifted left)
    "\uf711": "\u0e4d",  # Nikhahit (shifted left)
    "\uf712": "\u0e47",  # Maitaikhu (shifted left)
    "\uf713": "\u0e48",  # Mai Ek (high left)
    "\uf714": "\u0e49",  # Mai Tho (high left)
    "\uf715": "\u0e4a",  # Mai Tri (high left)
    "\uf716": "\u0e4b",  # Mai Chattawa (high left)
    "\uf717": "\u0e4c",  # Thanthakhat (high left)
    "\uf718": "\u0e38",  # Sara U (low)
    "\uf719": "\u0e39",  # Sara Uu (low)
    "\uf71a": "\u0e3a",  # Phinthu (low)
}
THAI_PUA_TRANS = str.maketrans(THAI_PUA_MAP)
CID_PATTERN = re.compile(r"\(cid:\d+\)")
SARA_AM_PATTERN = re.compile(r"\u0e4d([\u0e48-\u0e4b]?)\u0e32")
NUMERIC_CELL_RE = re.compile(r"^\s*[-+]?[\d,]+(?:\.\d+)?%?\s*$")
SHEET_ID_RE = re.compile(r"\b([A-Z]{1,3}-\d{1,4}(?:\.\d+)?)\b")
LEGEND_LINE_RE = re.compile(
    r"^(?:[A-Z0-9]{1,3}\s*[:\-]|LEGEND|KEY\b|NOTE|สัญลักษณ์|หมายเหตุ|คำอธิบาย)",
    re.IGNORECASE,
)
GRID_LABEL_RE = re.compile(
    r"^(?:[A-Z](?:[.'\u2032]?[0-9]{1,2}|[a-z'\u2032])?|[AB][A-Z]|"
    r"[1-9][0-9]?(?:\.[0-9]{1,2}|[a-zA-Z'\u2032])?)$"
)
DETAIL_SLASH_CALLOUT_RE = re.compile(
    r"(?:(DETAIL|DTL|SEC|SECT|SECTION|ELEV|EL)\.?\s*(?:NO\.?\s*)?)?"
    r"\b([A-Z0-9]{1,4})\s*/\s*([A-Z]{1,3}-\d{1,4}(?:\.\d+)?)\b",
    re.IGNORECASE,
)
DETAIL_ON_SHEET_RE = re.compile(
    r"\b(DETAIL|DTL|SEC|SECT|SECTION|ELEV|EL)\.?\s+(?:ON\s+)?(?:SHT\.?|SHEET|DWG\.?)\s*"
    r"([A-Z]{1,3}-\d{1,4}(?:\.\d+)?)\b",
    re.IGNORECASE,
)
SEE_SHEET_CALLOUT_RE = re.compile(
    r"\b(?:SEE|REF\.?|REFER\s+TO)\s+(?:(?:SHT\.?|SHEET|DWG\.?)\s*)?"
    r"([A-Z]{1,3}-\d{1,4}(?:\.\d+)?)\b",
    re.IGNORECASE,
)
REV_MARKER_RE = re.compile(
    r"(?:[\u0394\u2206\u25b3\u25b2]\s*([A-Z0-9]{1,4})\b|"
    r"\b(?:REV(?:ISION)?\.?\s*[#:\-]?\s*([A-Z0-9]{1,4})|"
    r"ADDENDUM\s*[#:\-]?\s*([A-Z0-9]{1,4})|"
    r"ASI[-\s]?(\d{1,4}))\b)",
    re.IGNORECASE,
)
TERMINAL_TOTAL_RE = re.compile(
    r"\b(?:grand\s+total|net\s+total|total\s+bid|final\s+total|overall\s+total)\b|"
    r"รวมทั้งสิ้น|รวมเป็นเงินทั้งสิ้น|รวมสุทธิ",
    re.IGNORECASE,
)
BRIDGE_CARRY_RE = re.compile(
    r"\b(?:carried\s+forward|brought\s+forward|sub[\s\-]?total|page\s+total|c/f|b/f)\b|"
    r"ยอดยกไป|ยอดยกมา|รวมย่อย",
    re.IGNORECASE,
)
CONT_SIGNAL_RE = re.compile(
    r"(?:\(\s*cont(?:inued)?\.?\s*\)|\bcont(?:inued)?\.?\b(?:\s+from|\s+on)?|"
    r"\(\s*ต่อ\s*\)|(?:^|\s)ต่อ(?:\s*$|\s*\)))",
    re.IGNORECASE,
)

_COMPOSITE_CACHE_LOCK = threading.Lock()
_COMPOSITE_CACHE = OrderedDict()
_MAX_COMPOSITE_CACHE = 2
_RAPIDOCR_READER = None
_EASYOCR_READERS = {}


def non_ws_count(text):
    """Return count of non-whitespace characters in text."""
    return len(re.sub(r"\s+", "", text or ""))


def normalize_text(raw_text):
    """Normalize Thai PUA codepoints, Sara Am, and zero-width chars."""
    if not raw_text:
        return ""
    text = raw_text.translate(THAI_PUA_TRANS)
    # Normalize decomposed Nikhahit + optional tone mark + Sara Aa -> Sara Am
    text = SARA_AM_PATTERN.sub("\\1\u0e33", text)
    # Remove zero-width space / BOM artifacts inside text streams
    text = text.replace("\u200b", "").replace("\ufeff", "")
    return text


normalize_thai_text = normalize_text


def _detect_gpu_vram_gb():
    """Probe NVIDIA VRAM via nvidia-smi without importing torch."""
    smi = shutil.which("nvidia-smi")
    if not smi:
        return 0, 0.0, 0.0
    try:
        proc = subprocess.run(
            [smi, "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=2.5,
            check=False,
        )
        if proc.returncode != 0:
            return 0, 0.0, 0.0
        vals = []
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if line:
                vals.append(float(line) / 1024.0)
        if not vals:
            return 0, 0.0, 0.0
        return len(vals), round(vals[0], 2), round(sum(vals), 2)
    except Exception:  # nosec B110
        return 0, 0.0, 0.0


def _has_module_available(mod_name):
    """Safely check module presence including mocked sys.modules entries without __spec__."""
    if mod_name in sys.modules:
        return sys.modules[mod_name] is not None
    try:
        return importlib.util.find_spec(mod_name) is not None
    except (ValueError, ImportError):
        return False


def resolve_hardware_profile(profile="auto"):
    """Resolve hardware execution profile without importing PyTorch under nano/edge."""
    raw = (profile or "auto").strip().lower()
    if raw == "auto":
        env_p = os.environ.get("XOCR_PROFILE", "").strip().lower()
        eff = env_p if env_p else "auto"
    else:
        eff = raw

    if eff not in XOCR_PROFILES:
        raise ValueError(
            f"Unsupported profile {profile!r}; expected one of {list(XOCR_PROFILES)}."
        )

    has_rapidocr = _has_module_available("rapidocr_onnxruntime")
    has_tesseract = bool(
        _has_module_available("pytesseract")
        and shutil.which("tesseract")
    )

    if eff == "nano":
        return {
            "profile": "nano",
            "requested_profile": raw,
            "allow_torch": False,
            "allow_vlm": False,
            "allow_local_cpu_ocr": False,
            "allow_easyocr": False,
            "has_rapidocr": False,
            "has_tesseract": False,
            "has_cpu_ocr": False,
            "device": "cpu",
            "cuda_device_count": 0,
            "vram_single_gb": 0.0,
            "vram_cluster_gb": 0.0,
            "max_composite_px": 5400,
            "max_bytes": 4_500_000,
        }

    if eff == "edge":
        return {
            "profile": "edge",
            "requested_profile": raw,
            "allow_torch": False,
            "allow_vlm": False,
            "allow_local_cpu_ocr": True,
            "allow_easyocr": False,
            "has_rapidocr": has_rapidocr,
            "has_tesseract": has_tesseract,
            "has_cpu_ocr": bool(has_rapidocr or has_tesseract),
            "device": "cpu",
            "cuda_device_count": 0,
            "vram_single_gb": 0.0,
            "vram_cluster_gb": 0.0,
            "max_composite_px": 6400,
            "max_bytes": 4_500_000,
        }

    has_torch_spec = importlib.util.find_spec("torch") is not None
    cuda_cnt, vram_single, vram_cluster = (
        _detect_gpu_vram_gb() if has_torch_spec else (0, 0.0, 0.0)
    )
    is_mps_host = sys.platform == "darwin" and has_torch_spec

    if eff == "auto":
        if has_torch_spec and cuda_cnt > 0 and (vram_cluster >= 48.0 or vram_single >= 22.0):
            res_prof = "max"
        elif has_torch_spec and ((cuda_cnt > 0 and vram_single >= 4.0) or is_mps_host):
            res_prof = "workstation"
        elif has_rapidocr or has_tesseract:
            res_prof = "edge"
        else:
            res_prof = "nano"
        if res_prof in ("nano", "edge"):
            return resolve_hardware_profile(res_prof)
    else:
        res_prof = eff

    device = "cuda" if cuda_cnt > 0 else ("mps" if is_mps_host else "cpu")
    return {
        "profile": res_prof,
        "requested_profile": raw,
        "allow_torch": True,
        "allow_vlm": True,
        "allow_local_cpu_ocr": True,
        "allow_easyocr": True,
        "has_rapidocr": has_rapidocr,
        "has_tesseract": has_tesseract,
        "has_cpu_ocr": True,
        "device": device,
        "cuda_device_count": cuda_cnt,
        "vram_single_gb": vram_single,
        "vram_cluster_gb": vram_cluster,
        "max_composite_px": 10200 if res_prof == "max" else 8800,
        "max_bytes": 4_500_000,
    }


def _fast_page_image_metrics(page):
    """Inspect embedded image metadata in O(N_imgs) using get_images(full=False).

    Guards against PyMuPDF's multi-minute stream decompression hang when a page
    has > 10 images, (> 4 images with max_img_px >= 4M px), or sum_img_px >= 40M px
    by never invoking page.get_image_info() or page.get_image_rects().
    """
    page_w = max(1.0, float(abs(page.rect.width)))
    page_h = max(1.0, float(abs(page.rect.height)))
    page_area = max(1.0, page_w * page_h)

    try:
        imgs = page.get_images(full=False) or []
    except Exception:  # nosec B110
        imgs = []

    image_count = len(imgs)
    if image_count == 0:
        return {
            "image_count": 0,
            "max_img_w": 0,
            "max_img_h": 0,
            "max_img_px": 0,
            "sum_img_px": 0,
            "area_proxy": 0.0,
            "image_area_ratio": 0.0,
            "skipped_image_info": False,
        }

    max_img_w = 0
    max_img_h = 0
    max_img_px = 0
    sum_img_px = 0
    for im in imgs:
        try:
            w = int(im[2]) if len(im) > 2 else 0
            h = int(im[3]) if len(im) > 3 else 0
        except (TypeError, ValueError):
            w, h = 0, 0
        px = max(0, w) * max(0, h)
        sum_img_px += px
        if px >= max_img_px:
            max_img_px = px
            max_img_w = max(0, w)
            max_img_h = max(0, h)

    # Conservative 150-DPI baseline pixel-to-point conversion proxy
    area_proxy = round(
        min(1.0, sum_img_px / max(1.0, page_area * ((150.0 / 72.0) ** 2))),
        4,
    )

    if image_count > 10 or (image_count > 4 and max_img_px >= 4_000_000) or sum_img_px >= 40_000_000:
        return {
            "image_count": image_count,
            "max_img_w": max_img_w,
            "max_img_h": max_img_h,
            "max_img_px": max_img_px,
            "sum_img_px": sum_img_px,
            "area_proxy": area_proxy,
            "image_area_ratio": area_proxy,
            "skipped_image_info": True,
        }

    image_area_ratio = area_proxy
    try:
        img_infos = page.get_image_info() or []
        max_img_area = 0.0
        for info in img_infos:
            bbox = info.get("bbox")
            if bbox and len(bbox) == 4:
                area = max(0.0, (bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))
                if area > max_img_area:
                    max_img_area = area
        if img_infos:
            image_area_ratio = round(min(1.0, max_img_area / page_area), 4)
    except Exception:  # nosec B110
        pass

    return {
        "image_count": image_count,
        "max_img_w": max_img_w,
        "max_img_h": max_img_h,
        "max_img_px": max_img_px,
        "sum_img_px": sum_img_px,
        "area_proxy": area_proxy,
        "image_area_ratio": image_area_ratio,
        "skipped_image_info": False,
    }


def evaluate_page_quality(raw_text, page):
    """Compute text quality metrics and decide whether a page needs OCR."""
    cid_matches = CID_PATTERN.findall(raw_text or "")
    cid_count = len(cid_matches)
    rep_count = (raw_text or "").count("\ufffd")
    cleaned = CID_PATTERN.sub("", normalize_text(raw_text or "")).strip()
    non_ws_len = non_ws_count(cleaned)
    total_len = max(1, len(raw_text or ""))
    garble_ratio = round((cid_count * 6 + rep_count) / total_len, 4)

    img_metrics = _fast_page_image_metrics(page)
    image_count = img_metrics["image_count"]
    image_area_ratio = img_metrics["image_area_ratio"]

    needs_ocr = (
        non_ws_len < 25
        or garble_ratio > 0.05
        or (image_count > 0 and non_ws_len < 60)
        or (image_area_ratio >= 0.45 and non_ws_len < 250)
    )
    return {
        "clean_text": cleaned,
        "char_count": non_ws_len,
        "cid_count": cid_count,
        "replacement_count": rep_count,
        "garble_ratio": garble_ratio,
        "image_count": image_count,
        "image_area_ratio": image_area_ratio,
        "image_metrics": img_metrics,
        "needs_ocr": needs_ocr,
    }


def load_xocr_genomes(genomes_file=None):
    """Load calibrated xocr_genomes.json with explicit-override validation."""
    if genomes_file:
        explicit = os.path.abspath(str(genomes_file))
        if not os.path.isfile(explicit):
            raise FileNotFoundError(f"Genomes file not found: {explicit}")
        try:
            with open(explicit, "r", encoding="utf-8") as fh:
                data = json.load(fh)
        except Exception as exc:
            raise ValueError(f"Invalid JSON in genomes file {explicit}: {exc}") from exc
        if not (
            isinstance(data, dict)
            and isinstance(data.get("weights"), dict)
            and isinstance(data.get("platt"), dict)
            and all(r in data["weights"] for r in XOCR_REGIMES)
        ):
            raise ValueError(f"Invalid xocr genomes schema in {explicit}")
        data.setdefault("source_path", explicit)
        return data

    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent_1 = os.path.dirname(script_dir)
    parent_2 = os.path.dirname(parent_1)
    parent_3 = os.path.dirname(parent_2)
    candidates = [
        os.path.join(script_dir, "resources", "xocr_genomes.json"),
        os.path.join(parent_1, "resources", "xocr_genomes.json"),
        os.path.join(parent_2, "resources", "xocr_genomes.json"),
        os.path.join(parent_3, "resources", "xocr_genomes.json"),
    ]
    for cand in candidates:
        if cand and os.path.isfile(cand):
            try:
                with open(cand, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                if (
                    isinstance(data, dict)
                    and isinstance(data.get("weights"), dict)
                    and isinstance(data.get("platt"), dict)
                    and all(r in data["weights"] for r in XOCR_REGIMES)
                ):
                    data.setdefault("source_path", cand)
                    return data
            except Exception:  # nosec B110
                continue
    fallback = copy.deepcopy(DEFAULT_XOCR_GENOMES)
    fallback["source_path"] = "builtin_default"
    return fallback


def _normalize_span_key(text):
    """Return whitespace-collapsed normalized text for faux-bold span matching."""
    return re.sub(r"\s+", " ", normalize_text(text or "")).strip()


def _detect_and_strip_faux_bold(pdict):
    """Remove micro-shifted duplicate faux-bold spans from a PyMuPDF text dict.

    Returns ``(clean_pdict, faux_bold_detected)``. When no duplicate spans are
    found (99%+ normal pages), returns ``(pdict, False)`` completely untouched.
    """
    if not isinstance(pdict, dict):
        return pdict, False
    blocks = pdict.get("blocks") or []
    by_text = {}
    span_count = 0
    for bi, blk in enumerate(blocks):
        if blk.get("type", 0) != 0:
            continue
        for li, ln in enumerate(blk.get("lines") or []):
            for si, sp in enumerate(ln.get("spans") or []):
                norm_k = _normalize_span_key(sp.get("text") or "")
                if not norm_k:
                    continue
                sb = sp.get("bbox") or ln.get("bbox")
                if not sb or len(sb) != 4:
                    continue
                span_count += 1
                by_text.setdefault(norm_k, []).append(
                    (
                        bi,
                        li,
                        si,
                        float(sb[0]),
                        float(sb[1]),
                        float(sb[2]),
                        float(sb[3]),
                        float(sp.get("size") or 10.0),
                    )
                )

    if span_count < 2:
        return pdict, False

    ghost_coords = set()
    for norm_k, entries in by_text.items():
        if len(entries) < 2:
            continue
        entries.sort(key=lambda e: (round(e[4], 2), round(e[3], 2), e[0], e[1], e[2]))
        is_short_1 = len(norm_k) == 1
        kept = []
        for ent in entries:
            bi, li, si, x0, y0, x1, y1, fsz = ent
            is_ghost = False
            for _, _, _, kx0, ky0, kx1, ky1, kfsz in kept:
                size_ratio = max(fsz, kfsz) / max(0.5, min(fsz, kfsz))
                if size_ratio > 1.35:
                    continue
                dx = abs(x0 - kx0)
                dy = abs(y0 - ky0)
                if dx <= 2.0 and dy <= 2.0:
                    if is_short_1:
                        x_ov = min(x1, kx1) > max(x0, kx0)
                        if (dx <= 0.8 and dy <= 0.8) or x_ov:
                            is_ghost = True
                            break
                    else:
                        is_ghost = True
                        break
            if is_ghost:
                ghost_coords.add((bi, li, si))
            else:
                kept.append(ent)

    if not ghost_coords:
        return pdict, False

    clean_blocks = []
    for bi, blk in enumerate(blocks):
        if blk.get("type", 0) != 0:
            clean_blocks.append(blk)
            continue
        new_lines = []
        for li, ln in enumerate(blk.get("lines") or []):
            orig_spans = ln.get("spans") or []
            kept_spans = [
                sp
                for si, sp in enumerate(orig_spans)
                if (bi, li, si) not in ghost_coords
            ]
            if kept_spans:
                new_ln = dict(ln)
                new_ln["spans"] = kept_spans
                new_lines.append(new_ln)
        if new_lines:
            new_blk = dict(blk)
            new_blk["lines"] = new_lines
            clean_blocks.append(new_blk)

    clean_pdict = dict(pdict)
    clean_pdict["blocks"] = clean_blocks
    return clean_pdict, True


def _rebuild_clean_text_from_dict(pdict):
    """Rebuild sorted reading-order text from a de-ghosted PyMuPDF text dict."""
    horiz_lines = []
    other_lines = []
    for blk in (pdict or {}).get("blocks") or []:
        if blk.get("type", 0) != 0:
            continue
        for ln in blk.get("lines") or []:
            dir_vec = ln.get("dir") or (1.0, 0.0)
            dx = float(dir_vec[0])
            spans = []
            for sp in ln.get("spans") or []:
                stxt = sp.get("text") or ""
                if not stxt:
                    continue
                if not stxt.strip():
                    if spans and not spans[-1][4].endswith((" ", "\t")):
                        spans[-1] = (
                            spans[-1][0],
                            spans[-1][1],
                            spans[-1][2],
                            spans[-1][3],
                            spans[-1][4] + " ",
                            spans[-1][5],
                        )
                    continue
                sb = sp.get("bbox") or ln.get("bbox")
                if not sb or len(sb) != 4:
                    continue
                spans.append(
                    (
                        float(sb[0]),
                        float(sb[1]),
                        float(sb[2]),
                        float(sb[3]),
                        stxt,
                        float(sp.get("size") or 10.0),
                    )
                )
            if not spans:
                continue
            if dx >= 0.92:
                spans.sort(key=lambda s: (s[0], s[1]))
                horiz_lines.append(
                    [
                        min(s[0] for s in spans),
                        min(s[1] for s in spans),
                        max(s[2] for s in spans),
                        max(s[3] for s in spans),
                        max(6.0, sum(s[5] for s in spans) / len(spans)),
                        spans,
                    ]
                )
            else:
                txt_joined = "".join(s[4] for s in spans).strip()
                lb = ln.get("bbox") or (spans[0][0], spans[0][1], spans[0][2], spans[0][3])
                if txt_joined:
                    other_lines.append(
                        (float(lb[1]), float(lb[0]), normalize_text(txt_joined))
                    )

    horiz_lines.sort(key=lambda item: (item[1], item[0]))
    baseline_groups = []
    for item in horiz_lines:
        iyc = 0.5 * (item[1] + item[3])
        if baseline_groups:
            grp = baseline_groups[-1]
            gyc = 0.5 * (grp[1] + grp[3])
            fref = max(6.0, grp[4], item[4])
            if abs(item[1] - grp[1]) <= 0.45 * fref or abs(iyc - gyc) <= 0.45 * fref:
                grp[0] = min(grp[0], item[0])
                grp[1] = min(grp[1], item[1])
                grp[2] = max(grp[2], item[2])
                grp[3] = max(grp[3], item[3])
                grp[4] = max(grp[4], item[4])
                grp[5].extend(item[5])
                continue
        baseline_groups.append(
            [item[0], item[1], item[2], item[3], item[4], list(item[5])]
        )

    out_lines = []
    for grp in baseline_groups:
        spans = sorted(grp[5], key=lambda s: (s[0], s[1]))
        parts = [spans[0][4]]
        prev_x1 = spans[0][2]
        prev_txt = spans[0][4]
        for sp in spans[1:]:
            gap = sp[0] - prev_x1
            cur_txt = sp[4]
            if (
                gap > 1.5
                and not prev_txt.endswith((" ", "\t"))
                and not cur_txt.startswith((" ", "\t"))
            ):
                parts.append(" ")
            parts.append(cur_txt)
            prev_x1 = max(prev_x1, sp[2])
            prev_txt = cur_txt
        line_str = normalize_text("".join(parts)).strip()
        if line_str:
            out_lines.append((grp[1], grp[0], line_str))

    out_lines.extend(other_lines)
    out_lines.sort(key=lambda row: (round(row[0], 2), round(row[1], 2)))
    return "\n".join(row[2] for row in out_lines)


def _extract_text_and_dict_fast(page):
    """Extract sorted text and text-only dict in one TextPage pass with faux-bold de-ghosting."""
    if page is None:
        return "", None
    if hasattr(page, "get_textpage"):
        try:
            import fitz

            txt_flags = getattr(fitz, "TEXTFLAGS_TEXT", 0)
            tp = page.get_textpage(flags=txt_flags)
            raw_txt = page.get_text("text", textpage=tp, sort=True) or ""
            pdict = page.get_text("dict", textpage=tp) or {}
            clean_pdict, faux_bold = _detect_and_strip_faux_bold(pdict)
            if not faux_bold:
                return raw_txt, pdict
            clean_txt = _rebuild_clean_text_from_dict(clean_pdict)
            return (clean_txt if clean_txt else raw_txt), clean_pdict
        except Exception:  # nosec B110
            pass
    try:
        raw_txt = (
            page.get_text("text", sort=True) if hasattr(page, "get_text") else ""
        )
        return raw_txt or "", None
    except Exception:  # nosec B110
        return "", None


def _quantize_dir_bucket(dir_vec):
    """Quantize line direction unit vector into stable orientation buckets."""
    if not dir_vec or len(dir_vec) < 2:
        return "H", 1.0, 0.0
    dx, dy = float(dir_vec[0]), float(dir_vec[1])
    norm = math.hypot(dx, dy)
    if norm <= 1e-6:
        return "H", 1.0, 0.0
    ux, uy = dx / norm, dy / norm
    if ux >= 0.92:
        return "H", 1.0, 0.0
    if uy <= -0.92:
        return "V90", 0.0, -1.0
    if uy >= 0.92:
        return "V270", 0.0, 1.0
    ang = int(round(math.degrees(math.atan2(uy, ux)) / 15.0) * 15) % 360
    rad = math.radians(ang)
    return f"A{ang}", math.cos(rad), math.sin(rad)


def _assemble_horizontal_block(blk, atoms, seen):
    """Assemble horizontal lines inside a single PyMuPDF dict block into atoms."""
    line_items = []
    for line in blk.get("lines") or []:
        bkey, _, _ = _quantize_dir_bucket(line.get("dir"))
        if bkey != "H":
            continue
        spans = []
        for sp in line.get("spans") or []:
            txt = sp.get("text") or ""
            if not txt.strip():
                continue
            sb = sp.get("bbox") or line.get("bbox")
            if not sb or len(sb) != 4:
                continue
            spans.append(
                [
                    float(sb[0]),
                    float(sb[1]),
                    float(sb[2]),
                    float(sb[3]),
                    txt,
                    float(sp.get("size") or 10.0),
                ]
            )
        if not spans:
            continue
        spans.sort(key=lambda s: (s[0], s[1]))
        merged = [spans[0]]
        for sp in spans[1:]:
            prev = merged[-1]
            fsize = max(6.0, 0.5 * (prev[5] + sp[5]))
            gap = sp[0] - prev[2]
            y_diff = abs(0.5 * (sp[1] + sp[3]) - 0.5 * (prev[1] + prev[3]))
            if y_diff <= 0.45 * fsize and gap <= max(8.0, 0.65 * fsize):
                sep = "" if gap <= 1.5 else " "
                prev[0] = min(prev[0], sp[0])
                prev[1] = min(prev[1], sp[1])
                prev[2] = max(prev[2], sp[2])
                prev[3] = max(prev[3], sp[3])
                prev[4] = prev[4] + sep + sp[4]
            else:
                merged.append(sp)
        for item in merged:
            line_items.append(item)

    if not line_items:
        return

    line_items.sort(key=lambda s: (round(s[1], 1), s[0]))
    baseline_merged = [line_items[0]]
    for item in line_items[1:]:
        prev = baseline_merged[-1]
        h = max(6.0, min(prev[3] - prev[1], item[3] - item[1]))
        yc_diff = abs(0.5 * (item[1] + item[3]) - 0.5 * (prev[1] + prev[3]))
        gap = item[0] - prev[2]
        if yc_diff <= 0.35 * h and -h <= gap <= max(8.0, 0.65 * item[5]):
            sep = "" if gap <= 1.5 else " "
            prev[0] = min(prev[0], item[0])
            prev[1] = min(prev[1], item[1])
            prev[2] = max(prev[2], item[2])
            prev[3] = max(prev[3], item[3])
            prev[4] = prev[4] + sep + item[4]
        else:
            baseline_merged.append(item)

    col_groups = []
    for item in baseline_merged:
        norm_line = re.sub(r"\s+", " ", normalize_text(item[4])).strip()
        if not norm_line:
            continue
        placed = False
        for grp in col_groups:
            x_ov = min(grp[2], item[2]) - max(grp[0], item[0])
            min_w = max(1.0, min(grp[2] - grp[0], item[2] - item[0]))
            y_gap = item[1] - grp[3]
            h_ref = max(6.0, item[3] - item[1])
            if (
                (abs(item[0] - grp[0]) <= 18.0 or x_ov / min_w >= 0.45)
                and -0.4 * h_ref <= y_gap <= 0.75 * h_ref
            ):
                grp[0] = min(grp[0], item[0])
                grp[1] = min(grp[1], item[1])
                grp[2] = max(grp[2], item[2])
                grp[3] = max(grp[3], item[3])
                grp[4] = grp[4] + " " + norm_line
                placed = True
                break
        if not placed:
            col_groups.append(
                [item[0], item[1], item[2], item[3], norm_line, item[5]]
            )

    for grp in col_groups:
        _append_dedup_atom(
            atoms,
            seen,
            grp[0],
            grp[1],
            grp[2],
            grp[3],
            grp[4],
            grp[5],
        )


def _assemble_rotated_bucket_spans(bucket_items, bdx, bdy, atoms, seen):
    """Assemble rotated spans sharing one orientation bucket along (n_band, t)."""
    if not bucket_items:
        return
    # Group into parallel normal-axis bands without cross-band merging
    bands = []
    for sp in sorted(bucket_items, key=lambda s: (s["n_c"], s["t_start"])):
        placed = False
        for band in reversed(bands):
            ref_n = band["n_sum"] / float(len(band["items"]))
            ref_f = max(sp["size"], band["max_size"])
            if abs(sp["n_c"] - ref_n) <= 0.55 * ref_f:
                band["items"].append(sp)
                band["n_sum"] += sp["n_c"]
                band["max_size"] = ref_f
                placed = True
                break
        if not placed:
            bands.append(
                {"n_sum": sp["n_c"], "max_size": sp["size"], "items": [sp]}
            )

    for band in bands:
        items = sorted(band["items"], key=lambda s: (s["t_start"], s["t_c"]))
        merged = [dict(items[0])]
        for cur in items[1:]:
            prev = merged[-1]
            fsize = max(6.0, prev["size"], cur["size"])
            n_diff = abs(cur["n_c"] - prev["n_c"])
            t_gap = cur["t_start"] - prev["t_end"]
            if (
                n_diff <= 0.55 * fsize
                and -0.35 * fsize <= t_gap <= max(10.0, 1.2 * fsize)
            ):
                had_space = prev.get("trail_space") or cur.get("lead_space")
                sep = " " if (t_gap > 1.5 or had_space) else ""
                prev["x0"] = min(prev["x0"], cur["x0"])
                prev["y0"] = min(prev["y0"], cur["y0"])
                prev["x1"] = max(prev["x1"], cur["x1"])
                prev["y1"] = max(prev["y1"], cur["y1"])
                prev["t_end"] = max(prev["t_end"], cur["t_end"])
                prev["n_c"] = 0.5 * (prev["n_c"] + cur["n_c"])
                prev["size"] = max(prev["size"], cur["size"])
                prev["trail_space"] = bool(cur.get("trail_space", False))
                prev["text"] = f"{prev['text']}{sep}{cur['text']}"
            else:
                merged.append(dict(cur))
        for item in merged:
            clean_txt = re.sub(r"\s+", " ", normalize_text(item["text"])).strip()
            if clean_txt:
                _append_dedup_atom(
                    atoms,
                    seen,
                    item["x0"],
                    item["y0"],
                    item["x1"],
                    item["y1"],
                    clean_txt,
                    item["size"],
                    dir_vec=item["dir"],
                )


def _extract_clean_text_atoms(page, blocks=None, text_dict=None):
    """Extract normalized, orientation-aware deduplicated text atoms with bboxes."""
    atoms = []
    seen = set()

    if text_dict is not None or (
        blocks is None and page is not None and hasattr(page, "get_text")
    ):
        try:
            if text_dict is not None:
                pdict = text_dict
            else:
                import fitz

                txt_flags = getattr(fitz, "TEXTFLAGS_TEXT", 0)
                pdict = page.get_text("dict", flags=txt_flags) or {}

            dict_blocks = [
                blk
                for blk in (pdict.get("blocks") or [])
                if blk.get("type", 0) == 0
            ]
            has_rotated = False
            for blk in dict_blocks:
                for line in blk.get("lines") or []:
                    if not any((sp.get("text") or "").strip() for sp in (line.get("spans") or [])):
                        continue
                    bkey, _, _ = _quantize_dir_bucket(line.get("dir"))
                    if bkey != "H":
                        has_rotated = True
                        break
                if has_rotated:
                    break

            for blk in dict_blocks:
                _assemble_horizontal_block(blk, atoms, seen)

            if has_rotated:
                rot_buckets = {}
                for blk in dict_blocks:
                    for line in blk.get("lines") or []:
                        raw_dir = line.get("dir") or (1.0, 0.0)
                        bkey, bdx, bdy = _quantize_dir_bucket(raw_dir)
                        if bkey == "H":
                            continue
                        norm_raw = math.hypot(float(raw_dir[0]), float(raw_dir[1])) or 1.0
                        dir_out = [
                            round(float(raw_dir[0]) / norm_raw, 3),
                            round(float(raw_dir[1]) / norm_raw, 3),
                        ]
                        pending_lead_space = False
                        bucket_list = rot_buckets.setdefault((bkey, bdx, bdy), [])
                        for sp in line.get("spans") or []:
                            txt = sp.get("text") or ""
                            if not txt:
                                continue
                            if not txt.strip():
                                if bucket_list and bucket_list[-1].get("dir") == dir_out:
                                    bucket_list[-1]["trail_space"] = True
                                pending_lead_space = True
                                continue
                            sb = sp.get("bbox") or line.get("bbox")
                            if not sb or len(sb) != 4:
                                pending_lead_space = False
                                continue
                            x0, y0, x1, y1 = (
                                float(sb[0]),
                                float(sb[1]),
                                float(sb[2]),
                                float(sb[3]),
                            )
                            fsize = float(sp.get("size") or 10.0)
                            cx = 0.5 * (x0 + x1)
                            cy = 0.5 * (y0 + y1)
                            w = max(0.5, x1 - x0)
                            h = max(0.5, y1 - y0)
                            t_c = cx * bdx + cy * bdy
                            n_c = -cx * bdy + cy * bdx
                            half_t = max(
                                0.5 * fsize,
                                0.5 * (w * abs(bdx) + h * abs(bdy))
                                - abs(bdx * bdy) * 1.3 * fsize,
                            )
                            bucket_list.append(
                                {
                                    "x0": x0,
                                    "y0": y0,
                                    "x1": x1,
                                    "y1": y1,
                                    "text": txt.strip(),
                                    "lead_space": bool(
                                        pending_lead_space or txt.startswith((" ", "\t"))
                                    ),
                                    "trail_space": bool(txt.endswith((" ", "\t"))),
                                    "size": fsize,
                                    "t_c": t_c,
                                    "t_start": t_c - half_t,
                                    "t_end": t_c + half_t,
                                    "n_c": n_c,
                                    "dir": dir_out,
                                }
                            )
                            pending_lead_space = False
                for (bkey, bdx, bdy), items in rot_buckets.items():
                    _assemble_rotated_bucket_spans(items, bdx, bdy, atoms, seen)

            if atoms:
                return atoms
        except Exception:  # nosec B110
            atoms = []

    raw_blocks = blocks
    if raw_blocks is None and page is not None and hasattr(page, "get_text"):
        try:
            raw_blocks = page.get_text("blocks") or []
        except Exception:  # nosec B110
            raw_blocks = []

    for blk in raw_blocks or []:
        if isinstance(blk, dict):
            b_type = blk.get("type", 0)
            if b_type != 0:
                continue
            x0, y0, x1, y1 = blk.get("bbox", (0, 0, 0, 0))
            txt = blk.get("text", "")
        elif len(blk) >= 5:
            if len(blk) >= 7 and blk[6] != 0:
                continue
            x0, y0, x1, y1, txt = blk[0], blk[1], blk[2], blk[3], blk[4]
        else:
            continue
        clean_t = re.sub(r"\s+", " ", normalize_text(str(txt or ""))).strip()
        if not clean_t:
            continue
        _append_dedup_atom(atoms, seen, x0, y0, x1, y1, clean_t, 10.0)
    return atoms


def _append_dedup_atom(atoms, seen, x0, y0, x1, y1, text_val, size_val, dir_vec=None):
    """Append atom while suppressing faux-bold slightly-offset duplicate prints."""
    fx0, fy0, fx1, fy1 = float(x0), float(y0), float(x1), float(y1)
    key = (round(fx0, 1), round(fy0, 1), text_val)
    if key in seen:
        return
    compact = re.sub(r"\s+", "", text_val)
    for prev in reversed(atoms[-16:]):
        p_compact = re.sub(r"\s+", "", prev["text"])
        if abs(fx0 - prev["x0"]) <= 3.5 and abs(fy0 - prev["y0"]) <= 3.5:
            if compact == p_compact or (
                len(compact) >= 4
                and (compact in p_compact or p_compact in compact)
            ):
                if len(text_val) > len(prev["text"]):
                    prev.update(
                        {"x0": fx0, "y0": fy0, "x1": fx1, "y1": fy1, "text": text_val}
                    )
                return
        iw = max(0.0, min(fx1, prev["x1"]) - max(fx0, prev["x0"]))
        ih = max(0.0, min(fy1, prev["y1"]) - max(fy0, prev["y0"]))
        if iw > 0 and ih > 0:
            inter = iw * ih
            p_area = (prev["x1"] - prev["x0"]) * (prev["y1"] - prev["y0"])
            min_a = max(1e-6, min((fx1 - fx0) * (fy1 - fy0), p_area))
            if (inter / min_a) >= 0.70 and compact == p_compact:
                return
    seen.add(key)
    entry = {
        "x0": fx0,
        "y0": fy0,
        "x1": fx1,
        "y1": fy1,
        "text": text_val,
        "size": float(size_val),
    }
    if dir_vec is not None:
        entry["dir"] = [round(float(dir_vec[0]), 3), round(float(dir_vec[1]), 3)]
    atoms.append(entry)


def _compute_canvas_occupancy(page, atoms):
    """Compute union text coverage ratio & 4x4 short-callout spatial entropy."""
    rx0 = float(page.rect.x0)
    ry0 = float(page.rect.y0)
    pw = max(1.0, float(abs(page.rect.width)))
    ph = max(1.0, float(abs(page.rect.height)))

    if not atoms:
        return 1.0, 0.0

    grid_n = 24
    occupied = bytearray(grid_n * grid_n)
    callout_cells = [0] * 16
    short_count = 0

    for a in atoms:
        nx0 = max(0.0, min(1.0, (a["x0"] - rx0) / pw))
        ny0 = max(0.0, min(1.0, (a["y0"] - ry0) / ph))
        nx1 = max(0.0, min(1.0, (a["x1"] - rx0) / pw))
        ny1 = max(0.0, min(1.0, (a["y1"] - ry0) / ph))
        gx0 = min(grid_n - 1, int(nx0 * grid_n))
        gx1 = min(grid_n - 1, max(gx0, int(math.ceil(nx1 * grid_n)) - 1))
        gy0 = min(grid_n - 1, int(ny0 * grid_n))
        gy1 = min(grid_n - 1, max(gy0, int(math.ceil(ny1 * grid_n)) - 1))
        for gy in range(gy0, gy1 + 1):
            row_off = gy * grid_n
            for gx in range(gx0, gx1 + 1):
                occupied[row_off + gx] = 1

        nw = nx1 - nx0
        if len(a["text"]) <= 120 or nw <= 0.35:
            short_count += 1
            cx = min(3, max(0, int(0.5 * (nx0 + nx1) * 4.0)))
            cy = min(3, max(0, int(0.5 * (ny0 + ny1) * 4.0)))
            callout_cells[cy * 4 + cx] += 1

    union_ratio = sum(occupied) / float(grid_n * grid_n)
    unexplained_ratio = round(max(0.0, min(1.0, 1.0 - union_ratio)), 4)

    if short_count == 0:
        callout_entropy = 0.0
    else:
        entropy = 0.0
        for cnt in callout_cells:
            if cnt > 0:
                p = cnt / float(short_count)
                entropy -= p * math.log(p)
        h_norm = entropy / math.log(16.0)
        short_weight = short_count / float(len(atoms))
        callout_entropy = round(min(1.0, h_norm * short_weight), 4)

    return unexplained_ratio, callout_entropy


def _probe_drawings_fast(page, img_metrics):
    """Probe vector drawings safely; skip stream parse on giant multi-layer rasters."""
    if (
        img_metrics["image_count"] > 20
        and (img_metrics["max_img_px"] >= 4_000_000 or img_metrics["area_proxy"] >= 0.65)
    ):
        return [], True

    try:
        drawings = page.get_drawings() or []
    except Exception:  # nosec B110
        drawings = []
    return drawings, False


def _fast_drawing_metrics(page, drawings=None, img_metrics=None):
    """Compute vector drawing counts, table rules, and short-stroke ratio in one pass."""
    if img_metrics is None:
        img_metrics = _fast_page_image_metrics(page)
    if drawings is None:
        drawings, drawings_skipped = _probe_drawings_fast(page, img_metrics)
    else:
        drawings_skipped = False

    vector_drawing_count = len(drawings)
    h_rules = 0
    g_rects = 0
    short_strokes = 0
    finite_rects = 0
    for drw in drawings:
        rect = drw.get("rect")
        if not rect:
            continue
        x0 = float(rect.x0)
        y0 = float(rect.y0)
        x1 = float(rect.x1)
        y1 = float(rect.y1)
        if not (
            math.isfinite(x0)
            and math.isfinite(y0)
            and math.isfinite(x1)
            and math.isfinite(y1)
        ):
            continue
        finite_rects += 1
        w = abs(x1 - x0)
        h = abs(y1 - y0)
        max_dim = max(w, h)
        if 0.2 < max_dim <= 28.0:
            short_strokes += 1
        if w >= 120.0 and h <= 5.0:
            h_rules += 1
        elif w >= 25.0 and h >= 10.0 and drw.get("type") != "f":
            g_rects += 1

    short_stroke_ratio = (short_strokes / float(finite_rects)) if finite_rects > 0 else 0.0
    short_item_strokes = 0
    total_item_strokes = 0
    if (not drawings_skipped) and 0 < vector_drawing_count < 400:
        for drw in drawings:
            for item in drw.get("items") or ():
                if total_item_strokes >= 3000:
                    break
                if item and item[0] == "l" and len(item) >= 3:
                    p1, p2 = item[1], item[2]
                    seg_len = math.hypot(float(p2.x) - float(p1.x), float(p2.y) - float(p1.y))
                    total_item_strokes += 1
                    if 0.2 < seg_len <= 28.0:
                        short_item_strokes += 1
            if total_item_strokes >= 3000:
                break
        if total_item_strokes >= 400:
            short_stroke_ratio = short_item_strokes / float(total_item_strokes)

    return {
        "drawings": drawings,
        "drawings_skipped": drawings_skipped,
        "vector_drawing_count": max(vector_drawing_count, short_item_strokes if total_item_strokes >= 400 else 0),
        "h_rules": h_rules,
        "g_rects": g_rects,
        "short_stroke_ratio": round(short_stroke_ratio, 4),
    }


def classify_page_regime(
    page, raw_text=None, qual=None, genomes=None, profile="auto", text_dict=None
):
    """Classify page into one of 4 XOCR_REGIMES using 8D simplex + Platt + split-conformal."""
    prof = resolve_hardware_profile(profile)
    g_cfg = genomes if isinstance(genomes, dict) else load_xocr_genomes()

    if raw_text is None or text_dict is None:
        fast_raw, fast_dict = _extract_text_and_dict_fast(page)
        if raw_text is None:
            raw_text = fast_raw
        if text_dict is None:
            text_dict = fast_dict
    if qual is None:
        qual = evaluate_page_quality(raw_text, page)

    img_metrics = qual.get("image_metrics") or _fast_page_image_metrics(page)
    atoms = _extract_clean_text_atoms(page, text_dict=text_dict)
    drw_metrics = _fast_drawing_metrics(page, img_metrics=img_metrics)
    drawings = drw_metrics["drawings"]
    drawings_skipped = drw_metrics["drawings_skipped"]
    vector_drawing_count = drw_metrics["vector_drawing_count"]
    h_rules = drw_metrics["h_rules"]
    g_rects = drw_metrics["g_rects"]
    short_stroke_ratio = drw_metrics["short_stroke_ratio"]

    unexplained_ratio, callout_entropy = _compute_canvas_occupancy(page, atoms)

    pw = max(1.0, float(abs(page.rect.width)))
    ph = max(1.0, float(abs(page.rect.height)))
    page_area = pw * ph

    garble_cid_density = round(min(1.0, qual["garble_ratio"] / 0.20), 4)
    vector_drawing_density = round(
        min(1.0, math.log1p(vector_drawing_count) / math.log1p(1000.0)), 4
    )
    img_area_ratio = float(img_metrics["image_area_ratio"])
    max_raster_resolution = round(
        min(
            1.0,
            0.65 * img_area_ratio
            + 0.35 * min(1.0, img_metrics["max_img_px"] / 12_000_000.0),
        ),
        4,
    )
    area_scale = min(1.0, max(0.0, (page_area - 550_000.0) / 2_500_000.0))
    landscape_bonus = 0.20 if pw > ph * 1.15 else 0.0
    sheet_aspect_scale = round(min(1.0, 0.80 * area_scale + landscape_bonus), 4)

    table_rule_density = round(min(1.0, (h_rules * 2.0 + g_rects * 0.5) / 30.0), 4)
    if drawings_skipped and len(atoms) >= 6:
        table_rule_density = max(table_rule_density, 0.20)

    clean_chars = int(qual["char_count"])
    clean_sufficiency = min(1.0, clean_chars / 600.0) * (1.0 - garble_cid_density)
    text_sufficiency_penalty = round(max(0.0, 1.0 - clean_sufficiency), 4)

    feat_vec = [
        garble_cid_density,
        vector_drawing_density,
        max_raster_resolution,
        sheet_aspect_scale,
        unexplained_ratio,
        callout_entropy,
        table_rule_density,
        text_sufficiency_penalty,
    ]
    features = {name: feat_vec[idx] for idx, name in enumerate(XOCR_FEATURE_NAMES)}

    weights_map = g_cfg.get("weights") or DEFAULT_XOCR_GENOMES["weights"]
    platt_map = g_cfg.get("platt") or DEFAULT_XOCR_GENOMES["platt"]
    q_hat = float(g_cfg.get("conformal_q_hat", 0.38))

    raw_scores = {}
    platt_probs = {}
    for reg in XOCR_REGIMES:
        w = weights_map.get(reg) or DEFAULT_XOCR_GENOMES["weights"][reg]
        raw = sum(float(w[d]) * feat_vec[d] for d in range(8))
        raw_scores[reg] = round(raw, 4)
        p_cfg = platt_map.get(reg) or DEFAULT_XOCR_GENOMES["platt"][reg]
        t_val = float(p_cfg.get("T", 4.0))
        b_val = float(p_cfg.get("b", 0.0))
        logit = max(-30.0, min(30.0, t_val * raw + b_val))
        platt_probs[reg] = 1.0 / (1.0 + math.exp(-logit))

    prob_sum = max(1e-9, sum(platt_probs.values()))
    norm_probs = {reg: round(platt_probs[reg] / prob_sum, 4) for reg in XOCR_REGIMES}
    best_regime = max(XOCR_REGIMES, key=lambda r: (norm_probs[r], raw_scores[r]))
    confidence = norm_probs[best_regime]
    conformal_abstain = bool((1.0 - confidence) > q_hat)

    # Structural safety override when high-res raster coverage is unmistakable
    if (
        best_regime in ("DIGITAL_TEXT_TABLE", "RASTER_DRAWING_OR_MAP")
        and img_area_ratio >= 0.40
        and unexplained_ratio >= 0.55
        and (sheet_aspect_scale >= 0.35 or clean_chars < 250 or len(atoms) >= 4)
    ):
        target_regime = (
            "HYBRID_COMPOSITE_DRAWING"
            if (clean_chars >= 120 and qual["garble_ratio"] < 0.05 and len(atoms) >= 4)
            else "RASTER_DRAWING_OR_MAP"
        )
        if target_regime != best_regime:
            best_regime = target_regime
            confidence = norm_probs[best_regime]
            conformal_abstain = True

    exploded_glyphs_suspected = bool(
        (not drawings_skipped)
        and clean_chars < 35
        and vector_drawing_count >= 400
        and short_stroke_ratio >= 0.45
        and img_area_ratio < 0.35
        and h_rules == 0
        and g_rects <= 4
    )
    if exploded_glyphs_suspected and best_regime not in (
        "HYBRID_COMPOSITE_DRAWING",
        "RASTER_DRAWING_OR_MAP",
    ):
        best_regime = "VECTOR_CAD_DRAWING"
        confidence = norm_probs[best_regime]
        conformal_abstain = bool((1.0 - confidence) > q_hat)

    needs_ocr = bool(
        qual["needs_ocr"]
        or exploded_glyphs_suspected
        or best_regime in ("RASTER_DRAWING_OR_MAP", "HYBRID_COMPOSITE_DRAWING")
    )
    needs_vision = bool(
        exploded_glyphs_suspected
        or best_regime
        in (
            "VECTOR_CAD_DRAWING",
            "RASTER_DRAWING_OR_MAP",
            "HYBRID_COMPOSITE_DRAWING",
        )
        or (conformal_abstain and unexplained_ratio >= 0.65 and img_area_ratio >= 0.35)
    )

    return {
        "regime": best_regime,
        "confidence": confidence,
        "conformal_abstain": conformal_abstain,
        "conformal_q_hat": round(q_hat, 4),
        "regime_probabilities": norm_probs,
        "raw_scores": raw_scores,
        "features": features,
        "feature_vector": feat_vec,
        "unexplained_canvas_ratio": unexplained_ratio,
        "vector_drawing_count": vector_drawing_count,
        "short_stroke_ratio": short_stroke_ratio,
        "exploded_glyphs_suspected": exploded_glyphs_suspected,
        "drawings_probe_skipped": drawings_skipped,
        "image_metrics": img_metrics,
        "needs_ocr": needs_ocr,
        "needs_vision": needs_vision,
        "profile": prof["profile"],
        "_drawings": drawings,
        "_atoms": atoms,
    }


def _extract_aligned_block_tables(page, blocks=None, atoms=None):
    """Recover borderless multi-column tables by X/Y coordinate alignment."""
    if atoms is None or blocks is not None:
        atoms = _extract_clean_text_atoms(page, blocks=blocks)
    atoms = [
        a
        for a in (atoms or [])
        if not ("dir" in a and abs(float(a["dir"][0])) < 0.90)
    ]
    if len(atoms) < 4:
        return []

    pw = max(1.0, float(abs(page.rect.width))) if page is not None else 1000.0
    ph = max(1.0, float(abs(page.rect.height))) if page is not None else 1000.0
    rx0 = float(page.rect.x0) if page is not None else 0.0
    ry0 = float(page.rect.y0) if page is not None else 0.0

    # Group atoms into horizontal row bands by Y overlap
    sorted_atoms = sorted(atoms, key=lambda a: (0.5 * (a["y0"] + a["y1"]), a["x0"]))
    row_bands = []
    for a in sorted_atoms:
        ah = max(6.0, a["y1"] - a["y0"])
        ayc = 0.5 * (a["y0"] + a["y1"])
        placed = False
        for band in reversed(row_bands):
            by0, by1 = band["y0"], band["y1"]
            byc = 0.5 * (by0 + by1)
            bh = max(6.0, by1 - by0)
            y_ov = min(a["y1"], by1) - max(a["y0"], by0)
            min_h = max(1.0, min(ah, bh))
            if (y_ov / min_h) >= 0.35 or abs(ayc - byc) <= 0.42 * max(ah, bh):
                band["atoms"].append(a)
                band["y0"] = min(band["y0"], a["y0"])
                band["y1"] = max(band["y1"], a["y1"])
                placed = True
                break
        if not placed:
            row_bands.append({"y0": a["y0"], "y1": a["y1"], "atoms": [a]})

    # Sort atoms left-to-right inside each row band
    for band in row_bands:
        band["atoms"].sort(key=lambda a: a["x0"])

    # Form vertical table regions from consecutive multi-atom bands (>= 2 atoms)
    heights = [b["y1"] - b["y0"] for b in row_bands if len(b["atoms"]) >= 2]
    if len(heights) < 2:
        return []
    med_h = max(10.0, sorted(heights)[len(heights) // 2])

    regions = []
    cur_region = []
    for band in row_bands:
        if len(band["atoms"]) < 2:
            if len(cur_region) >= 2:
                regions.append(cur_region)
            cur_region = []
            continue
        if cur_region:
            gap = band["y0"] - cur_region[-1]["y1"]
            if gap > max(36.0, 1.8 * med_h):
                if len(cur_region) >= 2:
                    regions.append(cur_region)
                cur_region = [band]
                continue
        cur_region.append(band)
    if len(cur_region) >= 2:
        regions.append(cur_region)

    recovered = []
    for reg in regions:
        reg_atoms = [a for b in reg for a in b["atoms"]]
        # Cluster X intervals into column bins (by interval overlap)
        col_bins = []
        for a in sorted(reg_atoms, key=lambda x: x["x0"]):
            best_idx = None
            best_score = -1e9
            for idx, cb in enumerate(col_bins):
                x_ov = min(cb["x1"], a["x1"]) - max(cb["x0"], a["x0"])
                if x_ov > -8.0 or abs(a["x0"] - cb["x0"]) <= 18.0:
                    score = x_ov - 0.1 * abs(a["x0"] - cb["x0"])
                    if score > best_score:
                        best_score = score
                        best_idx = idx
            if best_idx is not None:
                cb = col_bins[best_idx]
                cb["x0"] = min(cb["x0"], a["x0"])
                cb["x1"] = max(cb["x1"], a["x1"])
            else:
                col_bins.append({"x0": a["x0"], "x1": a["x1"]})

        col_bins.sort(key=lambda c: c["x0"])
        if len(col_bins) < 2:
            continue

        raw_col_bounds_norm = [
            [
                round(max(0.0, min(1.0, (cb["x0"] - rx0) / pw)), 4),
                round(max(0.0, min(1.0, (cb["x1"] - rx0) / pw)), 4),
            ]
            for cb in col_bins
        ]

        grid_rows = []
        for band in reg:
            row_cells = [""] * len(col_bins)
            for a in band["atoms"]:
                best_ci = 0
                best_ov = -1e9
                for ci, cb in enumerate(col_bins):
                    ov = min(cb["x1"], a["x1"]) - max(cb["x0"], a["x0"])
                    dist = abs(0.5 * (a["x0"] + a["x1"]) - 0.5 * (cb["x0"] + cb["x1"]))
                    score = ov - 0.05 * dist
                    if score > best_ov:
                        best_ov = score
                        best_ci = ci
                row_cells[best_ci] = (
                    f"{row_cells[best_ci]} {a['text']}".strip()
                    if row_cells[best_ci]
                    else a["text"]
                )
            grid_rows.append(row_cells)

        cleaned, keep_cols = _clean_table_rows_with_meta(grid_rows)
        if not cleaned:
            continue
        col_bounds_norm = [
            raw_col_bounds_norm[ci]
            for ci in keep_cols
            if ci < len(raw_col_bounds_norm)
        ]

        ncols = len(cleaned[0])
        nrows = len(cleaned)
        total_slots = max(1, nrows * ncols)
        non_empty_slots = sum(1 for r in cleaned for c in r if c)
        if non_empty_slots / total_slots < 0.52:
            continue
        cell_lens = sorted(len(c) for r in cleaned for c in r if c)
        if not cell_lens:
            continue
        med_len = cell_lens[len(cell_lens) // 2]
        p90_len = cell_lens[min(len(cell_lens) - 1, int(0.9 * len(cell_lens)))]

        # Reject 2-column prose paragraphs & sparse headers
        if med_len > 75 or p90_len > 140:
            continue

        body_cells = [c for r in cleaned[1:] for c in r if c]
        num_cells = sum(1 for c in body_cells if NUMERIC_CELL_RE.match(c))
        num_ratio = num_cells / max(1, len(body_cells))

        if ncols == 2:
            if nrows < 3:
                continue
            if med_len > 48 or (num_ratio < 0.20 and med_len > 34):
                continue
        elif nrows < 2:
            continue

        bx0 = min(a["x0"] for a in reg_atoms)
        by0 = min(a["y0"] for a in reg_atoms)
        bx1 = max(a["x1"] for a in reg_atoms)
        by1 = max(a["y1"] for a in reg_atoms)
        recovered.append(
            {
                "bbox": [round(bx0, 2), round(by0, 2), round(bx1, 2), round(by1, 2)],
                "norm_bbox": [
                    round(max(0.0, min(1.0, (bx0 - rx0) / pw)), 4),
                    round(max(0.0, min(1.0, (by0 - ry0) / ph)), 4),
                    round(max(0.0, min(1.0, (bx1 - rx0) / pw)), 4),
                    round(max(0.0, min(1.0, (by1 - ry0) / ph)), 4),
                ],
                "col_bounds_norm": col_bounds_norm,
                "raw_col_bounds_norm": raw_col_bounds_norm,
                "keep_cols": keep_cols,
                "rows": cleaned,
                "nrows": nrows,
                "ncols": ncols,
                "source": "aligned_blocks",
            }
        )
    return recovered


def _grid_natural_key(label):
    """Natural CAD grid-axis sort key: ('2.1') < ('10') and ('Z') < ('AA')."""
    raw = str(label or "").strip()
    m_num = re.match(r"^(\d+)(?:\.(\d+))?([A-Za-z'\u2032]*)$", raw)
    if m_num:
        major = int(m_num.group(1))
        minor_s = m_num.group(2)
        suf = (m_num.group(3) or "").lower()
        sub_tier = 0 if (minor_s is None and not suf) else (1 if minor_s is not None else 2)
        return (0, major, sub_tier, int(minor_s) if minor_s is not None else 0, suf)
    m_alpha = re.match(r"^([A-Za-z]+)(?:[.'\u2032]?(\d+))?([A-Za-z'\u2032]*)$", raw)
    if m_alpha:
        letters = m_alpha.group(1).upper()
        alpha_rank = 0
        for ch in letters:
            alpha_rank = alpha_rank * 26 + (ord(ch) - ord("A") + 1)
        minor_s = m_alpha.group(2)
        suf = (m_alpha.group(3) or "").lower()
        sub_tier = 0 if (minor_s is None and not suf) else (1 if minor_s is not None else 2)
        return (1, alpha_rank, sub_tier, int(minor_s) if minor_s is not None else 0, suf)
    return (2, 0, 0, 0, raw.lower())


def _pt_xy(pt):
    """Normalize a PyMuPDF Point or 2-tuple into float (x, y)."""
    if hasattr(pt, "x"):
        return float(pt.x), float(pt.y)
    return float(pt[0]), float(pt[1])


def _safe_probe_drawings(page, drawings=None):
    """Fetch page drawings with O(1) multi-layer raster bailout."""
    if drawings is not None:
        return drawings
    if page is None:
        return []
    if hasattr(page, "get_images"):
        img_metrics = _fast_page_image_metrics(page)
        drws, _ = _probe_drawings_fast(page, img_metrics)
        return drws
    try:
        return page.get_drawings() or []
    except Exception:  # nosec B110
        return []


def _extract_vector_primitives(drawings):
    """Split PyMuPDF drawings into bubble loops, line segments, delta triangles, and clouds."""
    bubbles = []
    segments = []
    triangles = []
    clouds = []
    loose_curves = []

    def _flush_sub(sub):
        if not sub or not sub["pts"]:
            return
        xs = [p[0] for p in sub["pts"]]
        ys = [p[1] for p in sub["pts"]]
        x0, x1 = min(xs), max(xs)
        y0, y1 = min(ys), max(ys)
        w = x1 - x0
        h = y1 - y0
        n_c = sub["n_c"]
        n_l = sub["n_l"]
        max_dim = max(w, h)
        min_dim = min(w, h)
        if 7.0 <= w <= 60.0 and 7.0 <= h <= 60.0 and max_dim > 0 and (min_dim / max_dim) >= 0.72:
            if n_c >= 2 or n_l >= 6:
                cx = 0.5 * (x0 + x1)
                cy = 0.5 * (y0 + y1)
                for prev in bubbles:
                    if abs(prev["cx"] - cx) <= 4.0 and abs(prev["cy"] - cy) <= 4.0 and abs(prev["w"] - w) <= 6.0:
                        return
                bubbles.append(
                    {
                        "bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                        "cx": cx,
                        "cy": cy,
                        "w": w,
                        "h": h,
                    }
                )
                return
        if n_c == 0 and 2 <= n_l <= 4 and 6.0 <= w <= 42.0 and 6.0 <= h <= 42.0:
            uniq = []
            for px, py in sub["verts"]:
                if not any(math.hypot(px - ux, py - uy) <= 1.5 for ux, uy in uniq):
                    uniq.append((px, py))
            if len(uniq) == 3:
                triangles.append({"bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]})
                return
        if n_c >= 6 and max_dim >= 24.0:
            clouds.append({"bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]})

    for drw in drawings or ():
        items = drw.get("items") or ()
        if not items:
            rect = drw.get("rect")
            if rect:
                x0, y0, x1, y1 = float(rect.x0), float(rect.y0), float(rect.x1), float(rect.y1)
                rw, rh = abs(x1 - x0), abs(y1 - y0)
                if min(rw, rh) <= 2.5 and max(rw, rh) >= 12.0:
                    if rw >= rh:
                        yc = 0.5 * (y0 + y1)
                        segments.append((min(x0, x1), yc, max(x0, x1), yc))
                    else:
                        xc = 0.5 * (x0 + x1)
                        segments.append((xc, min(y0, y1), xc, max(y0, y1)))
            continue

        cur = None
        for item in items:
            if not item:
                continue
            op = item[0]
            if op == "l" and len(item) >= 3:
                p0 = _pt_xy(item[1])
                p1 = _pt_xy(item[2])
                segments.append((p0[0], p0[1], p1[0], p1[1]))
                if cur is None or math.hypot(p0[0] - cur["end"][0], p0[1] - cur["end"][1]) > 1.5:
                    _flush_sub(cur)
                    cur = {"start": p0, "end": p1, "pts": [p0, p1], "verts": [p0, p1], "n_l": 1, "n_c": 0}
                else:
                    cur["pts"].append(p1)
                    cur["verts"].append(p1)
                    cur["end"] = p1
                    cur["n_l"] += 1
                    if (
                        math.hypot(p1[0] - cur["start"][0], p1[1] - cur["start"][1]) <= 1.5
                        and (cur["n_l"] + cur["n_c"]) >= 3
                    ):
                        _flush_sub(cur)
                        cur = None
            elif op == "c" and len(item) >= 5:
                p0 = _pt_xy(item[1])
                p1 = _pt_xy(item[2])
                p2 = _pt_xy(item[3])
                p3 = _pt_xy(item[4])
                if math.hypot(p3[0] - p0[0], p3[1] - p0[1]) <= 40.0:
                    loose_curves.append((p0, p1, p2, p3))
                if cur is None or math.hypot(p0[0] - cur["end"][0], p0[1] - cur["end"][1]) > 1.5:
                    _flush_sub(cur)
                    cur = {"start": p0, "end": p3, "pts": [p0, p1, p2, p3], "verts": [], "n_l": 0, "n_c": 1}
                else:
                    cur["pts"].extend([p1, p2, p3])
                    cur["end"] = p3
                    cur["n_c"] += 1
                    if (
                        math.hypot(p3[0] - cur["start"][0], p3[1] - cur["start"][1]) <= 1.5
                        and (cur["n_l"] + cur["n_c"]) >= 2
                    ):
                        _flush_sub(cur)
                        cur = None
            elif op == "re" and len(item) >= 2:
                _flush_sub(cur)
                cur = None
                r = item[1]
                rx0, ry0, rx1, ry1 = float(r.x0), float(r.y0), float(r.x1), float(r.y1)
                rw, rh = abs(rx1 - rx0), abs(ry1 - ry0)
                if min(rw, rh) <= 2.5 and max(rw, rh) >= 12.0:
                    if rw >= rh:
                        yc = 0.5 * (ry0 + ry1)
                        segments.append((min(rx0, rx1), yc, max(rx0, rx1), yc))
                    else:
                        xc = 0.5 * (rx0 + rx1)
                        segments.append((xc, min(ry0, ry1), xc, max(ry0, ry1)))
            elif op == "qu":
                _flush_sub(cur)
                cur = None
        _flush_sub(cur)

    if not clouds and len(loose_curves) >= 6:
        used = [False] * len(loose_curves)
        for i in range(len(loose_curves)):
            if used[i]:
                continue
            used[i] = True
            cluster = [loose_curves[i]]
            queue = [loose_curves[i]]
            while queue:
                c0 = queue.pop()
                pts_a = (c0[0], c0[3])
                for j in range(len(loose_curves)):
                    if used[j]:
                        continue
                    c1 = loose_curves[j]
                    if min(
                        math.hypot(pa[0] - pb[0], pa[1] - pb[1])
                        for pa in pts_a
                        for pb in (c1[0], c1[3])
                    ) <= 6.5:
                        used[j] = True
                        cluster.append(c1)
                        queue.append(c1)
            if len(cluster) >= 6:
                all_pts = [p for seg in cluster for p in seg]
                xs = [p[0] for p in all_pts]
                ys = [p[1] for p in all_pts]
                x0, x1 = min(xs), max(xs)
                y0, y1 = min(ys), max(ys)
                if max(x1 - x0, y1 - y0) >= 24.0:
                    clouds.append({"bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)]})

    return {
        "bubbles": bubbles,
        "segments": segments,
        "triangles": triangles,
        "clouds": clouds,
    }


def _bubble_has_bisector(bubble, segments):
    """Return True when a roughly horizontal divider line bisects a circle bubble."""
    bx0, by0, bx1, by1 = bubble["bbox"]
    w, h = bubble["w"], bubble["h"]
    for sx0, sy0, sx1, sy1 in segments:
        lo_x, hi_x = min(sx0, sx1), max(sx0, sx1)
        lo_y, hi_y = min(sy0, sy1), max(sy0, sy1)
        if hi_x < bx0 or lo_x > bx1 or hi_y < by0 or lo_y > by1:
            continue
        overlap_x = min(hi_x, bx1) - max(lo_x, bx0)
        mid_y = 0.5 * (sy0 + sy1)
        if (
            abs(sy1 - sy0) <= max(3.0, 0.25 * h)
            and overlap_x >= 0.50 * w
            and (by0 + 0.15 * h) <= mid_y <= (by1 - 0.15 * h)
        ):
            return True
    return False


def _bubble_ray_flags(bubble, segments, pw, ph):
    """Detect orthogonal vertical/horizontal grid lines extending inward from a bubble."""
    bx0, by0, bx1, by1 = bubble["bbox"]
    cx, cy, w, h = bubble["cx"], bubble["cy"], bubble["w"], bubble["h"]
    tol_x = max(6.0, 0.55 * w)
    tol_y = max(6.0, 0.55 * h)
    min_single_v = min(45.0, 0.08 * ph)
    min_single_h = min(45.0, 0.08 * pw)
    min_dash_v = min(60.0, 0.12 * ph)
    min_dash_h = min(60.0, 0.12 * pw)

    v_top_sum = 0.0
    v_top_near = False
    v_bot_sum = 0.0
    v_bot_near = False
    h_left_sum = 0.0
    h_left_near = False
    h_right_sum = 0.0
    h_right_near = False
    has_v_single = False
    has_h_single = False

    for sx0, sy0, sx1, sy1 in segments:
        dx = abs(sx1 - sx0)
        dy = abs(sy1 - sy0)
        if dx <= 3.0 and dy >= 4.0:
            xm = 0.5 * (sx0 + sx1)
            if abs(xm - cx) <= tol_x:
                ylo, yhi = min(sy0, sy1), max(sy0, sy1)
                if yhi > by1 + 12.0:
                    v_top_sum += dy
                    if ylo <= by1 + 32.0:
                        v_top_near = True
                    if dy >= min_single_v and ylo <= by1 + 32.0:
                        has_v_single = True
                if ylo < by0 - 12.0:
                    v_bot_sum += dy
                    if yhi >= by0 - 32.0:
                        v_bot_near = True
                    if dy >= min_single_v and yhi >= by0 - 32.0:
                        has_v_single = True
        if dy <= 3.0 and dx >= 4.0:
            ym = 0.5 * (sy0 + sy1)
            if abs(ym - cy) <= tol_y:
                xlo, xhi = min(sx0, sx1), max(sx0, sx1)
                if xhi > bx1 + 12.0:
                    h_left_sum += dx
                    if xlo <= bx1 + 32.0:
                        h_left_near = True
                    if dx >= min_single_h and xlo <= bx1 + 32.0:
                        has_h_single = True
                if xlo < bx0 - 12.0:
                    h_right_sum += dx
                    if xhi >= bx0 - 32.0:
                        h_right_near = True
                    if dx >= min_single_h and xhi >= bx0 - 32.0:
                        has_h_single = True

    has_v = has_v_single or (v_top_near and v_top_sum >= min_dash_v) or (v_bot_near and v_bot_sum >= min_dash_v)
    has_h = has_h_single or (h_left_near and h_left_sum >= min_dash_h) or (h_right_near and h_right_sum >= min_dash_h)
    return has_v, has_h


def _longest_monotonic_chain(cands, reverse_order=False):
    """Select longest strictly monotonic subsequence by _grid_natural_key."""
    n = len(cands)
    if n < 2:
        return []
    keys = [_grid_natural_key(c["label"]) for c in cands]
    dp_len = [1] * n
    dp_ray = [1 if c["has_ray"] else 0 for c in cands]
    parent = [-1] * n
    for i in range(n):
        for j in range(i):
            if keys[j][0] != keys[i][0]:
                continue
            ok = (keys[j] > keys[i]) if reverse_order else (keys[j] < keys[i])
            if ok:
                cand_score = (dp_len[j] + 1, dp_ray[j] + (1 if cands[i]["has_ray"] else 0))
                cur_score = (dp_len[i], dp_ray[i])
                if cand_score > cur_score:
                    dp_len[i] = cand_score[0]
                    dp_ray[i] = cand_score[1]
                    parent[i] = j
    best_i = max(range(n), key=lambda idx: (dp_len[idx], dp_ray[idx]))
    if dp_len[best_i] < 2:
        return []
    chain = []
    cur = best_i
    while cur != -1:
        chain.append(cands[cur])
        cur = parent[cur]
    chain.reverse()
    return chain


def _consolidate_axis_chains(band_lists, dim_pt, axis_kind):
    """Cluster collinear perimeter bubbles, run monotonic LIS, and separate primary vs secondary."""
    chains = []
    for cands in band_lists:
        if len(cands) < 2:
            continue
        ortho_sorted = sorted(cands, key=lambda c: c["ortho_pt"])
        ortho_clusters = []
        for item in ortho_sorted:
            tol = max(14.0, 0.75 * item["diam"])
            if ortho_clusters and abs(item["ortho_pt"] - ortho_clusters[-1]["ref"]) <= tol:
                cl = ortho_clusters[-1]
                cl["items"].append(item)
                cl["ref"] = sum(x["ortho_pt"] for x in cl["items"]) / len(cl["items"])
            else:
                ortho_clusters.append({"ref": item["ortho_pt"], "items": [item]})

        for cl in ortho_clusters:
            by_fam = {}
            for item in cl["items"]:
                by_fam.setdefault(item["family"], []).append(item)
            for fam_items in by_fam.values():
                fam_sorted = sorted(fam_items, key=lambda c: c["coord_pt"])
                deduped = []
                for it in fam_sorted:
                    if deduped and abs(it["coord_pt"] - deduped[-1]["coord_pt"]) <= 8.0:
                        if it["has_ray"] and not deduped[-1]["has_ray"]:
                            deduped[-1] = it
                    else:
                        deduped.append(it)
                if len(deduped) < 2:
                    continue
                inc_chain = _longest_monotonic_chain(deduped, reverse_order=False)
                best_chain = inc_chain
                if axis_kind == "y":
                    dec_chain = _longest_monotonic_chain(deduped, reverse_order=True)
                    inc_score = (sum(1 for c in inc_chain if c["has_ray"]), len(inc_chain))
                    dec_score = (sum(1 for c in dec_chain if c["has_ray"]), len(dec_chain))
                    if dec_score > inc_score:
                        best_chain = dec_chain
                if len(best_chain) >= 2:
                    ordered = sorted(best_chain, key=lambda c: _grid_natural_key(c["label"]))
                    chains.append(ordered)

    if not chains:
        return [], []

    # Merge opposite-margin chains belonging to the same physical grid family
    merged_groups = []
    for ch in chains:
        ch_map = {c["label"]: c for c in ch}
        placed = False
        for grp in merged_groups:
            shared = set(ch_map.keys()) & set(grp.keys())
            if shared:
                max_diff = max(abs(ch_map[k]["coord_pt"] - grp[k]["coord_pt"]) for k in shared)
                if max_diff <= max(20.0, 0.02 * dim_pt) and (
                    len(shared) >= max(2, min(len(ch_map), len(grp)) // 2)
                ):
                    for k, item in ch_map.items():
                        if k in grp:
                            ex = grp[k]
                            n_b = len(ex["bubble_bboxes"])
                            ex["coord_pt"] = (ex["coord_pt"] * n_b + item["coord_pt"]) / float(n_b + 1)
                            ex["bubble_bboxes"].extend(item["bubble_bboxes"])
                            ex["has_ray"] = bool(ex["has_ray"] or item["has_ray"])
                        else:
                            grp[k] = dict(item, bubble_bboxes=list(item["bubble_bboxes"]))
                    placed = True
                    break
        if not placed:
            merged_groups.append(
                {c["label"]: dict(c, bubble_bboxes=list(c["bubble_bboxes"])) for c in ch}
            )

    formatted = []
    for grp in merged_groups:
        items = sorted(grp.values(), key=lambda c: _grid_natural_key(c["label"]))
        ray_cnt = sum(1 for c in items if c["has_ray"])
        span = (max(c["coord_pt"] for c in items) - min(c["coord_pt"] for c in items)) / max(1.0, dim_pt)
        entries = [
            {
                "label": c["label"],
                "coord_pt": round(c["coord_pt"], 2),
                "coord_norm": round(max(0.0, min(1.0, (c["coord_pt"] - c["origin_pt"]) / max(1.0, dim_pt))), 4),
                "bubble_bboxes": c["bubble_bboxes"],
                "has_ray": bool(c["has_ray"]),
            }
            for c in items
        ]
        formatted.append(((1 if ray_cnt > 0 else 0, ray_cnt, len(entries), round(span, 3)), entries))

    formatted.sort(key=lambda x: x[0], reverse=True)
    primary = formatted[0][1]
    secondary = formatted[1][1] if len(formatted) > 1 else []
    return primary, secondary


def extract_grid_axes(page, drawings=None, atoms=None):
    """Detect perimeter circular/octagonal grid bubbles, natural-sort axes, and reject keynotes."""
    rx0 = float(page.rect.x0)
    ry0 = float(page.rect.y0)
    pw = max(1.0, float(abs(page.rect.width)))
    ph = max(1.0, float(abs(page.rect.height)))

    if drawings is None:
        drawings = _safe_probe_drawings(page)
    if atoms is None:
        atoms = _extract_clean_text_atoms(page)

    prims = _extract_vector_primitives(drawings)
    bubbles = prims["bubbles"]
    segments = prims["segments"]

    top_cands = []
    bot_cands = []
    left_cands = []
    right_cands = []

    for b in bubbles:
        bx0, by0, bx1, by1 = b["bbox"]
        cx, cy, w, h = b["cx"], b["cy"], b["w"], b["h"]
        nx_c = (cx - rx0) / pw
        ny_c = (cy - ry0) / ph

        in_top = ny_c <= 0.26
        in_bot = ny_c >= 0.74
        in_left = nx_c <= 0.26
        in_right = nx_c >= 0.74
        if not (in_top or in_bot or in_left or in_right):
            continue

        if _bubble_has_bisector(b, segments):
            continue

        inside_atoms = []
        has_inline_note = False
        for a in atoms or ():
            ax0, ay0, ax1, ay1 = float(a["x0"]), float(a["y0"]), float(a["x1"]), float(a["y1"])
            axc = 0.5 * (ax0 + ax1)
            ayc = 0.5 * (ay0 + ay1)
            if (bx0 - 2.0) <= axc <= (bx1 + 2.0) and (by0 - 2.0) <= ayc <= (by1 + 2.0):
                if (ax1 - ax0) <= max(w + 12.0, 2.2 * w):
                    inside_atoms.append(a)
            elif (
                ax0 > bx1
                and (ax0 - bx1) <= 45.0
                and abs(ayc - cy) <= max(10.0, 0.75 * h)
                and len((a.get("text") or "").strip()) >= 8
            ):
                has_inline_note = True

        if not inside_atoms:
            continue
        if len(inside_atoms) == 1:
            lbl = (inside_atoms[0].get("text") or "").strip()
        else:
            ys = [0.5 * (float(a["y0"]) + float(a["y1"])) for a in inside_atoms]
            if (max(ys) - min(ys)) > 4.0:
                continue
            inside_atoms.sort(key=lambda a: float(a["x0"]))
            lbl = "".join((a.get("text") or "").strip() for a in inside_atoms)

        if not lbl or SHEET_ID_RE.search(lbl) or not GRID_LABEL_RE.match(lbl):
            continue

        has_v_ray, has_h_ray = _bubble_ray_flags(b, segments, pw, ph)
        if has_inline_note and not (has_v_ray or has_h_ray):
            continue

        fam = "numeric" if lbl[0].isdigit() else "alpha"
        diam = 0.5 * (w + h)

        def _mk(coord_pt, origin_pt, ortho_pt, has_ray):
            return {
                "label": lbl,
                "family": fam,
                "coord_pt": coord_pt,
                "origin_pt": origin_pt,
                "ortho_pt": ortho_pt,
                "diam": diam,
                "nx_c": nx_c,
                "ny_c": ny_c,
                "bubble_bboxes": [b["bbox"]],
                "has_ray": has_ray,
            }

        assign_x = in_top or in_bot
        assign_y = in_left or in_right
        if assign_x and assign_y:
            if has_v_ray and not has_h_ray:
                assign_y = False
            elif has_h_ray and not has_v_ray:
                assign_x = False

        if assign_x:
            if not (nx_c >= 0.72 and not has_v_ray):
                item_x = _mk(cx, rx0, cy, has_v_ray)
                if in_top:
                    top_cands.append(item_x)
                else:
                    bot_cands.append(item_x)
        if assign_y:
            item_y = _mk(cy, ry0, cx, has_h_ray)
            if in_left:
                left_cands.append(item_y)
            else:
                right_cands.append(item_y)

    # Disambiguate right-sidebar circled keynotes: require ray OR matching left-band bubble
    left_refs = {(c["label"], round(c["coord_pt"], 0)) for c in left_cands}
    filtered_right = []
    for rc in right_cands:
        if rc["has_ray"]:
            filtered_right.append(rc)
        elif any(lbl == rc["label"] and abs(lcy - rc["coord_pt"]) <= 18.0 for lbl, lcy in left_refs):
            filtered_right.append(rc)

    x_primary, x_secondary = _consolidate_axis_chains([top_cands, bot_cands], pw, "x")
    y_primary, y_secondary = _consolidate_axis_chains([left_cands, filtered_right], ph, "y")

    secondary_axes = {}
    if x_secondary:
        secondary_axes["x"] = x_secondary
    if y_secondary:
        secondary_axes["y"] = y_secondary

    all_items = x_primary + y_primary
    if not all_items:
        confidence = 0.0
    else:
        base_cov = (0.30 if x_primary else 0.0) + (0.30 if y_primary else 0.0)
        if not (x_primary and y_primary):
            base_cov = 0.40
        ray_ratio = sum(1 for it in all_items if it["has_ray"]) / float(len(all_items))
        mult_bonus = min(1.0, len(all_items) / 6.0)
        confidence = round(min(1.0, base_cov + 0.25 * ray_ratio + 0.15 * mult_bonus), 4)

    return {
        "x": x_primary,
        "y": y_primary,
        "x_labels": [it["label"] for it in x_primary],
        "y_labels": [it["label"] for it in y_primary],
        "confidence": confidence,
        "secondary_axes": secondary_axes,
    }


def _resolve_1d_axis(val, axis_items, snap_tol_norm=0.008):
    """Resolve 1D normalized coordinate along an axis with bracketed margin support."""
    if not axis_items:
        return None
    ordered = sorted(axis_items, key=lambda it: float(it["coord_norm"]))
    if len(ordered) == 1:
        if abs(val - float(ordered[0]["coord_norm"])) <= snap_tol_norm:
            return ordered[0]["label"]
        return None

    coords = [float(it["coord_norm"]) for it in ordered]
    deltas = sorted(abs(coords[i + 1] - coords[i]) for i in range(len(coords) - 1))
    delta_med = deltas[len(deltas) // 2]
    margin = 0.5 * delta_med
    if val < (coords[0] - margin) or val > (coords[-1] + margin):
        return None

    best_idx = min(range(len(ordered)), key=lambda i: abs(val - coords[i]))
    if abs(val - coords[best_idx]) <= snap_tol_norm:
        return ordered[best_idx]["label"]

    if val < coords[0]:
        return ordered[0]["label"]
    if val > coords[-1]:
        return ordered[-1]["label"]

    for i in range(len(ordered) - 1):
        if coords[i] <= val <= coords[i + 1]:
            l_a, l_b = sorted(
                [ordered[i]["label"], ordered[i + 1]["label"]],
                key=_grid_natural_key,
            )
            return f"{l_a}-{l_b}"
    return None


def resolve_grid_ref(norm_bbox, grid_axes, snap_tol_norm: float = 0.008):
    """Resolve normalized bbox/point onto structural grid coordinates with CHK-03 bracket."""
    if not norm_bbox or not isinstance(grid_axes, dict):
        return None
    if len(norm_bbox) == 4:
        nx = 0.5 * (float(norm_bbox[0]) + float(norm_bbox[2]))
        ny = 0.5 * (float(norm_bbox[1]) + float(norm_bbox[3]))
    elif len(norm_bbox) == 2:
        nx, ny = float(norm_bbox[0]), float(norm_bbox[1])
    else:
        return None

    x_items = grid_axes.get("x") or []
    y_items = grid_axes.get("y") or []
    if not x_items and not y_items:
        return None

    rx = _resolve_1d_axis(nx, x_items, snap_tol_norm=snap_tol_norm) if x_items else None
    ry = _resolve_1d_axis(ny, y_items, snap_tol_norm=snap_tol_norm) if y_items else None

    if x_items and y_items:
        if rx is None or ry is None:
            return None
        return f"{rx} / {ry}"
    return rx if x_items else ry


def _callout_kind_from_prefix(prefix):
    """Map callout prefix token to canonical edge kind."""
    p = (prefix or "").upper()
    if p.startswith("SEC"):
        return "section"
    if p.startswith("EL"):
        return "elevation"
    return "detail"


def extract_sheet_callouts(
    page, atoms=None, drawings=None, grid_axes=None, tile_grid: str = "4x4"
):
    """Extract primary_sheet_id, cross-sheet detail/section callouts, and revision deltas."""
    cols, rows = _parse_tile_grid(tile_grid)
    rx0 = float(page.rect.x0)
    ry0 = float(page.rect.y0)
    pw = max(1.0, float(abs(page.rect.width)))
    ph = max(1.0, float(abs(page.rect.height)))

    if drawings is None:
        drawings = _safe_probe_drawings(page)
    if atoms is None:
        atoms = _extract_clean_text_atoms(page)

    prims = _extract_vector_primitives(drawings)
    callouts = []
    revision_deltas = []
    seen_callout_keys = set()
    bisected_atom_ids = set()

    def _norm_pt_bbox(bx0, by0, bx1, by1):
        nx0 = round(max(0.0, min(1.0, (bx0 - rx0) / pw)), 4)
        ny0 = round(max(0.0, min(1.0, (by0 - ry0) / ph)), 4)
        nx1 = round(max(0.0, min(1.0, (bx1 - rx0) / pw)), 4)
        ny1 = round(max(0.0, min(1.0, (by1 - ry0) / ph)), 4)
        tid = _tile_id_from_norm_point(0.5 * (nx0 + nx1), 0.5 * (ny0 + ny1), cols=cols, rows=rows)
        gref = resolve_grid_ref([nx0, ny0, nx1, ny1], grid_axes) if grid_axes else None
        return [nx0, ny0, nx1, ny1], [round(bx0, 2), round(by0, 2), round(bx1, 2), round(by1, 2)], tid, gref

    # 1. Stacked bisected circle callouts ("3" over divider line over "S-501")
    for b in prims["bubbles"]:
        if not _bubble_has_bisector(b, prims["segments"]):
            continue
        bx0, by0, bx1, by1 = b["bbox"]
        inside = []
        for idx, a in enumerate(atoms or ()):
            axc = 0.5 * (float(a["x0"]) + float(a["x1"]))
            ayc = 0.5 * (float(a["y0"]) + float(a["y1"]))
            if (bx0 - 3.0) <= axc <= (bx1 + 3.0) and (by0 - 3.0) <= ayc <= (by1 + 3.0):
                inside.append((idx, ayc, a))
        if not inside:
            continue
        for idx, _, _ in inside:
            bisected_atom_ids.add(idx)
        inside.sort(key=lambda x: x[1])
        detail_no = None
        target_sheet = None
        raw_txt = " ".join((x[2].get("text") or "").strip() for x in inside).strip()
        if len(inside) >= 2:
            top_txt = (inside[0][2].get("text") or "").strip().upper()
            bot_txt = (inside[-1][2].get("text") or "").strip().upper()
            m_sid = SHEET_ID_RE.search(bot_txt)
            if m_sid and re.match(r"^[A-Z0-9]{1,4}$", top_txt):
                detail_no = top_txt
                target_sheet = m_sid.group(1)
        if not target_sheet:
            m_combo = re.search(
                r"\b([A-Z0-9]{1,4})\s*[/\s]\s*([A-Z]{1,3}-\d{1,4}(?:\.\d+)?)\b",
                raw_txt.upper(),
            )
            if m_combo:
                detail_no = m_combo.group(1)
                target_sheet = m_combo.group(2)
        if target_sheet:
            nb, pb, tid, gref = _norm_pt_bbox(bx0, by0, bx1, by1)
            ckey = ("detail", detail_no or "", target_sheet, tid)
            if ckey not in seen_callout_keys:
                seen_callout_keys.add(ckey)
                callouts.append(
                    {
                        "kind": "detail",
                        "detail_no": detail_no,
                        "target_sheet": target_sheet,
                        "text": raw_txt,
                        "norm_bbox": nb,
                        "pt_bbox": pb,
                        "tile_id": tid,
                        "grid_ref": gref,
                    }
                )

    # 2. Text-based detail/section/elevation/reference callouts + title-block sheet scoring
    sheet_scores = {}
    for idx, a in enumerate(atoms or ()):
        txt = (a.get("text") or "").strip()
        if not txt:
            continue
        ax0, ay0, ax1, ay1 = float(a["x0"]), float(a["y0"]), float(a["x1"]), float(a["y1"])
        nb, pb, tid, gref = _norm_pt_bbox(ax0, ay0, ax1, ay1)
        txt_up = txt.upper()

        matched_ref_spans = False
        if idx not in bisected_atom_ids:
            for m in DETAIL_SLASH_CALLOUT_RE.finditer(txt_up):
                kind = _callout_kind_from_prefix(m.group(1))
                dno = m.group(2).strip()
                tgt = m.group(3).strip()
                matched_ref_spans = True
                ckey = (kind, dno, tgt, tid)
                if ckey not in seen_callout_keys:
                    seen_callout_keys.add(ckey)
                    callouts.append(
                        {
                            "kind": kind,
                            "detail_no": dno,
                            "target_sheet": tgt,
                            "text": txt[:140],
                            "norm_bbox": nb,
                            "pt_bbox": pb,
                            "tile_id": tid,
                            "grid_ref": gref,
                        }
                    )
            for m in DETAIL_ON_SHEET_RE.finditer(txt_up):
                kind = _callout_kind_from_prefix(m.group(1))
                tgt = m.group(2).strip()
                matched_ref_spans = True
                ckey = (kind, "", tgt, tid)
                if ckey not in seen_callout_keys:
                    seen_callout_keys.add(ckey)
                    callouts.append(
                        {
                            "kind": kind,
                            "detail_no": None,
                            "target_sheet": tgt,
                            "text": txt[:140],
                            "norm_bbox": nb,
                            "pt_bbox": pb,
                            "tile_id": tid,
                            "grid_ref": gref,
                        }
                    )
            for m in SEE_SHEET_CALLOUT_RE.finditer(txt_up):
                tgt = m.group(1).strip()
                matched_ref_spans = True
                ckey = ("reference", "", tgt, tid)
                if ckey not in seen_callout_keys:
                    seen_callout_keys.add(ckey)
                    callouts.append(
                        {
                            "kind": "reference",
                            "detail_no": None,
                            "target_sheet": tgt,
                            "text": txt[:140],
                            "norm_bbox": nb,
                            "pt_bbox": pb,
                            "tile_id": tid,
                            "grid_ref": gref,
                        }
                    )

        # Revision markers in text
        for m_rev in REV_MARKER_RE.finditer(txt):
            rev_id = next((g for g in m_rev.groups() if g), None)
            rev_kind = "addendum" if "ADDENDUM" in m_rev.group(0).upper() else "revision_tag"
            revision_deltas.append(
                {
                    "kind": rev_kind,
                    "rev_id": rev_id.upper() if rev_id else None,
                    "text": m_rev.group(0).strip(),
                    "norm_bbox": nb,
                    "pt_bbox": pb,
                    "tile_id": tid,
                    "grid_ref": gref,
                }
            )

        # Score candidate primary_sheet_id outside callout/bisected atoms
        if idx in bisected_atom_ids or matched_ref_spans:
            continue
        is_ref_ctx = bool(
            re.search(r"\b(?:SEE|REF|REFER|DETAIL|DTL|SEC|SECT|SECTION|ELEV)\b", txt_up)
        )
        if is_ref_ctx:
            continue
        for m_sid in SHEET_ID_RE.finditer(txt_up):
            sid = m_sid.group(1)
            sc = 1.0
            if nb[0] >= 0.60 and nb[1] >= 0.65:
                sc += 10.0
            elif nb[0] >= 0.72 or nb[1] >= 0.80:
                sc += 6.0
            if re.search(
                r"\b(?:SHEET|SHT|DWG|DRAWING)\s*(?:NO\.?\s*[:\-]?\s*)?" + re.escape(sid) + r"\b",
                txt_up,
            ):
                sc += 8.0
            fsize = float(a.get("size") or 10.0)
            if fsize >= 11.5:
                sc += 2.0 * min(3.0, fsize / 12.0)
            if sc > sheet_scores.get(sid, 0.0):
                sheet_scores[sid] = sc

    # 3. Vector delta triangles & revision cloud contours
    for tri in prims["triangles"]:
        tx0, ty0, tx1, ty1 = tri["bbox"]
        tag = None
        for a in atoms or ():
            axc = 0.5 * (float(a["x0"]) + float(a["x1"]))
            ayc = 0.5 * (float(a["y0"]) + float(a["y1"]))
            if (tx0 - 3.0) <= axc <= (tx1 + 3.0) and (ty0 - 3.0) <= ayc <= (ty1 + 3.0):
                t_cand = (a.get("text") or "").strip().upper()
                if re.match(r"^[A-Z0-9]{1,3}$", t_cand):
                    tag = t_cand
                    break
        if tag is not None:
            nb, pb, tid, gref = _norm_pt_bbox(tx0, ty0, tx1, ty1)
            if not any(
                d.get("rev_id") == tag and d.get("tile_id") == tid for d in revision_deltas
            ):
                revision_deltas.append(
                    {
                        "kind": "delta_triangle",
                        "rev_id": tag,
                        "text": f"\u0394{tag}",
                        "norm_bbox": nb,
                        "pt_bbox": pb,
                        "tile_id": tid,
                        "grid_ref": gref,
                    }
                )

    for cld in prims["clouds"]:
        cx0, cy0, cx1, cy1 = cld["bbox"]
        nb, pb, tid, gref = _norm_pt_bbox(cx0, cy0, cx1, cy1)
        attached_rev = None
        for rd in revision_deltas:
            rb = rd.get("pt_bbox") or []
            if len(rb) == 4 and not (
                rb[2] < cx0 - 36.0 or rb[0] > cx1 + 36.0 or rb[3] < cy0 - 36.0 or rb[1] > cy1 + 36.0
            ):
                attached_rev = rd.get("rev_id")
                break
        revision_deltas.append(
            {
                "kind": "revision_cloud",
                "rev_id": attached_rev,
                "text": f"CLOUD {attached_rev}" if attached_rev else "REVISION CLOUD",
                "norm_bbox": nb,
                "pt_bbox": pb,
                "tile_id": tid,
                "grid_ref": gref,
            }
        )

    primary_sheet_id = (
        max(sheet_scores.keys(), key=lambda s: sheet_scores[s])
        if sheet_scores
        else None
    )
    return {
        "primary_sheet_id": primary_sheet_id,
        "callouts": callouts,
        "revision_deltas": revision_deltas,
    }


def build_callout_graph(spatial_pages: list):
    """Build cross-sheet callout graph mapping sheet IDs to 1-based pages and unresolved targets."""
    sheets = {}
    for sp in spatial_pages or ():
        if not isinstance(sp, dict):
            continue
        p_num = int(sp.get("page", 1))
        psid = sp.get("primary_sheet_id")
        if psid:
            sid_norm = str(psid).strip().upper()
            if sid_norm and sid_norm not in sheets:
                sheets[sid_norm] = p_num

    edges = []
    dangling = set()
    for sp in spatial_pages or ():
        if not isinstance(sp, dict):
            continue
        p_num = int(sp.get("page", 1))
        psid = sp.get("primary_sheet_id")
        from_sheet = str(psid).strip().upper() if psid else None
        for c in sp.get("callouts") or ():
            if not isinstance(c, dict):
                continue
            target = str(c.get("target_sheet") or "").strip().upper()
            if not target:
                continue
            resolved = target in sheets
            if not resolved:
                dangling.add(target)
            edges.append(
                {
                    "from_sheet": from_sheet,
                    "from_page": p_num,
                    "target_sheet": target,
                    "detail_no": c.get("detail_no"),
                    "kind": c.get("kind", "reference"),
                    "resolved": resolved,
                }
            )

    return {
        "sheets": sheets,
        "edges": edges,
        "dangling_targets": sorted(dangling),
    }


def _parse_tile_grid(tile_grid="4x4"):
    """Parse grid spec like '4x4' or '3x2' into (cols, rows)."""
    raw = str(tile_grid or "4x4").strip().lower()
    m = re.match(r"^(\d+)\s*[x×]\s*(\d+)$", raw)
    if not m:
        raise ValueError(
            f"Invalid --tile-grid {tile_grid!r}; expected 'CxR' like '4x4' or '3x2'."
        )
    cols = max(1, min(12, int(m.group(1))))
    rows = max(1, min(12, int(m.group(2))))
    return cols, rows


def _col_index_to_letters(idx):
    """Convert 0-based column index to spreadsheet label (A, B, ..., Z, AA)."""
    out = []
    n = int(idx)
    while True:
        out.append(chr(ord("A") + (n % 26)))
        n = n // 26 - 1
        if n < 0:
            break
    return "".join(reversed(out))


def _tile_id_from_norm_point(nx, ny, cols=4, rows=4):
    """Return canonical tile id (e.g. 'A1'..'D4') for normalized coordinates."""
    ci = min(cols - 1, max(0, int(max(0.0, min(0.999999, nx)) * cols)))
    ri = min(rows - 1, max(0, int(max(0.0, min(0.999999, ny)) * rows)))
    return f"{_col_index_to_letters(ci)}{ri + 1}"


def _norm_bbox_from_tile(tile_id, cols=4, rows=4):
    """Parse tile cell id like 'B2' into [nx0, ny0, nx1, ny1]."""
    m = re.match(r"^\s*([A-Za-z]+)(\d+)\s*$", str(tile_id or ""))
    if not m:
        raise ValueError(f"Invalid tile coordinate {tile_id!r}; expected e.g. 'B2'.")
    col_str, row_str = m.group(1).upper(), int(m.group(2))
    col_idx = 0
    for ch in col_str:
        col_idx = col_idx * 26 + (ord(ch) - ord("A") + 1)
    col_idx -= 1
    row_idx = row_str - 1
    if not (0 <= col_idx < cols and 0 <= row_idx < rows):
        raise ValueError(
            f"Tile {tile_id!r} out of range for {cols}x{rows} grid."
        )
    return [
        round(col_idx / float(cols), 6),
        round(row_idx / float(rows), 6),
        round((col_idx + 1) / float(cols), 6),
        round((row_idx + 1) / float(rows), 6),
    ]


def extract_spatial_cad_index(
    page, tile_grid="4x4", blocks=None, tables=None, regime_info=None
):
    """Extract canonical A1..D4 spatial CAD callout index, tiles, and hints."""
    cols, rows = _parse_tile_grid(tile_grid)
    if regime_info is None:
        regime_info = classify_page_regime(page)
    regime_clean = {
        k: v for k, v in regime_info.items() if not str(k).startswith("_")
    }

    rx0 = float(page.rect.x0)
    ry0 = float(page.rect.y0)
    pw = max(1.0, float(abs(page.rect.width)))
    ph = max(1.0, float(abs(page.rect.height)))

    atoms = (
        _extract_clean_text_atoms(page, blocks=blocks)
        if blocks is not None
        else (regime_info.get("_atoms") or _extract_clean_text_atoms(page))
    )
    drawings = regime_info.get("_drawings")
    if drawings is None:
        drawings = _safe_probe_drawings(page)

    grid_axes = extract_grid_axes(page, drawings=drawings, atoms=atoms)
    callout_info = extract_sheet_callouts(
        page,
        atoms=atoms,
        drawings=drawings,
        grid_axes=grid_axes,
        tile_grid=f"{cols}x{rows}",
    )

    tiles = OrderedDict()
    for r_i in range(rows):
        for c_i in range(cols):
            tid = f"{_col_index_to_letters(c_i)}{r_i + 1}"
            nx0 = c_i / float(cols)
            ny0 = r_i / float(rows)
            nx1 = (c_i + 1) / float(cols)
            ny1 = (r_i + 1) / float(rows)
            tiles[tid] = {
                "tile_id": tid,
                "norm_bbox": [round(nx0, 4), round(ny0, 4), round(nx1, 4), round(ny1, 4)],
                "pt_bbox": [
                    round(rx0 + nx0 * pw, 2),
                    round(ry0 + ny0 * ph, 2),
                    round(rx0 + nx1 * pw, 2),
                    round(ry0 + ny1 * ph, 2),
                ],
                "block_count": 0,
                "sample_labels": [],
            }

    localized_blocks = []
    titleblock_hints = []
    legend_hints = []
    sheet_ids = set()

    for idx, a in enumerate(atoms):
        nx0 = round(max(0.0, min(1.0, (a["x0"] - rx0) / pw)), 4)
        ny0 = round(max(0.0, min(1.0, (a["y0"] - ry0) / ph)), 4)
        nx1 = round(max(0.0, min(1.0, (a["x1"] - rx0) / pw)), 4)
        ny1 = round(max(0.0, min(1.0, (a["y1"] - ry0) / ph)), 4)
        cx = 0.5 * (nx0 + nx1)
        cy = 0.5 * (ny0 + ny1)
        tid = _tile_id_from_norm_point(cx, cy, cols=cols, rows=rows)
        txt = a["text"]
        entry = {
            "id": idx + 1,
            "text": txt,
            "norm_bbox": [nx0, ny0, nx1, ny1],
            "pt_bbox": [round(a["x0"], 2), round(a["y0"], 2), round(a["x1"], 2), round(a["y1"], 2)],
            "tile_id": tid,
        }
        if "dir" in a:
            entry["dir"] = a["dir"]
        gref = resolve_grid_ref([nx0, ny0, nx1, ny1], grid_axes)
        if gref:
            entry["grid_ref"] = gref
        localized_blocks.append(entry)

        t_rec = tiles[tid]
        t_rec["block_count"] += 1
        if len(t_rec["sample_labels"]) < 8:
            t_rec["sample_labels"].append(txt[:80])

        for sid in SHEET_ID_RE.findall(txt):
            sheet_ids.add(sid)

        if (nx0 >= 0.65 and ny0 >= 0.65) or re.search(
            r"(?:SHEET|SCALE|REV|DRAWING|รวมทั้งหมด|มาตราส่วน)", txt, re.IGNORECASE
        ):
            if len(titleblock_hints) < 12:
                titleblock_hints.append(
                    {"text": txt[:120], "norm_bbox": [nx0, ny0, nx1, ny1], "tile_id": tid}
                )
        if LEGEND_LINE_RE.match(txt) and len(legend_hints) < 25:
            legend_hints.append(
                {"text": txt[:120], "norm_bbox": [nx0, ny0, nx1, ny1], "tile_id": tid}
            )

    aligned_tabs = _extract_aligned_block_tables(
        page, blocks=blocks, atoms=None if blocks is not None else atoms
    )
    out_tables = []
    seen_sigs = set()

    for tab in tables or []:
        rows_data = tab["rows"] if isinstance(tab, dict) else tab
        if not rows_data:
            continue
        sig = tuple(tuple(r) for r in rows_data[:4])
        seen_sigs.add(sig)
        t_item = {
            "rows": rows_data,
            "nrows": len(rows_data),
            "ncols": max((len(r) for r in rows_data), default=0),
            "markdown": rows_to_markdown(rows_data),
            "source": tab.get("source", "vector_grid") if isinstance(tab, dict) else "vector_grid",
        }
        if isinstance(tab, dict) and "norm_bbox" in tab:
            t_item["norm_bbox"] = tab["norm_bbox"]
            t_item["bbox"] = tab.get("bbox")
            nb = tab["norm_bbox"]
            t_item["tile_id"] = _tile_id_from_norm_point(
                0.5 * (nb[0] + nb[2]), 0.5 * (nb[1] + nb[3]), cols=cols, rows=rows
            )
            gref = resolve_grid_ref(nb, grid_axes)
            if gref:
                t_item["grid_ref"] = gref
        if isinstance(tab, dict):
            for mk in ("col_bounds_norm", "raw_col_bounds_norm", "keep_cols"):
                if mk in tab:
                    t_item[mk] = tab[mk]
        out_tables.append(t_item)

    for at in aligned_tabs:
        sig = tuple(tuple(r) for r in at["rows"][:4])
        if sig in seen_sigs:
            continue
        seen_sigs.add(sig)
        nb = at["norm_bbox"]
        t_item = {
            "bbox": at["bbox"],
            "norm_bbox": nb,
            "tile_id": _tile_id_from_norm_point(
                0.5 * (nb[0] + nb[2]), 0.5 * (nb[1] + nb[3]), cols=cols, rows=rows
            ),
            "col_bounds_norm": at.get("col_bounds_norm"),
            "raw_col_bounds_norm": at.get("raw_col_bounds_norm"),
            "keep_cols": at.get("keep_cols"),
            "rows": at["rows"],
            "nrows": at["nrows"],
            "ncols": at["ncols"],
            "markdown": rows_to_markdown(at["rows"]),
            "source": "aligned_blocks",
        }
        gref = resolve_grid_ref(nb, grid_axes)
        if gref:
            t_item["grid_ref"] = gref
        out_tables.append(t_item)

    page_num = getattr(page, "number", 0) + 1
    return {
        "page": page_num,
        "page_width_pt": round(pw, 2),
        "page_height_pt": round(ph, 2),
        "tile_grid": f"{cols}x{rows}",
        "regime": regime_clean["regime"],
        "regime_info": regime_clean,
        "primary_sheet_id": callout_info["primary_sheet_id"],
        "sheet_id_hints": sorted(sheet_ids),
        "grid_axes": grid_axes,
        "callouts": callout_info["callouts"],
        "revision_deltas": callout_info["revision_deltas"],
        "titleblock_hints": titleblock_hints,
        "legend_hints": legend_hints,
        "tiles": tiles,
        "blocks": localized_blocks,
        "tables": out_tables,
    }


def _resolve_page_rect_bounds(page_rect):
    """Normalize fitz.Rect, (x0, y0, x1, y1), or (w, h) into (rx0, ry0, pw, ph)."""
    if hasattr(page_rect, "x0") and hasattr(page_rect, "width"):
        return (
            float(page_rect.x0),
            float(page_rect.y0),
            max(1.0, abs(float(page_rect.width))),
            max(1.0, abs(float(page_rect.height))),
        )
    if isinstance(page_rect, (tuple, list)):
        if len(page_rect) == 4:
            rx0, ry0, x1, y1 = [float(v) for v in page_rect]
            return rx0, ry0, max(1.0, abs(x1 - rx0)), max(1.0, abs(y1 - ry0))
        if len(page_rect) == 2:
            return 0.0, 0.0, max(1.0, float(page_rect[0])), max(1.0, float(page_rect[1]))
    return 0.0, 0.0, 1.0, 1.0


def compute_unexplained_canvas_bbox(page_rect, atoms, tables=None, drawing_stats=None):
    """Compute normalized canvas ROI excluding dense sidebar legends or titleblocks."""
    del drawing_stats
    rx0, ry0, pw, ph = _resolve_page_rect_bounds(page_rect)

    norm_atoms = []
    for a in atoms or []:
        if not isinstance(a, dict):
            continue
        txt = str(a.get("text") or "").strip()
        if not txt:
            continue
        nx0 = max(0.0, min(1.0, (float(a["x0"]) - rx0) / pw))
        ny0 = max(0.0, min(1.0, (float(a["y0"]) - ry0) / ph))
        nx1 = max(0.0, min(1.0, (float(a["x1"]) - rx0) / pw))
        ny1 = max(0.0, min(1.0, (float(a["y1"]) - ry0) / ph))
        norm_atoms.append(
            (nx0, ny0, nx1, ny1, 0.5 * (nx0 + nx1), 0.5 * (ny0 + ny1), len(txt))
        )

    if not norm_atoms and tables:
        for tab in tables:
            if not isinstance(tab, dict):
                continue
            nb = tab.get("norm_bbox")
            if not nb or len(nb) != 4:
                continue
            rows_data = tab.get("rows") or []
            flat_len = sum(len(str(c or "").strip()) for r in rows_data for c in r)
            if flat_len > 0:
                nx0, ny0, nx1, ny1 = [max(0.0, min(1.0, float(v))) for v in nb]
                norm_atoms.append(
                    (nx0, ny0, nx1, ny1, 0.5 * (nx0 + nx1), 0.5 * (ny0 + ny1), flat_len)
                )

    total_chars = sum(item[6] for item in norm_atoms)
    if total_chars < 80:
        return (0.0, 0.0, 1.0, 1.0)

    right_atoms = [it for it in norm_atoms if it[4] >= 0.68]
    right_chars = sum(it[6] for it in right_atoms)
    if (right_chars / float(total_chars)) >= 0.70:
        right_min_nx0 = min(it[0] for it in right_atoms)
        return (0.0, 0.0, round(max(0.50, min(0.88, right_min_nx0 + 0.015)), 3), 1.0)

    left_atoms = [it for it in norm_atoms if it[4] <= 0.32]
    left_chars = sum(it[6] for it in left_atoms)
    if (left_chars / float(total_chars)) >= 0.70:
        left_max_nx1 = max(it[2] for it in left_atoms)
        return (round(min(0.45, max(0.15, left_max_nx1 - 0.015)), 3), 0.0, 1.0, 1.0)

    bottom_atoms = [it for it in norm_atoms if it[5] >= 0.75]
    bottom_chars = sum(it[6] for it in bottom_atoms)
    if (bottom_chars / float(total_chars)) >= 0.70:
        bottom_min_ny0 = min(it[1] for it in bottom_atoms)
        return (0.0, 0.0, 1.0, round(max(0.55, min(0.88, bottom_min_ny0 + 0.015)), 3))

    return (0.0, 0.0, 1.0, 1.0)


def _tile_cell_range_a1_d4(nx0, ny0, nx1, ny1):
    """Map normalized bbox onto canonical 4x4 A1..D4 cell range string."""
    cx0 = min(3, max(0, int(nx0 * 4.0 + 1e-6)))
    cy0 = min(3, max(0, int(ny0 * 4.0 + 1e-6)))
    cx1 = min(3, max(cx0, int(math.ceil(nx1 * 4.0 - 1e-6)) - 1))
    cy1 = min(3, max(cy0, int(math.ceil(ny1 * 4.0 - 1e-6)) - 1))
    start_cell = f"{_col_index_to_letters(cx0)}{cy0 + 1}"
    end_cell = f"{_col_index_to_letters(cx1)}{cy1 + 1}"
    return start_cell if start_cell == end_cell else f"{start_cell}..{end_cell}"


def _seam_line_tokens(norm_line):
    """Return lowercase alphanumeric and Thai tokens for seam Jaccard deduplication."""
    return set(re.findall(r"[a-z0-9\u0e00-\u0e7f]+", norm_line))


def stitch_tile_results(tile_entries):
    """Deduplicate seam overlaps across adjacent tiles and stitch Markdown + tables."""
    kept_by_rc = {}
    sections = []
    spatial_blocks = []
    all_tables = []
    seen_table_sigs = set()
    engines = []
    ocr_warnings = []

    ordered = sorted(tile_entries, key=lambda t: (int(t["row"]), int(t["col"])))
    for item in ordered:
        r = int(item["row"])
        c = int(item["col"])
        nb = item["norm_bbox"]
        nx0, ny0, nx1, ny1 = float(nb[0]), float(nb[1]), float(nb[2]), float(nb[3])
        raw_text = normalize_text(str(item.get("text") or "")).strip()

        eng = item.get("engine")
        if eng and eng not in engines:
            engines.append(eng)
        warn = item.get("ocr_warning")
        if warn and warn not in ocr_warnings:
            ocr_warnings.append(warn)

        if raw_text:
            for rows in extract_html_tables_from_text(raw_text):
                sig = tuple(tuple(cell for cell in row) for row in rows)
                if sig not in seen_table_sigs:
                    seen_table_sigs.add(sig)
                    all_tables.append(rows)

        raw_lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        n_cur = len(raw_lines)
        cur_lead_limit = n_cur if n_cur <= 2 else max(1, int(math.ceil(0.45 * n_cur)))

        neighbor_lines = []
        for prev_rc in ((r, c - 1), (r - 1, c)):
            if prev_rc[0] < 0 or prev_rc[1] < 0:
                continue
            prev_entries = kept_by_rc.get(prev_rc, [])
            if len(prev_entries) <= 2:
                neighbor_lines.extend(prev_entries)
            else:
                seam_tail = max(1, int(0.35 * len(prev_entries)))
                neighbor_lines.extend(prev_entries[-seam_tail:])

        kept_lines = []
        kept_entries = []
        for ln_idx, stripped in enumerate(raw_lines):
            norm_ln = re.sub(r"\s+", " ", stripped).strip().lower()
            toks_ln = _seam_line_tokens(norm_ln)
            is_dup = False
            if ln_idx < cur_lead_limit and neighbor_lines:
                for n_norm, n_toks in neighbor_lines:
                    if len(norm_ln) >= 4 and norm_ln == n_norm:
                        is_dup = True
                        break
                    if toks_ln and n_toks and (len(norm_ln) >= 4 or len(toks_ln) >= 2):
                        union_sz = len(toks_ln | n_toks)
                        if union_sz > 0 and (len(toks_ln & n_toks) / float(union_sz)) >= 0.80:
                            is_dup = True
                            break
            if not is_dup:
                kept_lines.append(stripped)
                kept_entries.append((norm_ln, toks_ln))

        kept_by_rc[(r, c)] = kept_entries
        item["dedup_text"] = "\n".join(kept_lines)
        if kept_lines:
            cell_range = item["cell_range"]
            header = (
                f"#### [Tile {r},{c} | {cell_range} | "
                f"{nx0:.2f}..{nx1:.2f}, {ny0:.2f}..{ny1:.2f}]"
            )
            sections.append(f"{header}\n" + "\n".join(kept_lines))
            primary_tid = _tile_id_from_norm_point(
                0.5 * (nx0 + nx1), 0.5 * (ny0 + ny1), cols=4, rows=4
            )
            spatial_blocks.append(
                {
                    "text": " ".join(kept_lines)[:240],
                    "norm_bbox": [round(nx0, 4), round(ny0, 4), round(nx1, 4), round(ny1, 4)],
                    "tile_id": primary_tid,
                    "cell_range": cell_range,
                    "source": "tile_ocr",
                }
            )

    return {
        "stitched_text": "\n\n".join(sections),
        "tables": all_tables,
        "spatial_blocks": spatial_blocks,
        "engines": engines,
        "ocr_warnings": ocr_warnings,
    }


def tile_and_stitch_canvas(
    doc,
    page_idx,
    canvas_bbox,
    profile,
    ocr_tile_fn,
    cache_dir=None,
    overlap=0.10,
    max_tiles=6,
    target_dpi=None,
):
    """Render composite once, crop adaptive overlapping tiles, run OCR, and stitch."""
    import fitz

    prof = resolve_hardware_profile(profile)
    owns_doc = not isinstance(doc, fitz.Document)
    doc_obj = fitz.open(str(doc)) if owns_doc else doc
    try:
        if page_idx < 0 or page_idx >= len(doc_obj):
            raise ValueError(f"page_idx {page_idx} out of range (0..{len(doc_obj) - 1}).")
        page = doc_obj[page_idx]
        page_num = page_idx + 1

        raw_doc_path = (
            os.path.abspath(str(doc))
            if owns_doc
            else (os.path.abspath(doc_obj.name) if getattr(doc_obj, "name", "") else "")
        )
        if raw_doc_path and os.path.isfile(raw_doc_path):
            st_doc = os.stat(raw_doc_path)
            doc_key = f"{raw_doc_path}:{st_doc.st_size}:{st_doc.st_mtime_ns}"
        elif raw_doc_path:
            doc_key = raw_doc_path
        else:
            stream_tok = getattr(doc_obj, "_xocr_stream_id", None)
            if not stream_tok:
                import uuid as _uuid

                stream_tok = f"stream:{_uuid.uuid4().hex}"
                try:
                    setattr(doc_obj, "_xocr_stream_id", stream_tok)
                except Exception:  # nosec B110
                    pass
            doc_key = str(stream_tok)

        if canvas_bbox and len(canvas_bbox) == 4:
            cb_x0 = max(0.0, min(1.0, float(canvas_bbox[0])))
            cb_y0 = max(0.0, min(1.0, float(canvas_bbox[1])))
            cb_x1 = max(0.0, min(1.0, float(canvas_bbox[2])))
            cb_y1 = max(0.0, min(1.0, float(canvas_bbox[3])))
            if cb_x1 <= cb_x0 or cb_y1 <= cb_y0:
                cb_x0, cb_y0, cb_x1, cb_y1 = 0.0, 0.0, 1.0, 1.0
        else:
            cb_x0, cb_y0, cb_x1, cb_y1 = 0.0, 0.0, 1.0, 1.0

        pw = max(1.0, float(abs(page.rect.width)))
        ph = max(1.0, float(abs(page.rect.height)))
        cw_pt = pw * (cb_x1 - cb_x0)
        ch_pt = ph * (cb_y1 - cb_y0)

        m_tiles = max(1, int(max_tiles))
        if m_tiles == 1:
            cols, rows = 1, 1
        elif m_tiles == 2:
            cols, rows = (2, 1) if cw_pt >= ch_pt else (1, 2)
        elif m_tiles == 3:
            cols, rows = (3, 1) if cw_pt >= ch_pt else (1, 3)
        elif (cw_pt / max(1.0, ch_pt)) >= 1.25 and m_tiles >= 6:
            cols, rows = 3, 2
        else:
            cols, rows = 2, 2

        eff_dpi = int(target_dpi if target_dpi is not None else 220)
        max_comp_px = max(4200, int(prof.get("max_composite_px", 5400)))
        composite_img, composite_dpi, composite_used_cache = _get_or_build_composite(
            page,
            doc_key,
            page_num,
            eff_dpi,
            max_comp_px,
            cache_dir=cache_dir,
        )
        comp_w, comp_h = composite_img.size

        tile_dir = (
            os.path.join(cache_dir, "tiles")
            if cache_dir
            else tempfile.mkdtemp(prefix="xocr_tiles_")
        )
        os.makedirs(tile_dir, exist_ok=True)

        cb_w = cb_x1 - cb_x0
        cb_h = cb_y1 - cb_y0
        step_x = cb_w / float(cols)
        step_y = cb_h / float(rows)
        ov = max(0.0, min(0.35, float(overlap)))

        tiles_out = []
        for r in range(rows):
            for c in range(cols):
                core_nx0 = cb_x0 + c * step_x
                core_ny0 = cb_y0 + r * step_y
                core_nx1 = cb_x0 + (c + 1) * step_x
                core_ny1 = cb_y0 + (r + 1) * step_y

                nx0 = max(cb_x0, core_nx0 - (0.5 * ov * step_x if c > 0 else 0.0))
                ny0 = max(cb_y0, core_ny0 - (0.5 * ov * step_y if r > 0 else 0.0))
                nx1 = min(cb_x1, core_nx1 + (0.5 * ov * step_x if c < cols - 1 else 0.0))
                ny1 = min(cb_y1, core_ny1 + (0.5 * ov * step_y if r < rows - 1 else 0.0))

                px0 = max(0, min(comp_w - 1, int(round(nx0 * comp_w))))
                py0 = max(0, min(comp_h - 1, int(round(ny0 * comp_h))))
                px1 = max(px0 + 1, min(comp_w, int(round(nx1 * comp_w))))
                py1 = max(py0 + 1, min(comp_h, int(round(ny1 * comp_h))))

                tile_img = composite_img.crop((px0, py0, px1, py1))
                tile_img = _resize_image_if_needed(tile_img, max_size=1800)

                png_path = os.path.join(tile_dir, f"tile_p{page_num}_r{r}_c{c}.png")
                tile_img.save(png_path, format="PNG", compress_level=2)

                cell_range = _tile_cell_range_a1_d4(core_nx0, core_ny0, core_nx1, core_ny1)
                tile_meta = {
                    "page": page_num,
                    "row": r,
                    "col": c,
                    "rows": rows,
                    "cols": cols,
                    "tile_label": f"r{r}c{c}",
                    "cell_range": cell_range,
                    "norm_bbox": [round(nx0, 4), round(ny0, 4), round(nx1, 4), round(ny1, 4)],
                    "width_px": tile_img.width,
                    "height_px": tile_img.height,
                    "png_path": png_path,
                    "text": "",
                    "engine": None,
                    "ocr_warning": None,
                }
                if ocr_tile_fn is not None:
                    res = ocr_tile_fn(png_path, tile_meta)
                    if isinstance(res, dict):
                        tile_meta["text"] = str(res.get("text") or "")
                        tile_meta["engine"] = res.get("engine")
                        tile_meta["ocr_warning"] = res.get("ocr_warning")
                    else:
                        tile_meta["text"] = str(res or "")
                        tile_meta["engine"] = "tile_ocr"
                tiles_out.append(tile_meta)

        stitched = (
            stitch_tile_results(tiles_out)
            if ocr_tile_fn is not None
            else {
                "stitched_text": "",
                "tables": [],
                "spatial_blocks": [],
                "engines": [],
                "ocr_warnings": [],
            }
        )
        return {
            "page": page_num,
            "canvas_bbox": [round(cb_x0, 4), round(cb_y0, 4), round(cb_x1, 4), round(cb_y1, 4)],
            "grid": f"{cols}x{rows}",
            "cols": cols,
            "rows": rows,
            "composite_cached": composite_used_cache,
            "composite_dpi": composite_dpi,
            "tile_dir": tile_dir,
            "tiles": tiles_out,
            "stitched_text": stitched["stitched_text"],
            "tables": stitched["tables"],
            "spatial_blocks": stitched["spatial_blocks"],
            "engines": stitched["engines"],
            "ocr_warnings": stitched["ocr_warnings"],
        }
    finally:
        if owns_doc:
            doc_obj.close()


def _merge_tile_blocks_into_spatial_page(spatial_page, tile_blocks):
    """Append OCR tile spatial_blocks into a spatial_index page and matching A1..D4 cells."""
    if not isinstance(spatial_page, dict) or not tile_blocks:
        return
    blocks = spatial_page.setdefault("blocks", [])
    tiles = spatial_page.setdefault("tiles", {})
    pw = max(1.0, float(spatial_page.get("page_width_pt", 1000.0)))
    ph = max(1.0, float(spatial_page.get("page_height_pt", 1000.0)))
    next_id = max((int(b.get("id", 0)) for b in blocks), default=0) + 1

    for tb in tile_blocks:
        nb = tb.get("norm_bbox") or [0.0, 0.0, 1.0, 1.0]
        nx0, ny0, nx1, ny1 = [float(v) for v in nb]
        txt = str(tb.get("text") or "").strip()
        if not txt:
            continue
        tid = tb.get("tile_id") or _tile_id_from_norm_point(
            0.5 * (nx0 + nx1), 0.5 * (ny0 + ny1), cols=4, rows=4
        )
        entry = {
            "id": next_id,
            "text": txt,
            "norm_bbox": [round(nx0, 4), round(ny0, 4), round(nx1, 4), round(ny1, 4)],
            "pt_bbox": [
                round(nx0 * pw, 2),
                round(ny0 * ph, 2),
                round(nx1 * pw, 2),
                round(ny1 * ph, 2),
            ],
            "tile_id": tid,
            "source": tb.get("source", "tile_ocr"),
        }
        if "cell_range" in tb:
            entry["cell_range"] = tb["cell_range"]
        blocks.append(entry)
        next_id += 1

        matched_cells = []
        for cell_id, t_rec in tiles.items():
            cb = t_rec.get("norm_bbox") or [0.0, 0.0, 0.0, 0.0]
            iw = max(0.0, min(nx1, float(cb[2])) - max(nx0, float(cb[0])))
            ih = max(0.0, min(ny1, float(cb[3])) - max(ny0, float(cb[1])))
            c_area = max(1e-6, (float(cb[2]) - float(cb[0])) * (float(cb[3]) - float(cb[1])))
            if (iw * ih) / c_area >= 0.20:
                matched_cells.append(cell_id)
        if tid in tiles and tid not in matched_cells:
            matched_cells.append(tid)
        for cell_id in matched_cells:
            t_rec = tiles[cell_id]
            t_rec["block_count"] = int(t_rec.get("block_count", 0)) + 1
            samples = t_rec.setdefault("sample_labels", [])
            if len(samples) < 12:
                samples.append(txt[:100])


_XLAYA_BRIDGE_CACHE = {"checked": False, "fn": None}


def _load_xlaya_lexical_fn():
    """Dynamically locate xlaya's compute_lexical_scores without hardcoding user paths."""
    if _XLAYA_BRIDGE_CACHE["checked"]:
        return _XLAYA_BRIDGE_CACHE["fn"]
    _XLAYA_BRIDGE_CACHE["checked"] = True
    try:
        laya_path = (
            Path.home()
            / ".gemini"
            / "config"
            / "skills"
            / "xlaya"
            / "scripts"
            / "laya_triage.py"
        )
        if laya_path.is_file():
            spec = importlib.util.spec_from_file_location("_xocr_xlaya_bridge", str(laya_path))
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                fn = getattr(mod, "compute_lexical_scores", None)
                if callable(fn):
                    _XLAYA_BRIDGE_CACHE["fn"] = fn
    except Exception:  # nosec B110
        _XLAYA_BRIDGE_CACHE["fn"] = None
    return _XLAYA_BRIDGE_CACHE["fn"]


def _tokenize_sniper_text(text):
    """Tokenize query or tile text into lowercase words, sheet IDs, numbers, and Thai 3-grams."""
    norm = normalize_text(text or "").strip()
    low = norm.lower()
    tokens = []

    for tok in re.findall(r"[a-z0-9]+(?:[-/:.][a-z0-9]+)*", low):
        tokens.append(tok)
        if "-" in tok or "/" in tok or ":" in tok:
            for part in re.split(r"[-/:]", tok):
                if len(part) >= 2:
                    tokens.append(part)

    for sid in SHEET_ID_RE.findall(norm.upper()):
        tokens.append(sid.lower())

    for run in re.findall(r"[\u0e00-\u0e7f]+", norm):
        if len(run) >= 3:
            for i in range(len(run) - 2):
                tokens.append(run[i : i + 3])
        elif len(run) == 2:
            tokens.append(run)

    return tokens


def rank_spatial_rois(spatial_index, query, top_k=5, xlaya_bridge=False):
    """Rank A1..D4 spatial ROIs in <10 ms via BM25 + sheet/scale/substring/Thai boosts."""
    if not query or not str(query).strip():
        return []

    if isinstance(spatial_index, (str, os.PathLike)):
        with open(str(spatial_index), "r", encoding="utf-8") as fh:
            idx_data = json.load(fh)
    elif isinstance(spatial_index, dict):
        idx_data = spatial_index
    else:
        return []

    pages = idx_data.get("pages") or []
    if not pages:
        return []

    q_raw = normalize_text(str(query)).strip()
    q_low = re.sub(r"\s+", " ", q_raw).lower()
    q_tokens = _tokenize_sniper_text(q_raw)
    q_unique = list(dict.fromkeys(q_tokens))
    q_sheet_ids = {s.lower() for s in SHEET_ID_RE.findall(q_raw.upper())}
    # Capture grid/sheet identifiers like A-01, AX-1, GRID A-01, S-102
    for gid in re.findall(r"\b[A-Z]{1,3}-\d{1,4}(?:\.\d+)?\b", q_raw.upper()):
        q_sheet_ids.add(gid.lower())
    q_num_scales = set(re.findall(r"\b\d+(?::\d+|\.\d+)?%?\b", q_low))

    tile_docs = []
    for pg in pages:
        page_num = int(pg.get("page", 1))
        regime = str(pg.get("regime", "DIGITAL_TEXT_TABLE"))
        reg_info = pg.get("regime_info") or {}
        vec_density = float(
            (reg_info.get("features") or {}).get("vector_drawing_density", 0.0)
        )
        if vec_density <= 0.0 and reg_info.get("vector_drawing_count"):
            vec_density = min(
                1.0,
                math.log1p(float(reg_info["vector_drawing_count"])) / math.log1p(1000.0),
            )

        blocks_by_tid = {}
        grid_refs_by_tid = {}
        for blk in pg.get("blocks") or []:
            tid = blk.get("tile_id")
            if tid and blk.get("text"):
                blocks_by_tid.setdefault(tid, []).append(str(blk["text"]))
            if tid and blk.get("grid_ref"):
                grid_refs_by_tid.setdefault(tid, []).append(str(blk["grid_ref"]))

        tables_by_tid = {}
        for tab in pg.get("tables") or []:
            tid = tab.get("tile_id")
            if tid and tab.get("markdown"):
                tables_by_tid.setdefault(tid, []).append(str(tab["markdown"]))
            if tid and tab.get("grid_ref"):
                grid_refs_by_tid.setdefault(tid, []).append(str(tab["grid_ref"]))

        callouts_by_tid = {}
        callout_strs_by_tid = {}
        for co in pg.get("callouts") or []:
            tid = co.get("tile_id")
            if not tid:
                continue
            for field in ("text", "target_sheet", "detail_no"):
                val = co.get(field)
                if val:
                    callouts_by_tid.setdefault(tid, []).append(str(val))
            if co.get("target_sheet"):
                callout_strs_by_tid.setdefault(tid, []).append(str(co["target_sheet"]))
            if co.get("text"):
                callout_strs_by_tid.setdefault(tid, []).append(str(co["text"]))
            if co.get("grid_ref"):
                grid_refs_by_tid.setdefault(tid, []).append(str(co["grid_ref"]))

        tiles_map = pg.get("tiles") or {}
        for tid, t_rec in tiles_map.items():
            parts = list(t_rec.get("sample_labels") or [])
            parts.extend(blocks_by_tid.get(tid, ()))
            parts.extend(tables_by_tid.get(tid, ()))
            parts.extend(callouts_by_tid.get(tid, ()))
            parts.extend(grid_refs_by_tid.get(tid, ()))
            raw_doc = normalize_text(" ".join(parts)).strip()
            if not raw_doc:
                continue
            toks = _tokenize_sniper_text(raw_doc)
            tile_docs.append(
                {
                    "page": page_num,
                    "tile_id": tid,
                    "norm_bbox": list(t_rec.get("norm_bbox") or [0.0, 0.0, 1.0, 1.0]),
                    "regime": regime,
                    "vector_density": vec_density,
                    "grid_refs": list(dict.fromkeys(grid_refs_by_tid.get(tid, ()))),
                    "callout_strs": list(dict.fromkeys(callout_strs_by_tid.get(tid, ()))),
                    "raw_low": re.sub(r"\s+", " ", raw_doc).lower(),
                    "tokens": toks,
                    "counts": Counter(toks),
                    "dl": max(1, len(toks)),
                }
            )

    if not tile_docs:
        return []

    n_docs = len(tile_docs)
    avgdl = sum(d["dl"] for d in tile_docs) / float(n_docs)
    k1 = 1.5
    b = 0.75

    df = Counter()
    for d in tile_docs:
        cnt = d["counts"]
        for qt in q_unique:
            if qt in cnt:
                df[qt] += 1

    idfs = {
        qt: math.log(1.0 + (n_docs - df[qt] + 0.5) / (df[qt] + 0.5))
        for qt in q_unique
    }

    xlaya_scores = None
    if xlaya_bridge:
        laya_fn = _load_xlaya_lexical_fn()
        if laya_fn is not None:
            try:
                xlaya_scores = laya_fn([{"text": d["raw_low"]} for d in tile_docs], q_raw)
            except Exception:  # nosec B110
                xlaya_scores = None

    scored = []
    for idx, d in enumerate(tile_docs):
        cnt = d["counts"]
        raw_low = d["raw_low"]
        matched = []
        bm25 = 0.0
        for qt in q_unique:
            tf = cnt.get(qt, 0)
            if tf > 0:
                matched.append(qt)
                denom = tf + k1 * (1.0 - b + b * (d["dl"] / avgdl))
                bm25 += idfs[qt] * ((tf * (k1 + 1.0)) / denom)

        sheet_boost = 0.0
        for sid in q_sheet_ids:
            if re.search(rf"(?<![a-z0-9]){re.escape(sid)}(?![a-z0-9])", raw_low):
                sheet_boost += 3.0
                if sid not in matched:
                    matched.append(sid)

        num_boost = 0.0
        for ntok in q_num_scales:
            if re.search(rf"(?<![0-9.:]){re.escape(ntok)}(?![0-9.:])", raw_low):
                num_boost += 2.0
                if ntok not in matched:
                    matched.append(ntok)

        sub_boost = 0.0
        if len(q_low) >= 3 and q_low in raw_low:
            sub_boost = 1.5
            if not matched:
                matched.append(q_low)

        grid_callout_boost = 0.0
        for gr in d["grid_refs"]:
            gr_low = gr.lower()
            gr_parts = [p.strip() for p in re.split(r"[\s/,-]+", gr_low) if p.strip()]
            if gr_low in q_low or (
                gr_parts
                and all(
                    re.search(rf"(?<![a-z0-9]){re.escape(gp)}(?![a-z0-9])", q_low)
                    for gp in gr_parts
                )
            ):
                grid_callout_boost += 2.5
                if gr_low not in matched:
                    matched.append(gr_low)
                break
        for cs in d["callout_strs"]:
            cs_low = cs.lower()
            if cs_low in q_low or cs_low in q_sheet_ids:
                grid_callout_boost += 2.5
                if cs_low not in matched:
                    matched.append(cs_low)
                break

        if (
            bm25 <= 0.0
            and sheet_boost <= 0.0
            and num_boost <= 0.0
            and sub_boost <= 0.0
            and grid_callout_boost <= 0.0
        ):
            continue

        total_score = (
            bm25
            + sheet_boost
            + num_boost
            + sub_boost
            + grid_callout_boost
            + 0.25 * d["vector_density"]
        )
        if xlaya_scores is not None and idx < len(xlaya_scores):
            total_score += float(xlaya_scores[idx])

        scored.append(
            {
                "page": d["page"],
                "tile_id": d["tile_id"],
                "norm_bbox": d["norm_bbox"],
                "score": round(total_score, 4),
                "regime": d["regime"],
                "matched_terms": matched,
                "recommended_pdf_render": {
                    "page": d["page"],
                    "crop": d["norm_bbox"],
                    "dpi": 300,
                },
            }
        )

    scored.sort(key=lambda r: (-r["score"], r["page"], r["tile_id"]))
    return scored[: max(1, int(top_k))]


def _encode_png_under_limit(pil_img, max_bytes=4_500_000):
    """Encode PIL Image as PNG strictly <= max_bytes via optimize + LANCZOS scale."""
    from PIL import Image

    cur = pil_img
    min_dim = 256 if int(max_bytes) >= 350_000 else 32
    for attempt in range(8):
        buf = io.BytesIO()
        cur.save(buf, format="PNG", optimize=(attempt >= 1), compress_level=9 if attempt >= 4 else 6)
        data = buf.getvalue()
        if len(data) <= max_bytes or (cur.width <= min_dim and cur.height <= min_dim):
            break
        ratio = math.sqrt(max_bytes / float(len(data))) * 0.90
        ratio = max(0.35, min(0.88, ratio))
        nw = max(min_dim, int(cur.width * ratio))
        nh = max(min_dim, int(cur.height * ratio))
        if nw == cur.width and nh == cur.height:
            nw = max(min_dim, int(cur.width * 0.75))
            nh = max(min_dim, int(cur.height * 0.75))
        cur = cur.resize((nw, nh), Image.Resampling.LANCZOS)
    else:
        buf = io.BytesIO()
        cur.save(buf, format="PNG", optimize=True, compress_level=9)
        data = buf.getvalue()

    if len(data) > max_bytes:
        for n_colors in (128, 64, 32):
            q = cur.convert("P", palette=Image.Palette.ADAPTIVE, colors=n_colors)
            buf = io.BytesIO()
            q.save(buf, format="PNG", optimize=True, compress_level=9)
            q_data = buf.getvalue()
            if len(q_data) <= max_bytes:
                return q_data, q.width, q.height
            data = q_data
    return data, cur.width, cur.height


def _draw_grid_overlay(pil_img, cols=4, rows=4, draw_cells=True):
    """Draw translucent A1..D4 grid + normalized ruler ticks on an RGB PIL image."""
    from PIL import Image, ImageDraw, ImageFont

    base = pil_img.convert("RGBA")
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    w, h = base.size
    font = ImageFont.load_default()

    # Outer frame & normalized ruler ticks (0.25 increments)
    draw.rectangle([(0, 0), (w - 1, h - 1)], outline=(30, 64, 175, 160), width=2)
    if draw_cells:
        for ci in range(1, cols):
            x = int(round(ci * w / float(cols)))
            draw.line([(x, 0), (x, h)], fill=(37, 99, 235, 130), width=2)
        for ri in range(1, rows):
            y = int(round(ri * h / float(rows)))
            draw.line([(0, y), (w, y)], fill=(37, 99, 235, 130), width=2)

        for ri in range(rows):
            for ci in range(cols):
                tid = f"{_col_index_to_letters(ci)}{ri + 1}"
                lx = int(round(ci * w / float(cols))) + 8
                ly = int(round(ri * h / float(rows))) + 8
                box_w = max(28, 12 + len(tid) * 8)
                draw.rectangle(
                    [(lx, ly), (lx + box_w, ly + 18)],
                    fill=(15, 23, 42, 165),
                    outline=(147, 197, 253, 210),
                    width=1,
                )
                draw.text((lx + 6, ly + 4), tid, fill=(255, 255, 255, 240), font=font)

    return Image.alpha_composite(base, overlay).convert("RGB")


def _get_or_build_composite(page, doc_key, page_num, target_dpi, max_composite_px, cache_dir=None):
    """Render full-page composite once per page/DPI and reuse across crops/tiles."""
    from PIL import Image

    pw = max(1.0, float(abs(page.rect.width)))
    ph = max(1.0, float(abs(page.rect.height)))
    max_pt = max(pw, ph)
    eff_dpi = int(target_dpi)
    if (max_pt * eff_dpi / 72.0) > max_composite_px:
        eff_dpi = max(72, int(max_composite_px * 72.0 / max_pt))

    cache_key = (doc_key, int(page_num), int(eff_dpi))
    disk_path = None
    if cache_dir:
        import hashlib

        doc_hash = hashlib.sha256(str(doc_key).encode("utf-8")).hexdigest()[:16]
        disk_path = os.path.join(cache_dir, f"composite_{doc_hash}_p{page_num}_d{eff_dpi}.png")

    with _COMPOSITE_CACHE_LOCK:
        cached = _COMPOSITE_CACHE.get(cache_key)
        if cached is not None:
            _COMPOSITE_CACHE.move_to_end(cache_key)
            return cached.copy(), eff_dpi, True
        if disk_path and os.path.isfile(disk_path):
            try:
                with Image.open(disk_path) as im_disk:
                    pil_img = im_disk.convert("RGB")
                _COMPOSITE_CACHE[cache_key] = pil_img.copy()
                while len(_COMPOSITE_CACHE) > _MAX_COMPOSITE_CACHE:
                    _COMPOSITE_CACHE.popitem(last=False)
                return pil_img, eff_dpi, True
            except Exception:  # nosec B110
                pass

    pix = page.get_pixmap(dpi=eff_dpi, alpha=False)
    pil_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    with _COMPOSITE_CACHE_LOCK:
        if disk_path:
            try:
                import tempfile as _tmp

                os.makedirs(cache_dir, exist_ok=True)
                fd, tmp_name = _tmp.mkstemp(prefix=".comp_", suffix=".png", dir=cache_dir)
                os.close(fd)
                try:
                    pil_img.save(tmp_name, format="PNG", compress_level=1)
                    os.replace(tmp_name, disk_path)
                finally:
                    if os.path.exists(tmp_name):
                        os.unlink(tmp_name)
            except Exception:  # nosec B110
                pass
        _COMPOSITE_CACHE[cache_key] = pil_img.copy()
        while len(_COMPOSITE_CACHE) > _MAX_COMPOSITE_CACHE:
            _COMPOSITE_CACHE.popitem(last=False)
    return pil_img, eff_dpi, False


def render_drawing_view(
    doc_or_path,
    page_num=1,
    render_mode="overview",
    bbox=None,
    query=None,
    tile=None,
    tile_grid="4x4",
    dpi=None,
    grid_overlay=True,
    max_bytes=4_500_000,
    profile="edge",
    out_path=None,
    cache_dir=None,
):
    """Render multi-scale overview/crop/around_text/tile/quadrants drawing views."""
    import fitz
    from PIL import Image

    prof = resolve_hardware_profile(profile)
    eff_max_bytes = int(max_bytes or prof["max_bytes"])
    valid_modes = ("overview", "crop", "around_text", "tile", "quadrants")
    if render_mode not in valid_modes:
        raise ValueError(
            f"Unsupported render_mode {render_mode!r}; expected one of {list(valid_modes)}."
        )

    owns_doc = not isinstance(doc_or_path, fitz.Document)
    doc = fitz.open(str(doc_or_path)) if owns_doc else doc_or_path
    try:
        if page_num < 1 or page_num > len(doc):
            raise ValueError(
                f"Page {page_num} out of range (1..{len(doc)})."
            )
        page = doc[page_num - 1]
        raw_doc_path = (
            os.path.abspath(str(doc_or_path))
            if owns_doc
            else (os.path.abspath(doc.name) if getattr(doc, "name", "") else "")
        )
        if raw_doc_path and os.path.isfile(raw_doc_path):
            st_doc = os.stat(raw_doc_path)
            doc_key = f"{raw_doc_path}:{st_doc.st_size}:{st_doc.st_mtime_ns}"
        elif raw_doc_path:
            doc_key = raw_doc_path
        else:
            stream_tok = getattr(doc, "_xocr_stream_id", None)
            if not stream_tok:
                import uuid as _uuid

                stream_tok = f"stream:{_uuid.uuid4().hex}"
                try:
                    setattr(doc, "_xocr_stream_id", stream_tok)
                except Exception:  # nosec B110
                    pass
            doc_key = str(stream_tok)

        rx0 = float(page.rect.x0)
        ry0 = float(page.rect.y0)
        pw = max(1.0, float(abs(page.rect.width)))
        ph = max(1.0, float(abs(page.rect.height)))
        cols, rows = _parse_tile_grid(tile_grid)

        try:
            img_count = len(page.get_images(full=False) or [])
        except Exception:  # nosec B110
            img_count = 0
        use_composite_cache = img_count > 20

        # Resolve target ROIs [(label, [nx0, ny0, nx1, ny1])] and default DPI
        rois = []
        matched_hits = []
        eff_grid = f"{cols}x{rows}"

        if render_mode == "overview":
            eff_dpi = int(dpi if dpi is not None else 150)
            rois.append(("overview", [0.0, 0.0, 1.0, 1.0]))
        elif render_mode == "crop":
            if bbox is None or len(bbox) != 4:
                raise ValueError("render_mode='crop' requires bbox=[nx0, ny0, nx1, ny1].")
            raw_vals = [float(v) for v in bbox]
            if any(abs(v) > 1.5 for v in raw_vals):
                nx0 = max(0.0, min(1.0, (raw_vals[0] - rx0) / pw))
                ny0 = max(0.0, min(1.0, (raw_vals[1] - ry0) / ph))
                nx1 = max(0.0, min(1.0, (raw_vals[2] - rx0) / pw))
                ny1 = max(0.0, min(1.0, (raw_vals[3] - ry0) / ph))
            else:
                nx0, ny0, nx1, ny1 = [max(0.0, min(1.0, v)) for v in raw_vals]
            if nx1 <= nx0 or ny1 <= ny0:
                raise ValueError(f"Invalid crop bbox: {bbox}")
            eff_dpi = int(dpi if dpi is not None else 300)
            rois.append(("crop", [nx0, ny0, nx1, ny1]))
        elif render_mode == "tile":
            if not tile:
                raise ValueError("render_mode='tile' requires tile cell e.g. 'B2'.")
            nb = _norm_bbox_from_tile(tile, cols=cols, rows=rows)
            pad = 0.03
            rois.append(
                (
                    f"tile_{str(tile).upper()}",
                    [
                        max(0.0, nb[0] - pad),
                        max(0.0, nb[1] - pad),
                        min(1.0, nb[2] + pad),
                        min(1.0, nb[3] + pad),
                    ],
                )
            )
            eff_dpi = int(dpi if dpi is not None else 300)
        elif render_mode == "around_text":
            if not query or not str(query).strip():
                raise ValueError("render_mode='around_text' requires non-empty query.")
            q_str = str(query).strip()
            q_norm = normalize_text(q_str).lower()
            atoms = _extract_clean_text_atoms(page)
            for a in atoms:
                if q_norm in a["text"].lower():
                    matched_hits.append(a)
            if not matched_hits:
                try:
                    rects = page.search_for(q_str) or []
                    for r in rects:
                        matched_hits.append(
                            {
                                "x0": float(r.x0),
                                "y0": float(r.y0),
                                "x1": float(r.x1),
                                "y1": float(r.y1),
                                "text": q_str,
                            }
                        )
                except Exception:  # nosec B110
                    pass

            eff_dpi = int(dpi if dpi is not None else 300)
            if matched_hits:
                hx0 = min(h["x0"] for h in matched_hits)
                hy0 = min(h["y0"] for h in matched_hits)
                hx1 = max(h["x1"] for h in matched_hits)
                hy1 = max(h["y1"] for h in matched_hits)
                # If hits span > 65% of page, zoom around the first primary hit
                if ((hx1 - hx0) / pw > 0.65) or ((hy1 - hy0) / ph > 0.65):
                    h0 = matched_hits[0]
                    hx0, hy0, hx1, hy1 = h0["x0"], h0["y0"], h0["x1"], h0["y1"]
                nx0 = max(0.0, (hx0 - rx0) / pw - 0.12)
                ny0 = max(0.0, (hy0 - ry0) / ph - 0.12)
                nx1 = min(1.0, (hx1 - rx0) / pw + 0.12)
                ny1 = min(1.0, (hy1 - ry0) / ph + 0.12)
                if (nx1 - nx0) < 0.24:
                    midx = 0.5 * (nx0 + nx1)
                    nx0 = max(0.0, midx - 0.12)
                    nx1 = min(1.0, midx + 0.12)
                if (ny1 - ny0) < 0.24:
                    midy = 0.5 * (ny0 + ny1)
                    ny0 = max(0.0, midy - 0.12)
                    ny1 = min(1.0, midy + 0.12)
                rois.append(("around_text", [nx0, ny0, nx1, ny1]))
            else:
                rois.append(("around_text_fallback_overview", [0.0, 0.0, 1.0, 1.0]))
        else:  # quadrants
            q_cols, q_rows = (2, 2) if tile_grid == "4x4" else (cols, rows)
            eff_grid = f"{q_cols}x{q_rows}"
            eff_dpi = int(dpi if dpi is not None else (220 if use_composite_cache else 250))
            overlap = 0.10
            cw_step = 1.0 / float(q_cols)
            ch_step = 1.0 / float(q_rows)
            for ri in range(q_rows):
                for ci in range(q_cols):
                    tid = f"{_col_index_to_letters(ci)}{ri + 1}"
                    nx0 = max(0.0, ci * cw_step - (0.5 * overlap * cw_step if ci > 0 else 0.0))
                    ny0 = max(0.0, ri * ch_step - (0.5 * overlap * ch_step if ri > 0 else 0.0))
                    nx1 = min(1.0, (ci + 1) * cw_step + (0.5 * overlap * cw_step if ci < q_cols - 1 else 0.0))
                    ny1 = min(1.0, (ri + 1) * ch_step + (0.5 * overlap * ch_step if ri < q_rows - 1 else 0.0))
                    rois.append((f"quadrant_{tid}", [nx0, ny0, nx1, ny1]))

        composite_img = None
        composite_used_cache = False
        composite_dpi = eff_dpi
        if use_composite_cache:
            # Render composite once at crop-ready resolution when multi-layer PDF
            comp_target = max(eff_dpi, 180) if render_mode != "overview" else eff_dpi
            composite_img, composite_dpi, composite_used_cache = _get_or_build_composite(
                page,
                doc_key,
                page_num,
                comp_target,
                prof["max_composite_px"],
                cache_dir=cache_dir,
            )

        views = []
        for label, nb in rois:
            nx0, ny0, nx1, ny1 = nb
            pt_bbox = [
                round(rx0 + nx0 * pw, 2),
                round(ry0 + ny0 * ph, 2),
                round(rx0 + nx1 * pw, 2),
                round(ry0 + ny1 * ph, 2),
            ]
            if composite_img is not None:
                cw, ch = composite_img.size
                px0 = max(0, min(cw - 1, int(round(nx0 * cw))))
                py0 = max(0, min(ch - 1, int(round(ny0 * ch))))
                px1 = max(px0 + 1, min(cw, int(round(nx1 * cw))))
                py1 = max(py0 + 1, min(ch, int(round(ny1 * ch))))
                view_img = composite_img.crop((px0, py0, px1, py1))
                actual_dpi = composite_dpi
            else:
                clip = fitz.Rect(pt_bbox[0], pt_bbox[1], pt_bbox[2], pt_bbox[3])
                max_clip_pt = max(1.0, clip.width, clip.height)
                actual_dpi = eff_dpi
                if (max_clip_pt * actual_dpi / 72.0) > prof["max_composite_px"]:
                    actual_dpi = max(72, int(prof["max_composite_px"] * 72.0 / max_clip_pt))
                pix = page.get_pixmap(clip=clip, dpi=actual_dpi, alpha=False)
                view_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

            if grid_overlay:
                view_img = _draw_grid_overlay(
                    view_img,
                    cols=cols,
                    rows=rows,
                    draw_cells=(render_mode == "overview"),
                )

            png_bytes, out_w, out_h = _encode_png_under_limit(
                view_img, max_bytes=eff_max_bytes
            )

            saved_path = None
            if out_path:
                out_str = str(out_path)
                if out_str.lower().endswith(".png"):
                    os.makedirs(os.path.dirname(os.path.abspath(out_str)), exist_ok=True)
                    if len(rois) == 1:
                        saved_path = os.path.abspath(out_str)
                    else:
                        stem, ext = os.path.splitext(os.path.abspath(out_str))
                        saved_path = f"{stem}_{label}{ext}"
                else:
                    os.makedirs(out_str, exist_ok=True)
                    saved_path = os.path.abspath(
                        os.path.join(out_str, f"view_p{page_num}_{label}.png")
                    )
                with open(saved_path, "wb") as f_out:
                    f_out.write(png_bytes)

            serialized_hits = []
            if render_mode == "around_text":
                for h in matched_hits:
                    serialized_hits.append(
                        {
                            "text": h.get("text", ""),
                            "norm_bbox": [
                                round(max(0.0, min(1.0, (float(h["x0"]) - rx0) / pw)), 4),
                                round(max(0.0, min(1.0, (float(h["y0"]) - ry0) / ph)), 4),
                                round(max(0.0, min(1.0, (float(h["x1"]) - rx0) / pw)), 4),
                                round(max(0.0, min(1.0, (float(h["y1"]) - ry0) / ph)), 4),
                            ],
                        }
                    )

            views.append(
                {
                    "page": page_num,
                    "mode": render_mode,
                    "label": label,
                    "tile_grid": eff_grid,
                    "norm_bbox": [round(v, 4) for v in nb],
                    "pt_bbox": pt_bbox,
                    "width_px": out_w,
                    "height_px": out_h,
                    "dpi": actual_dpi,
                    "bytes": len(png_bytes),
                    "byte_size": len(png_bytes),
                    "mime_type": "image/png",
                    "output_path": saved_path,
                    "path": saved_path,
                    "matched_hits": serialized_hits,
                    "png_bytes": png_bytes,
                }
            )

        return {
            "status": "ok",
            "page": page_num,
            "render_mode": render_mode,
            "profile": prof["profile"],
            "tile_grid": eff_grid,
            "composite_cached": composite_used_cache,
            "multi_layer_composite": use_composite_cache,
            "query_hits": len(matched_hits) if render_mode == "around_text" else 0,
            "views": views,
        }
    finally:
        if owns_doc:
            doc.close()


def parse_page_selection(pages_arg, total_pages):
    """Parse 1-based page spec like '1-5,8,11-13' into 0-based indices."""
    if not pages_arg or pages_arg.strip().lower() in ("all", "*"):
        return list(range(total_pages))
    selected = set()
    try:
        for part in pages_arg.split(","):
            part = part.strip()
            if not part:
                continue
            if "-" in part:
                bounds = part.split("-", 1)
                raw_start = int(bounds[0].strip())
                raw_end = int(bounds[1].strip())
                if raw_start < 1 or raw_end < raw_start:
                    raise ValueError(f"Invalid page range '{part}'")
                start = max(1, raw_start)
                end = min(total_pages, raw_end)
                for p_num in range(start, end + 1):
                    selected.add(p_num - 1)
            else:
                p_num = int(part)
                if p_num < 1:
                    raise ValueError(f"Page number must be >= 1, got '{part}'")
                if 1 <= p_num <= total_pages:
                    selected.add(p_num - 1)
    except ValueError as exc:
        raise ValueError(
            f"Invalid --pages specification '{pages_arg}': "
            f"expected 1-based page numbers or ranges (e.g. '1-5,8,10-12') ({exc})."
        ) from exc
    return sorted(selected)


def _clean_table_rows_with_meta(raw_rows):
    """Normalize table cells, prune empty columns/rows, and return (rows, keep_cols)."""
    if not raw_rows:
        return [], []
    rows = []
    for raw_r in raw_rows:
        if not raw_r:
            continue
        norm_r = []
        has_val = False
        for cell in raw_r:
            val = normalize_text(str(cell or "")).replace("\n", " ").strip()
            val = re.sub(r"\s{2,}", " ", val)
            if val:
                has_val = True
            norm_r.append(val)
        if has_val:
            rows.append(norm_r)

    if len(rows) < 2:
        return [], []

    ncol = max(len(r) for r in rows)
    keep_cols = [
        ci for ci in range(ncol) if any(ci < len(r) and r[ci] for r in rows)
    ]
    if len(keep_cols) < 2:
        return [], []

    pruned = [
        [r[ci] if ci < len(r) else "" for ci in keep_cols] for r in rows
    ]
    multi_col_rows = sum(1 for r in pruned if sum(1 for c in r if c) >= 2)
    if multi_col_rows < 2 or (multi_col_rows / len(pruned)) < 0.60:
        return [], []
    total_cells = len(pruned) * len(keep_cols)
    raw_total = max(1, len(raw_rows) * ncol)
    filled_cells = sum(1 for r in pruned for c in r if c)
    if (
        total_cells > 0
        and (
            (filled_cells / total_cells) < 0.52
            or (filled_cells / raw_total) < 0.32
        )
    ):
        return [], []
    return pruned, keep_cols


def clean_table_rows(raw_rows):
    """Normalize table cells, prune empty columns/rows, and validate tables."""
    cleaned, _ = _clean_table_rows_with_meta(raw_rows)
    return cleaned


def _extract_tab_raw_col_bounds_norm(tab_obj, page_rect, bbox, raw_ncol):
    """Extract normalized [nx0, nx1] column bounds from a PyMuPDF Table pre-pruning."""
    rx0 = float(page_rect.x0)
    pw = max(1.0, float(abs(page_rect.width)))
    ncol = max(int(raw_ncol or 0), int(getattr(tab_obj, "col_count", 0) or 0))
    if ncol <= 0:
        return []
    col_x0 = [None] * ncol
    col_x1 = [None] * ncol
    try:
        for row in getattr(tab_obj, "rows", None) or ():
            cells = getattr(row, "cells", None) or ()
            for ci in range(min(ncol, len(cells))):
                cb = cells[ci]
                if cb and len(cb) == 4:
                    cx0, _, cx1, _ = [float(v) for v in cb]
                    col_x0[ci] = cx0 if col_x0[ci] is None else min(col_x0[ci], cx0)
                    col_x1[ci] = cx1 if col_x1[ci] is None else max(col_x1[ci], cx1)
    except Exception:  # nosec B110
        pass

    bx0, bx1 = float(bbox[0]), float(bbox[2])
    bw = max(1.0, bx1 - bx0)
    bounds = []
    for ci in range(ncol):
        if col_x0[ci] is not None and col_x1[ci] is not None and col_x1[ci] > col_x0[ci]:
            x0, x1 = col_x0[ci], col_x1[ci]
        else:
            x0 = bx0 + (ci / float(ncol)) * bw
            x1 = bx0 + ((ci + 1) / float(ncol)) * bw
        bounds.append(
            [
                round(max(0.0, min(1.0, (x0 - rx0) / pw)), 4),
                round(max(0.0, min(1.0, (x1 - rx0) / pw)), 4),
            ]
        )
    return bounds


def _is_booktabs_strip(rows):
    """Return True if a table region looks like a 1-2 row booktabs strip."""
    if len(rows) <= 2:
        return True
    max_nl = max(
        (str(c or "").count("\n") for r in rows for c in r), default=0
    )
    return max_nl >= 2


def _find_booktabs_rule_bboxes(page, drawings=None):
    """Detect LaTeX booktabs horizontal rule clusters (top/mid/bottomrule)."""
    if drawings is None:
        try:
            drawings = page.get_drawings() or []
        except Exception:  # nosec B110
            return []

    h_rules = []
    for drw in drawings:
        rect = drw.get("rect")
        if not rect:
            continue
        width = rect.x1 - rect.x0
        height = rect.y1 - rect.y0
        if width >= 200 and height <= 4.5:
            h_rules.append(
                [
                    float(rect.x0),
                    float(rect.y0),
                    float(rect.x1),
                    float(rect.y1),
                ]
            )

    if len(h_rules) < 3:
        return []

    h_rules.sort(key=lambda r: (r[1], r[0]))
    clusters = []
    for rule in h_rules:
        placed = False
        for cl in clusters:
            if (
                abs(rule[0] - cl["x0"]) < 25
                and abs(rule[2] - cl["x1"]) < 25
                and 0 <= (rule[1] - cl["last_y"]) < 240
            ):
                if (rule[1] - cl["last_y"]) > 3.5:
                    cl["rule_count"] += 1
                cl["y1"] = max(cl["y1"], rule[3])
                cl["last_y"] = rule[3]
                placed = True
                break
        if not placed:
            clusters.append(
                {
                    "x0": rule[0],
                    "y0": rule[1],
                    "x1": rule[2],
                    "y1": rule[3],
                    "last_y": rule[3],
                    "rule_count": 1,
                }
            )

    return [
        [cl["x0"], cl["y0"], cl["x1"], cl["y1"]]
        for cl in clusters
        if cl["rule_count"] >= 3 and (cl["y1"] - cl["y0"]) >= 25
    ]


def extract_tables_from_page(
    page, fitz_mod, raw_text: str = "", drawings=None, return_meta: bool = False
):
    """Two-Stage Grid + LaTeX booktabs table extractor using PyMuPDF."""
    extracted = []
    if drawings is None:
        try:
            drawings = page.get_drawings() or []
        except Exception:  # nosec B110
            drawings = []

    if not drawings:
        return extracted

    h_rules_cnt = 0
    g_rects_cnt = 0
    for drw in drawings:
        rect = drw.get("rect")
        if not rect:
            continue
        w = rect.x1 - rect.x0
        h = rect.y1 - rect.y0
        if w >= 150 and h <= 5:
            h_rules_cnt += 1
        elif w >= 25 and h >= 10 and drw.get("type") != "f":
            g_rects_cnt += 1

    if h_rules_cnt < 3 and g_rects_cnt < 8:
        return extracted

    if (
        len(drawings) > 200
        and g_rects_cnt < 12
        and not re.search(
            r"(?:^|\n)\s*(?:Table|Tab\.|ตาราง)\s*(?:\d+|[IVXLCDM]+)?\s*[:.|\-–—]",
            raw_text or "",
            re.IGNORECASE,
        )
    ):
        return extracted

    try:
        raw_tabs = page.find_tables().tables
    except Exception:  # nosec B110
        raw_tabs = []

    # Pre-extract rows and column bounds before any page.find_tables(clip=...) call,
    # which mutates PyMuPDF's internal table buffers on the same Page object.
    cached_tabs = []
    for tab in sorted(raw_tabs, key=lambda x: (x.bbox[1], x.bbox[0])):
        try:
            t_rows = tab.extract() or []
            t_box = list(tab.bbox)
            raw_ncol = max((len(r) for r in t_rows if r), default=0)
            raw_cols = _extract_tab_raw_col_bounds_norm(tab, page.rect, t_box, raw_ncol)
            cached_tabs.append((t_box, t_rows, raw_cols))
        except Exception:  # nosec B110
            pass

    groups = []
    for box, rows, raw_cols in cached_tabs:
        if len(rows) >= 5:
            r_ncol = max((len(r) for r in rows if r), default=1)
            r_fill = sum(
                1 for r in rows for c in (r or []) if c and str(c).strip()
            ) / max(1, len(rows) * r_ncol)
            if r_fill < 0.08:
                continue
        if (
            groups
            and abs(box[1] - groups[-1]["bbox"][3]) < 15
            and abs(box[0] - groups[-1]["bbox"][0]) < 20
            and abs(box[2] - groups[-1]["bbox"][2]) < 20
            and (
                _is_booktabs_strip(groups[-1]["last_rows"])
                or _is_booktabs_strip(rows)
            )
        ):
            groups[-1]["bbox"][3] = max(groups[-1]["bbox"][3], box[3])
            groups[-1]["rows_list"].append(rows)
            groups[-1]["last_rows"] = rows
            if len(raw_cols) >= len(groups[-1]["raw_cols"]):
                groups[-1]["raw_cols"] = raw_cols
        else:
            groups.append(
                {
                    "bbox": box,
                    "rows_list": [rows],
                    "last_rows": rows,
                    "raw_cols": raw_cols,
                    "reextract": False,
                    "source": "vector_grid",
                }
            )

    # Merge or append pure horizontal-rule booktabs clusters (3-rule tables
    # or header bands between \toprule and \midrule missed by lines strategy).
    for rbox in _find_booktabs_rule_bboxes(page, drawings=drawings):
        matched = False
        for grp in groups:
            gbox = grp["bbox"]
            y_overlap = min(gbox[3], rbox[3]) - max(gbox[1], rbox[1])
            if (
                abs(gbox[0] - rbox[0]) < 25
                and abs(gbox[2] - rbox[2]) < 25
                and y_overlap > -15
            ):
                if rbox[1] < gbox[1] - 4 or rbox[3] > gbox[3] + 4:
                    grp["bbox"] = [
                        min(gbox[0], rbox[0]),
                        min(gbox[1], rbox[1]),
                        max(gbox[2], rbox[2]),
                        max(gbox[3], rbox[3]),
                    ]
                    grp["reextract"] = True
                    grp["source"] = "booktabs"
                matched = True
                break
        if not matched:
            near_rect = fitz_mod.Rect(
                0, rbox[1] - 48, page.rect.width, rbox[3] + 48
            )
            top_rect = fitz_mod.Rect(rbox[0], rbox[1], rbox[2], rbox[1] + 24)
            near_txt = page.get_text("text", clip=near_rect) or ""
            top_txt = (page.get_text("text", clip=top_rect) or "").strip()
            if re.search(
                r"(?:^|\n)\s*(?:Table|Tab\.|ตาราง)\s*(?:\d+[A-Za-z]?|[IVXLCDM]+)\s*[:.|\-–—\s]",
                near_txt,
                re.IGNORECASE,
            ) and not re.match(
                r"^(Algorithm|Figure|Fig\.)\b", top_txt, re.IGNORECASE
            ):
                groups.append(
                    {
                        "bbox": rbox,
                        "rows_list": [],
                        "last_rows": [],
                        "raw_cols": [],
                        "reextract": True,
                        "source": "booktabs",
                    }
                )

    groups.sort(key=lambda g: (g["bbox"][1], g["bbox"][0]))

    rx0 = float(page.rect.x0)
    ry0 = float(page.rect.y0)
    pw = max(1.0, float(abs(page.rect.width)))
    ph = max(1.0, float(abs(page.rect.height)))

    for grp in groups:
        t0_rows = grp["rows_list"][0] if grp["rows_list"] else []
        max_nl = max(
            (str(c or "").count("\n") for r in t0_rows for c in r), default=0
        )
        candidates = []
        grp_w = grp["bbox"][2] - grp["bbox"][0]
        if (
            grp_w < 200
            or (
                not grp.get("reextract")
                and len(grp["rows_list"]) == 1
                and len(t0_rows) >= 2
                and max_nl < 2
            )
        ):
            candidates.append((t0_rows, grp["bbox"], grp["raw_cols"], grp["source"]))
        else:
            try:
                clip_rect = fitz_mod.Rect(grp["bbox"])
                min_v = 2 if not grp["rows_list"] else 3
                sub_tabs = page.find_tables(
                    clip=clip_rect,
                    vertical_strategy="text",
                    horizontal_strategy="text",
                    min_words_vertical=min_v,
                ).tables
                for st in sub_tabs:
                    st_rows = st.extract() or []
                    st_box = list(st.bbox)
                    st_ncol = max((len(r) for r in st_rows if r), default=0)
                    st_raw_cols = _extract_tab_raw_col_bounds_norm(
                        st, page.rect, st_box, st_ncol
                    )
                    candidates.append((st_rows, st_box, st_raw_cols, "booktabs"))
            except Exception:  # nosec B110
                pass
            if not candidates and t0_rows:
                candidates.append((t0_rows, grp["bbox"], grp["raw_cols"], grp["source"]))

        for cand_rows, cand_box, cand_raw_cols, cand_src in candidates:
            cleaned, keep_cols = _clean_table_rows_with_meta(cand_rows)
            if not cleaned:
                continue
            if return_meta:
                raw_ncol = max((len(r) for r in cand_rows if r), default=len(cleaned[0]))
                if not cand_raw_cols or len(cand_raw_cols) < raw_ncol:
                    bx0, bx1 = float(cand_box[0]), float(cand_box[2])
                    bw = max(1.0, bx1 - bx0)
                    cand_raw_cols = [
                        [
                            round(max(0.0, min(1.0, (bx0 + (ci / float(raw_ncol)) * bw - rx0) / pw)), 4),
                            round(max(0.0, min(1.0, (bx0 + ((ci + 1) / float(raw_ncol)) * bw - rx0) / pw)), 4),
                        ]
                        for ci in range(raw_ncol)
                    ]
                col_bounds_norm = [
                    cand_raw_cols[ci] for ci in keep_cols if ci < len(cand_raw_cols)
                ]
                norm_bbox = [
                    round(max(0.0, min(1.0, (float(cand_box[0]) - rx0) / pw)), 4),
                    round(max(0.0, min(1.0, (float(cand_box[1]) - ry0) / ph)), 4),
                    round(max(0.0, min(1.0, (float(cand_box[2]) - rx0) / pw)), 4),
                    round(max(0.0, min(1.0, (float(cand_box[3]) - ry0) / ph)), 4),
                ]
                extracted.append(
                    {
                        "rows": cleaned,
                        "bbox": [round(float(v), 2) for v in cand_box],
                        "norm_bbox": norm_bbox,
                        "col_bounds_norm": col_bounds_norm,
                        "raw_col_bounds_norm": cand_raw_cols,
                        "keep_cols": keep_cols,
                        "source": cand_src,
                    }
                )
            else:
                extracted.append(cleaned)

    return extracted


def rows_to_markdown(rows):
    """Format a 2D list of cleaned table rows as a GFM Markdown table."""
    if not rows:
        return ""
    col_count = max(len(r) for r in rows)
    padded = [r + [""] * (col_count - len(r)) for r in rows]
    header = [c.replace("|", "\\|") for c in padded[0]]
    md_lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join(["---"] * col_count) + " |",
    ]
    for r in padded[1:]:
        escaped = [c.replace("|", "\\|") for c in r]
        md_lines.append("| " + " | ".join(escaped) + " |")
    return "\n".join(md_lines)


class _HTMLTableParser(html.parser.HTMLParser):
    """Parse HTML <table>...</table> blocks with full rowspan/colspan expansion."""

    def __init__(self):
        super().__init__()
        self.tables = []
        self._in_table = False
        self._in_row = False
        self._in_cell = False
        self._cell_parts = []
        self._rowspan = 1
        self._colspan = 1
        self._raw_rows = []
        self._cur_row = []

    def _flush_cell(self):
        if self._in_cell:
            self._in_cell = False
            txt = normalize_text(
                re.sub(r"\s+", " ", "".join(self._cell_parts)).strip()
            )
            self._cur_row.append((txt, self._rowspan, self._colspan))
            self._cell_parts = []

    def _flush_row(self):
        self._flush_cell()
        if self._in_row:
            self._in_row = False
            if self._cur_row:
                self._raw_rows.append(self._cur_row)
            self._cur_row = []

    def handle_starttag(self, tag, attrs):
        t = tag.lower()
        if t == "table":
            if self._in_table:
                self._flush_row()
                grid = self._expand_grid(self._raw_rows)
                if grid:
                    self.tables.append(grid)
            self._in_table = True
            self._raw_rows = []
        elif self._in_table and t == "tr":
            self._flush_row()
            self._in_row = True
            self._cur_row = []
        elif self._in_row and t in ("td", "th"):
            self._flush_cell()
            self._in_cell = True
            self._cell_parts = []
            ad = {k.lower(): (v or "1") for k, v in attrs}
            try:
                self._rowspan = max(1, int(ad.get("rowspan", "1")))
            except ValueError:
                self._rowspan = 1
            try:
                self._colspan = max(1, int(ad.get("colspan", "1")))
            except ValueError:
                self._colspan = 1
        elif self._in_cell and t == "br":
            self._cell_parts.append(" ")

    def handle_data(self, data):
        if self._in_cell:
            self._cell_parts.append(data)

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in ("td", "th") and self._in_cell:
            self._flush_cell()
        elif t == "tr" and self._in_row:
            self._flush_row()
        elif t == "table" and self._in_table:
            self._flush_row()
            self._in_table = False
            grid = self._expand_grid(self._raw_rows)
            if grid:
                self.tables.append(grid)

    @staticmethod
    def _expand_grid(raw_rows):
        if not raw_rows:
            return []
        occupied = {}
        max_col = 0
        num_rows = len(raw_rows)
        for r_idx, row in enumerate(raw_rows):
            c_idx = 0
            for txt, rspan, cspan in row:
                while (r_idx, c_idx) in occupied:
                    c_idx += 1
                for dr in range(rspan):
                    for dc in range(cspan):
                        nr = r_idx + dr
                        nc = c_idx + dc
                        num_rows = max(num_rows, nr + 1)
                        max_col = max(max_col, nc + 1)
                        occupied[(nr, nc)] = (
                            txt if (dr == 0 and dc == 0) else ""
                        )
                c_idx += cspan
        grid = []
        for r in range(num_rows):
            r_vals = [occupied.get((r, c), "") for c in range(max_col)]
            if any(v.strip() for v in r_vals):
                grid.append(r_vals)
        return grid


def extract_html_tables_from_text(text):
    """Extract and clean HTML <table>...</table> blocks emitted by VLM OCR."""
    if not text or "<table" not in text.lower():
        return []
    parser = _HTMLTableParser()
    try:
        parser.feed(text)
    except Exception:  # nosec B110
        return []
    cleaned_tables = []
    for raw_grid in parser.tables:
        cleaned = clean_table_rows(raw_grid)
        if cleaned:
            cleaned_tables.append(cleaned)
        elif raw_grid:
            cleaned_tables.append(raw_grid)
    return cleaned_tables


TYPHOON_V15_PROMPT = (
    "Extract all text from the image.\n\n\n"
    "Instructions:\n"
    "- Only return the clean Markdown.\n"
    "- Do not include any explanation or extra text.\n"
    "- You must include all information on the page.\n\n\n"
    "Formatting Rules:\n"
    "- Tables: Render tables using <table>...</table> in clean HTML format.\n"
    "- Equations: Render equations using LaTeX syntax with inline ($...$) and block ($$...$$).\n"
    "- Images/Charts/Diagrams: Wrap any clearly defined visual areas (e.g. charts, diagrams, pictures) in:\n\n\n"
    "<figure>\n"
    "Describe the image's main elements (people, objects, text), note any contextual clues "
    "(place, event, culture), mention visible text and its meaning, provide deeper analysis "
    "when relevant (especially for financial charts, graphs, or documents), comment on style "
    "or architecture if relevant, then give a concise overall summary. Describe in Thai.\n"
    "</figure>\n\n\n"
    "- Page Numbers: Wrap page numbers in <page_number>...</page_number> "
    "(e.g., <page_number>14</page_number>).\n"
    "- Checkboxes: Use ☐ for unchecked and ☑ for checked boxes.\n"
)


def _resize_image_if_needed(img, max_size=1800):
    """Downscale PIL image only when width or height exceeds max_size (never upscale)."""
    width, height = img.size
    if width <= 0 or height <= 0 or max_size <= 0:
        return img
    if width > max_size or height > max_size:
        from PIL import Image

        if width >= height:
            scale = max_size / float(width)
            new_size = (max_size, max(1, int(height * scale)))
        else:
            scale = max_size / float(height)
            new_size = (max(1, int(width * scale)), max_size)
        return img.resize(new_size, Image.Resampling.LANCZOS)
    return img


def _get_torch_device():
    """Return 'cuda' on NVIDIA GPUs, 'mps' on Apple Silicon Metal, or 'cpu'."""
    try:
        import torch

        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except ImportError:
        pass
    return "cpu"


def _has_gpu_accel():
    """Return True when CUDA or Apple Silicon MPS acceleration is available."""
    return _get_torch_device() in ("cuda", "mps")


def unload_vlm_models():
    """Explicitly release CUDA/MPS VRAM caches between sequential VLM runs."""
    gc.collect()
    try:
        import torch

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        elif hasattr(torch, "mps") and hasattr(torch.mps, "empty_cache"):
            torch.mps.empty_cache()
    except ImportError:
        pass


def _run_typhoon_transformers_vlm(
    image_paths,
    model_id="typhoon-ai/typhoon-ocr1.5-2b",
    load_in_4bit=False,
    max_new_tokens=2048,
    max_image_dim=1800,
):
    """Run SCB 10X Typhoon-OCR v1.5 (Qwen3-VL-2B or Qwen2.5-VL-3B-QAT) locally on GPU/MPS."""
    import importlib.util
    import torch
    from PIL import Image
    from transformers import AutoModelForImageTextToText, AutoProcessor

    unload_vlm_models()
    device = _get_torch_device()
    use_4bit = bool(load_in_4bit and torch.cuda.is_available())
    has_accelerate = importlib.util.find_spec("accelerate") is not None
    load_kwargs = {
        "attn_implementation": "sdpa",
    }
    if use_4bit or (device == "cuda" and has_accelerate):
        load_kwargs["device_map"] = "auto"
    if use_4bit:
        from transformers import BitsAndBytesConfig

        load_kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_quant_type="nf4",
        )
    else:
        load_kwargs["dtype"] = torch.bfloat16

    model = AutoModelForImageTextToText.from_pretrained(
        model_id, **load_kwargs
    )
    if "device_map" not in load_kwargs:
        model = model.to(device)
    model = model.eval()
    processor = AutoProcessor.from_pretrained(model_id)

    vlm_texts = {}
    try:
        for img_p in image_paths:
            pil_img = Image.open(img_p).convert("RGB")
            pil_img = _resize_image_if_needed(pil_img, max_size=max_image_dim)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": TYPHOON_V15_PROMPT},
                        {"type": "image", "image": pil_img},
                    ],
                }
            ]
            inputs = processor.apply_chat_template(
                messages,
                tokenize=True,
                add_generation_prompt=True,
                return_dict=True,
                return_tensors="pt",
            ).to(model.device)
            with torch.inference_mode():
                generated_ids = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    do_sample=False,
                    repetition_penalty=1.1,
                )
            in_len = inputs["input_ids"].shape[1]
            out_ids = [out[in_len:] for out in generated_ids]
            decoded = processor.batch_decode(
                out_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=False,
            )[0]
            vlm_texts[img_p] = normalize_text(decoded.strip())
            del inputs, generated_ids, out_ids
    finally:
        del model, processor
        unload_vlm_models()

    suffix = "_4bit" if use_4bit else "_bf16"
    short_name = model_id.split("/")[-1].lower().replace("-", "_")
    return {
        "vlm_executed": True,
        "engine": f"hf_{short_name}{suffix}_{device}",
        "vlm_texts": vlm_texts,
    }


def _render_page_batch(batch_args):
    """Worker helper opening fitz.Document once per worker batch of pages."""
    pdf_path, dpi, items = batch_args
    import fitz

    if hasattr(fitz, "no_recommend_layout"):
        fitz.no_recommend_layout()

    rendered = []
    doc = fitz.open(pdf_path)
    try:
        for page_idx, out_png in items:
            pix = doc[page_idx].get_pixmap(dpi=dpi)
            pix.save(out_png)
            rendered.append((page_idx, out_png))
        return rendered
    finally:
        doc.close()


def ocr_image_local(image_path, langs=None, profile="auto", has_thai_hint=False):
    """Run local offline OCR respecting profile (nano=none, edge=RapidOCR/Tesseract) + Thai guard."""
    prof = resolve_hardware_profile(profile)
    if prof["profile"] == "nano" or not prof["allow_local_cpu_ocr"]:
        return {"engine": "none", "text": ""}

    if langs is None:
        langs = ["th", "en"]
    lang_key = tuple(langs)

    # Thai Script Guard: RapidOCR ONNX defaults to Latin/CJK PP-OCR models and garbles Thai.
    if has_thai_hint:
        if prof["has_tesseract"] or (
            "pytesseract" in sys.modules and bool(shutil.which("tesseract"))
        ):
            try:
                import pytesseract
                from PIL import Image

                avail_langs = []
                if hasattr(pytesseract, "get_languages"):
                    try:
                        avail_langs = [
                            str(lg).lower()
                            for lg in pytesseract.get_languages(config="")
                        ]
                    except Exception:  # nosec B110
                        avail_langs = []
                if "tha" in avail_langs:
                    img = Image.open(image_path)
                    text = normalize_text(
                        pytesseract.image_to_string(img, lang="tha+eng").strip()
                    )
                    if text:
                        return {"engine": "pytesseract", "text": text}
            except Exception:  # nosec B110
                pass

        if prof["allow_easyocr"]:
            try:
                with contextlib.redirect_stdout(sys.stderr):
                    import easyocr

                    reader = _EASYOCR_READERS.get(lang_key)
                    if reader is None:
                        use_gpu = _has_gpu_accel()
                        reader = easyocr.Reader(
                            list(langs), gpu=use_gpu, verbose=False
                        )
                        _EASYOCR_READERS[lang_key] = reader
                    lines = reader.readtext(image_path, detail=0, paragraph=True)
                text = normalize_text("\n".join(lines).strip())
                if text:
                    return {"engine": "easyocr", "text": text}
            except Exception:  # nosec B110
                pass

        return {
            "engine": "skipped_thai_guard",
            "text": "",
            "ocr_warning": "rapidocr_latin_only_skipped_for_thai",
        }

    # Under edge (and when RapidOCR ONNX is installed), try pure-CPU ONNX first (0 torch)
    if prof["profile"] == "edge" or prof["has_rapidocr"]:
        try:
            global _RAPIDOCR_READER
            from rapidocr_onnxruntime import RapidOCR

            if _RAPIDOCR_READER is None:
                _RAPIDOCR_READER = RapidOCR()
            result, _ = _RAPIDOCR_READER(image_path)
            lines = [str(item[1]) for item in (result or []) if len(item) >= 2 and item[1]]
            text = normalize_text("\n".join(lines).strip())
            if text:
                return {"engine": "rapidocr_onnxruntime", "text": text}
        except Exception:  # nosec B110
            pass

    if prof["allow_easyocr"]:
        try:
            with contextlib.redirect_stdout(sys.stderr):
                import easyocr

                reader = _EASYOCR_READERS.get(lang_key)
                if reader is None:
                    use_gpu = _has_gpu_accel()
                    try:
                        reader = easyocr.Reader(
                            list(langs), gpu=use_gpu, verbose=False
                        )
                    except Exception:  # nosec B110
                        reader = easyocr.Reader(
                            ["en"], gpu=use_gpu, verbose=False
                        )
                    _EASYOCR_READERS[lang_key] = reader
                lines = reader.readtext(image_path, detail=0, paragraph=True)
            text = normalize_text("\n".join(lines).strip())
            if text:
                return {"engine": "easyocr", "text": text}
        except Exception:  # nosec B110
            pass

    try:
        import pytesseract
        from PIL import Image

        img = Image.open(image_path)
        text = normalize_text(pytesseract.image_to_string(img).strip())
        if text:
            return {"engine": "pytesseract", "text": text}
    except Exception:  # nosec B110
        pass

    return {"engine": "none", "text": ""}


def _read_text_file(path):
    """Read UTF-8 text from a file if it exists, otherwise return empty."""
    if path and os.path.isfile(path):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return normalize_text(fh.read().strip())
    return ""


def run_vlm_engine(
    target_path, output_dir, image_paths=None, vlm_backend="auto", profile="auto"
):
    """Attempt SGLang server, SCB 10X Typhoon-OCR v1.5, or Baidu Unlimited-OCR VLM."""
    prof = resolve_hardware_profile(profile)
    if not prof["allow_vlm"]:
        return {
            "vlm_executed": False,
            "engine": f"profile_{prof['profile']}_cpu_only",
            "vlm_texts": {},
            "reason": f"VLM disabled under profile={prof['profile']!r}.",
        }

    targets = image_paths or [target_path]

    # Explicit Typhoon-OCR v1.5 local backends
    if vlm_backend in ("typhoon-2b", "typhoon-3b-qat", "typhoon-3b-4bit"):
        try:
            if _has_gpu_accel():
                t_model = (
                    "typhoon-ai/typhoon-ocr1.5-2b"
                    if vlm_backend == "typhoon-2b"
                    else "typhoon-ai/typhoon-ocr1.5-3b-qat"
                )
                return _run_typhoon_transformers_vlm(
                    targets,
                    model_id=t_model,
                    load_in_4bit=(vlm_backend == "typhoon-3b-4bit"),
                )
        except Exception as exc:  # nosec B110
            return {
                "vlm_executed": False,
                "engine": "local_fallback",
                "vlm_texts": {},
                "reason": f"Typhoon VLM ({vlm_backend}) failed: {exc}",
            }

    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(script_dir, "infer.py"),
        os.path.join(os.getcwd(), "tools", "Unlimited-OCR", "infer.py"),
    ]
    infer_script = next(
        (p for p in candidates if p and os.path.isfile(p)), None
    )

    sglang_live = False
    if vlm_backend in ("auto", "sglang"):
        try:
            import urllib.request

            req = urllib.request.Request("http://127.0.0.1:10000/health")
            if not req.full_url.startswith(("http://", "https://")):
                raise ValueError("Invalid URL scheme")
            with urllib.request.urlopen(req, timeout=1.5) as resp:  # nosec B310
                sglang_live = resp.status == 200
        except Exception:  # nosec B110
            sglang_live = False

    if infer_script and sglang_live:
        stage_dir = os.path.join(output_dir, "_vlm_stage")
        shutil.rmtree(stage_dir, ignore_errors=True)
        os.makedirs(stage_dir, exist_ok=True)
        staged_map = {}
        for img_p in targets:
            if img_p.lower().endswith(".pdf"):
                continue
            base_name = os.path.basename(img_p)
            stem, ext = os.path.splitext(base_name)
            if ext.lower() in (".tif", ".tiff"):
                dst_p = os.path.join(stage_dir, f"{stem}.png")
                from PIL import Image

                Image.open(img_p).save(dst_p)
            else:
                dst_p = os.path.join(stage_dir, base_name)
                if os.path.abspath(img_p) != os.path.abspath(dst_p):
                    shutil.copy2(img_p, dst_p)
            staged_map[img_p] = os.path.join(output_dir, f"{stem}.md")

        flag = "--image_dir" if staged_map else "--pdf"
        flag_val = stage_dir if staged_map else target_path
        cmd = [
            sys.executable,
            infer_script,
            flag,
            flag_val,
            "--output_dir",
            output_dir,
        ]
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False
        )
        if proc.returncode == 0:
            vlm_texts = {
                img_p: _read_text_file(md_p)
                for img_p, md_p in staged_map.items()
            }
            return {
                "vlm_executed": True,
                "engine": "sglang_infer_py",
                "vlm_texts": vlm_texts,
                "stdout_tail": (proc.stdout or "")[-400:],
            }

    # In "auto" mode on CUDA/MPS, try Typhoon-OCR v1.5 (2B) first if available, then Unlimited-OCR-2
    if vlm_backend == "auto":
        try:
            if _has_gpu_accel():
                typhoon_env = os.environ.get(
                    "TYPHOON_OCR_MODEL", "typhoon-ai/typhoon-ocr1.5-2b"
                ).strip()
                return _run_typhoon_transformers_vlm(
                    targets, model_id=typhoon_env, load_in_4bit=False
                )
        except Exception:  # nosec B110
            pass

    if vlm_backend in ("auto", "unlimited-ocr"):
        try:
            import torch

            device = _get_torch_device()
            if device in ("cuda", "mps"):
                from transformers import AutoModel, AutoTokenizer

                unload_vlm_models()
                env_model = os.environ.get("UNLIMITED_OCR_MODEL", "").strip()
                model_candidates = (
                    [env_model]
                    if env_model
                    else ["baidu/Unlimited-OCR-2", "baidu/Unlimited-OCR"]
                )
                tokenizer = None
                model = None
                model_name = model_candidates[0]
                for cand_model in model_candidates:
                    try:
                        tokenizer = AutoTokenizer.from_pretrained(
                            cand_model, trust_remote_code=True
                        )
                        model = (
                            AutoModel.from_pretrained(
                                cand_model,
                                trust_remote_code=True,
                                use_safetensors=True,
                                torch_dtype=torch.bfloat16,
                            )
                            .eval()
                            .to(device)
                        )
                        model_name = cand_model
                        break
                    except Exception:  # nosec B110
                        continue
                if model is None or tokenizer is None:
                    raise RuntimeError("No Unlimited-OCR model available")

                vlm_texts = {}
                try:
                    if image_paths and len(image_paths) > 1:
                        res = model.infer_multi(
                            tokenizer,
                            prompt="<image>Multi page parsing.",
                            image_files=image_paths,
                            output_path=output_dir,
                            image_size=1024,
                            max_length=32768,
                            no_repeat_ngram_size=35,
                            ngram_window=1024,
                            save_results=True,
                        )
                        if isinstance(res, tuple):
                            res = res[0]
                        if isinstance(res, list):
                            for img_p, txt in zip(image_paths, res):
                                vlm_texts[img_p] = normalize_text(
                                    str(txt or "")
                                )
                        elif isinstance(res, str):
                            if "<PAGE>" in res:
                                parts = [
                                    p.strip()
                                    for p in res.split("<PAGE>")
                                    if p.strip()
                                ]
                                for img_p, txt in zip(image_paths, parts):
                                    vlm_texts[img_p] = normalize_text(txt)
                            else:
                                vlm_texts[image_paths[0]] = normalize_text(res)
                    else:
                        img_target = (
                            image_paths[0] if image_paths else target_path
                        )
                        res = model.infer(
                            tokenizer,
                            prompt="<image>document parsing.",
                            image_file=img_target,
                            output_path=output_dir,
                            base_size=1024,
                            image_size=640,
                            crop_mode=True,
                            max_length=32768,
                            no_repeat_ngram_size=35,
                            ngram_window=128,
                            save_results=True,
                        )
                        if isinstance(res, tuple):
                            res = res[0]
                        if isinstance(res, str):
                            vlm_texts[img_target] = normalize_text(
                                res.replace("<PAGE>", "").strip()
                            )
                finally:
                    del model, tokenizer
                    unload_vlm_models()

                return {
                    "vlm_executed": True,
                    "engine": f"hf_{model_name.split('/')[-1].lower()}_{device}",
                    "vlm_texts": vlm_texts,
                }
        except Exception:  # nosec B110
            pass

    return {
        "vlm_executed": False,
        "engine": "local_fallback",
        "vlm_texts": {},
        "reason": "No active CUDA/MPS/SGLang VLM server; using local OCR engine.",
    }


def _dedup_merge_page_tables(vector_tables, aligned_tables, return_meta=False):
    """Merge vector/booktabs tables with aligned-block tables without duplicates."""
    merged = []
    seen_sigs = set()
    vec_sets = []
    for item in vector_tables or ():
        is_dict = isinstance(item, dict)
        rows = item["rows"] if is_dict else item
        if not rows:
            continue
        flat = tuple(tuple(c.strip() for c in r) for r in rows[:4])
        seen_sigs.add(flat)
        cells = {
            re.sub(r"\s+", " ", str(c or "").strip().lower())
            for r in rows
            for c in r
            if str(c or "").strip()
        }
        toks = set()
        for c in cells:
            toks.update(t for t in c.split() if len(t) >= 2)
        if cells:
            vec_sets.append((cells, toks))
        if return_meta:
            merged.append(
                dict(item)
                if is_dict
                else {"rows": rows, "source": "vector_grid"}
            )
        else:
            merged.append(rows)

    for item in aligned_tables or ():
        rows = item["rows"]
        flat = tuple(tuple(c.strip() for c in r) for r in rows[:4])
        if flat in seen_sigs:
            continue
        aln_cells = {
            re.sub(r"\s+", " ", str(c or "").strip().lower())
            for r in rows
            for c in r
            if str(c or "").strip()
        }
        aln_toks = set()
        for c in aln_cells:
            aln_toks.update(t for t in c.split() if len(t) >= 2)
        is_dup = False
        if aln_cells:
            for vcells, vtoks in vec_sets:
                cell_ov = len(vcells & aln_cells) / max(1, min(len(vcells), len(aln_cells)))
                tok_ov = len(vtoks & aln_toks) / max(1, len(aln_toks))
                if cell_ov >= 0.45 or (aln_toks and tok_ov >= 0.60):
                    is_dup = True
                    break
        if is_dup:
            continue
        seen_sigs.add(flat)
        if aln_cells:
            vec_sets.append((aln_cells, aln_toks))
        merged.append(dict(item) if return_meta else rows)

    if return_meta:
        merged.sort(
            key=lambda t: (
                float((t.get("norm_bbox") or [0.0, 0.0, 1.0, 1.0])[1]),
                float((t.get("norm_bbox") or [0.0, 0.0, 1.0, 1.0])[0]),
            )
        )
    return merged


_HEADER_SCHEMA_KW_RE = re.compile(
    r"\b(?:item|no|code|id|name|type|desc(?:ription)?|qty|quantity|unit|price|"
    r"cost|amount|total|budget|status|phase|zone|area|share|owner|material|"
    r"spec(?:ification)?|remarks?|note|date|category|diameter|flow|contractor|"
    r"phone|license|floor|level|room|finish)\b|"
    r"รายการ|ลำดับ|จำนวน|หน่วย|ราคา|พื้นที่|หมายเหตุ|สถานะ|หมวด",
    re.IGNORECASE,
)


def _norm_header_cell(cell):
    """Normalize a table header cell while stripping continuation tags."""
    s = normalize_text(str(cell or "")).strip().lower()
    s = re.sub(r"\(\s*cont(?:inued)?\.?\s*\)|\(\s*ต่อ\s*\)", "", s)
    return re.sub(r"\s+", " ", s).strip()


def _col_iou_1d(b1, b2):
    """Return 1D normalized X-interval IoU and center drift."""
    inter = max(0.0, min(float(b1[1]), float(b2[1])) - max(float(b1[0]), float(b2[0])))
    union = max(1e-6, max(float(b1[1]), float(b2[1])) - min(float(b1[0]), float(b2[0])))
    c1 = 0.5 * (float(b1[0]) + float(b1[1]))
    c2 = 0.5 * (float(b2[0]) + float(b2[1]))
    return inter / union, abs(c1 - c2)


def _align_table_columns_for_stitch(prev_item, next_item):
    """Gate 3 & Gate 4: align column bounds (recovering blank-pruned cols) and check X-IoU/drift."""
    p_rows = prev_item.get("rows") or []
    n_rows = next_item.get("rows") or []
    if not p_rows or not n_rows:
        return None

    p_cols = list(prev_item.get("col_bounds_norm") or [])
    n_cols = list(next_item.get("col_bounds_norm") or [])
    p_raw = list(prev_item.get("raw_col_bounds_norm") or p_cols)
    n_raw = list(next_item.get("raw_col_bounds_norm") or n_cols)

    p_ncols = len(p_rows[0])
    n_ncols = len(n_rows[0])

    # Fallback when synthetic callers omit col_bounds_norm entirely
    if not p_cols or not n_cols:
        if p_ncols != n_ncols:
            return None
        return {
            "prev_rows": [list(r) + [""] * (p_ncols - len(r)) for r in p_rows],
            "next_rows": [list(r) + [""] * (n_ncols - len(r)) for r in n_rows],
            "col_bounds_norm": p_cols or n_cols,
            "raw_col_bounds_norm": p_raw or n_raw,
            "mean_iou": 1.0,
            "median_drift": 0.0,
            "blank_col_recovered": False,
        }

    if len(p_cols) != p_ncols or len(n_cols) != n_ncols:
        return None

    if len(p_cols) == len(n_cols):
        ious = []
        drifts = []
        for pb, nb in zip(p_cols, n_cols):
            iou, drift = _col_iou_1d(pb, nb)
            ious.append(iou)
            drifts.append(drift)
        mean_iou = sum(ious) / max(1, len(ious))
        min_iou = min(ious) if ious else 0.0
        s_drifts = sorted(drifts)
        med_drift = s_drifts[len(s_drifts) // 2] if s_drifts else 1.0
        if mean_iou >= 0.80 and min_iou >= 0.50 and med_drift <= 0.025:
            return {
                "prev_rows": [list(r) + [""] * (p_ncols - len(r)) for r in p_rows],
                "next_rows": [list(r) + [""] * (n_ncols - len(r)) for r in n_rows],
                "col_bounds_norm": p_cols,
                "raw_col_bounds_norm": p_raw if len(p_raw) >= len(p_cols) else p_cols,
                "mean_iou": round(mean_iou, 4),
                "median_drift": round(med_drift, 4),
                "blank_col_recovered": False,
            }
        # Only abort early when neither fragment pruned any raw columns; otherwise fall through to Gate 3
        if len(p_raw) <= len(p_cols) and len(n_raw) <= len(n_cols):
            return None

    # Gate 3: Blank-column pruning recovery via raw_col_bounds_norm / X-interval union
    master = list(p_raw if len(p_raw) >= len(n_raw) else n_raw)
    for b in p_cols + n_cols:
        matched = False
        for mb in master:
            iou, drift = _col_iou_1d(b, mb)
            if iou >= 0.45 or drift <= 0.035:
                matched = True
                break
        if not matched:
            master.append(list(b))
    master.sort(key=lambda b: (float(b[0]), float(b[1])))
    n_master = len(master)
    if n_master < max(len(p_cols), len(n_cols)):
        return None

    def _map_cols(cols_list):
        mapping = {}
        used_slots = set()
        for ci, cb in enumerate(cols_list):
            best_si = None
            best_score = -1e9
            for si, mb in enumerate(master):
                if si in used_slots:
                    continue
                iou, drift = _col_iou_1d(cb, mb)
                if iou >= 0.45 or drift <= 0.04:
                    sc = iou - 2.0 * drift
                    if sc > best_score:
                        best_score = sc
                        best_si = si
            if best_si is None:
                return None
            used_slots.add(best_si)
            mapping[ci] = best_si
        return mapping

    p_map = _map_cols(p_cols)
    n_map = _map_cols(n_cols)
    if p_map is None or n_map is None:
        return None

    p_by_slot = {si: p_cols[ci] for ci, si in p_map.items()}
    n_by_slot = {si: n_cols[ci] for ci, si in n_map.items()}
    shared_slots = sorted(set(p_by_slot.keys()) & set(n_by_slot.keys()))
    if len(shared_slots) < min(len(p_cols), len(n_cols)):
        return None

    ious = []
    drifts = []
    for si in shared_slots:
        iou, drift = _col_iou_1d(p_by_slot[si], n_by_slot[si])
        ious.append(iou)
        drifts.append(drift)
    mean_iou = sum(ious) / max(1, len(ious))
    min_iou = min(ious) if ious else 0.0
    s_drifts = sorted(drifts)
    med_drift = s_drifts[len(s_drifts) // 2] if s_drifts else 1.0
    if mean_iou < 0.80 or min_iou < 0.50 or med_drift > 0.025:
        return None

    # Ensure unpopulated slots actually have valid blank-column provenance or don't collide
    def _expand_rows(rows, cmap):
        out = []
        for r in rows:
            new_r = [""] * n_master
            for ci, si in cmap.items():
                if ci < len(r):
                    new_r[si] = r[ci]
            out.append(new_r)
        return out

    return {
        "prev_rows": _expand_rows(p_rows, p_map),
        "next_rows": _expand_rows(n_rows, n_map),
        "col_bounds_norm": master,
        "raw_col_bounds_norm": master,
        "mean_iou": round(mean_iou, 4),
        "median_drift": round(med_drift, 4),
        "blank_col_recovered": True,
    }


def _evaluate_header_gate5(prev_rows, next_rows, blank_recovered=False):
    """Gate 5: detect repeated headers to strip vs distinct header schemas to block."""
    h_prev = prev_rows[0]
    h_next = next_rows[0]
    ncols = max(len(h_prev), len(h_next))
    np_cells = [_norm_header_cell(h_prev[i] if i < len(h_prev) else "") for i in range(ncols)]
    nn_cells = [_norm_header_cell(h_next[i] if i < len(h_next) else "") for i in range(ncols)]

    pair_sims = []
    for a, b in zip(np_cells, nn_cells):
        if a and b:
            pair_sims.append(difflib.SequenceMatcher(None, a, b).ratio())
        elif a or b:
            if not blank_recovered:
                pair_sims.append(0.0)
    mean_sim = (sum(pair_sims) / len(pair_sims)) if pair_sims else 0.0
    full_sim = difflib.SequenceMatcher(
        None,
        " | ".join(c for c in np_cells if c),
        " | ".join(c for c in nn_cells if c),
    ).ratio()
    header_sim = max(mean_sim, full_sim)

    if np_cells == nn_cells or header_sim >= 0.90:
        return "strip_repeated", header_sim

    # Bridge row on row 0 of next table is NOT a distinct table header
    if BRIDGE_CARRY_RE.search(" ".join(h_next)):
        return "keep_data", header_sim

    prev_body = prev_rows[1:]
    next_body = next_rows[1:]

    # Determine which columns are numeric in table body
    num_col_flags = []
    for ci in range(ncols):
        body_vals = [
            str(r[ci]).strip()
            for r in (prev_body + next_body)
            if ci < len(r) and str(r[ci]).strip()
        ]
        if body_vals:
            n_num = sum(1 for v in body_vals if NUMERIC_CELL_RE.match(v))
            num_col_flags.append((n_num / float(len(body_vals))) >= 0.50)
        else:
            num_col_flags.append(False)

    non_empty_hn = [str(c).strip() for c in h_next if str(c).strip()]
    hn_num_cnt = sum(1 for c in non_empty_hn if NUMERIC_CELL_RE.match(c))
    hn_num_ratio = hn_num_cnt / max(1, len(non_empty_hn))

    # Signal 1: numeric body column(s) topped by non-numeric alpha label in h_next
    text_over_num_col = 0
    for ci, is_num_col in enumerate(num_col_flags):
        val = str(h_next[ci]).strip() if ci < len(h_next) else ""
        if is_num_col and val and not NUMERIC_CELL_RE.match(val) and not re.match(r"^\d+$", val):
            text_over_num_col += 1
    if text_over_num_col >= 1 and hn_num_ratio < 0.35 and header_sim < 0.75:
        return "block_distinct_header", header_sim

    # Signal 2: >=2 header-schema keywords across h_next with low similarity to h_prev
    kw_hits = sum(1 for c in non_empty_hn if _HEADER_SCHEMA_KW_RE.search(c))
    if kw_hits >= 2 and hn_num_ratio < 0.35 and header_sim < 0.65 and len(next_body) >= 1:
        return "block_distinct_header", header_sim

    # Signal 3: all-text header row containing zero digits/codes while body contains codes/numbers
    hn_has_digit = any(re.search(r"\d", c) for c in non_empty_hn)
    hp_has_digit = any(re.search(r"\d", str(c)) for c in h_prev)
    nb_has_digit = any(
        re.search(r"\d", str(c))
        for r in next_body[:4]
        for c in r
    )
    if (
        (not hn_has_digit)
        and (not hp_has_digit)
        and nb_has_digit
        and len(non_empty_hn) >= 2
        and header_sim < 0.45
        and len(next_body) >= 1
    ):
        return "block_distinct_header", header_sim

    return "keep_data", header_sim


def stitch_multipage_tables(
    page_tables: list, page_prose_stats: dict | None = None
):
    """Run 6-gate cascade to stitch multi-page continuation tables across consecutive pages."""
    if not page_tables:
        return {"stitched_tables": [], "per_page_tables": {}, "merge_events": []}

    by_page = {}
    for idx, raw_t in enumerate(page_tables):
        if not isinstance(raw_t, dict) or not raw_t.get("rows"):
            continue
        p_num = int(raw_t.get("page", 1))
        t_copy = copy.deepcopy(raw_t)
        t_copy["page"] = p_num
        t_copy["start_page"] = p_num
        t_copy["end_page"] = p_num
        t_copy["pages"] = [p_num]
        t_copy["merged"] = False
        t_copy["superseded_csv_paths"] = []
        t_copy.setdefault("table_index", idx + 1)
        by_page.setdefault(p_num, []).append(t_copy)

    for p_num, items in by_page.items():
        items.sort(
            key=lambda t: (
                float((t.get("norm_bbox") or [0.0, 0.0, 1.0, 1.0])[1]),
                float((t.get("norm_bbox") or [0.0, 0.0, 1.0, 1.0])[0]),
                int(t.get("table_index", 0)),
            )
        )

    sorted_pages = sorted(by_page.keys())
    prose_stats = page_prose_stats or {}
    merge_events = []

    # Track the active tail chain for each page so 3+ pages fold transitively
    page_slots = {p: list(by_page[p]) for p in sorted_pages}
    # Map any folded table slot back to the owning chain dict on start_page
    merged_owner = {}

    for i in range(len(sorted_pages) - 1):
        p_prev = sorted_pages[i]
        p_next = sorted_pages[i + 1]
        if p_next != p_prev + 1:
            continue
        prev_list = page_slots.get(p_prev) or []
        next_list = page_slots.get(p_next) or []
        if not prev_list or not next_list:
            continue

        prev_slot = prev_list[-1]
        owner = merged_owner.get(id(prev_slot), prev_slot)
        next_item = next_list[0]

        # Gate 1: Consecutive page seam AND (<120 interstitial prose chars OR continuation signal)
        st_prev = prose_stats.get(p_prev) or prose_stats.get(str(p_prev)) or {}
        st_next = prose_stats.get(p_next) or prose_stats.get(str(p_next)) or {}
        below_chars = int(
            st_prev.get("prose_chars_below_last", st_prev.get("chars_below", 0)) or 0
        )
        above_chars = int(
            st_next.get("prose_chars_above_first", st_next.get("chars_above", 0)) or 0
        )
        interstitial_chars = int(
            st_next.get("interstitial_chars", below_chars + above_chars)
        )
        seam_texts = [
            str(st_prev.get("text_below_last") or ""),
            str(st_next.get("text_above_first") or ""),
            str(prev_slot.get("context_below") or ""),
            str(next_item.get("context_above") or ""),
            " ".join(str(c) for c in (next_item["rows"][0] if next_item["rows"] else ())),
            " ".join(str(c) for c in (owner["rows"][-1] if owner["rows"] else ())),
        ]
        has_cont_signal = bool(
            st_prev.get("has_continuation_signal")
            or st_next.get("has_continuation_signal")
            or any(CONT_SIGNAL_RE.search(t) for t in seam_texts if t)
        )
        if interstitial_chars >= 120 and not has_cont_signal:
            continue

        # Gate 2 (Part A): Terminal A_neg shield on owner's tail rows
        tail_rows = owner["rows"][-2:] if len(owner["rows"]) >= 2 else owner["rows"][-1:]
        terminal_hit = False
        for tr in tail_rows:
            tr_txt = " ".join(str(c or "") for c in tr).strip()
            if TERMINAL_TOTAL_RE.search(tr_txt) and not BRIDGE_CARRY_RE.search(tr_txt):
                terminal_hit = True
                break
        if terminal_hit:
            continue

        # Gate 3 & Gate 4: Blank-col recovery + Column X-IoU >= 0.80 & median drift <= 0.025
        aligned = _align_table_columns_for_stitch(owner, next_item)
        if aligned is None:
            continue

        # Gate 5: Repeated header strip vs distinct-header A_neg shield
        gate5_action, hdr_sim = _evaluate_header_gate5(
            aligned["prev_rows"],
            aligned["next_rows"],
            blank_recovered=aligned["blank_col_recovered"],
        )
        if gate5_action == "block_distinct_header":
            continue

        header_stripped = gate5_action == "strip_repeated"
        cur_prev_rows = [list(r) for r in aligned["prev_rows"]]
        cur_next_rows = (
            [list(r) for r in aligned["next_rows"][1:]]
            if header_stripped
            else [list(r) for r in aligned["next_rows"]]
        )

        # Gate 2 (Part B): Bridge carry rows allow merge and strip duplicate seam carry rows
        stripped_bridge = []
        if cur_prev_rows:
            prev_tail_txt = " ".join(str(c or "") for c in cur_prev_rows[-1]).strip()
        else:
            prev_tail_txt = ""
        next_head_txt = (
            " ".join(str(c or "") for c in cur_next_rows[0]).strip()
            if cur_next_rows
            else ""
        )
        prev_is_bridge = bool(BRIDGE_CARRY_RE.search(prev_tail_txt))
        prev_is_carry = bool(
            re.search(r"\b(?:carried\s+forward|c/f)\b|ยอดยกไป", prev_tail_txt, re.IGNORECASE)
        )
        next_is_bridge = bool(BRIDGE_CARRY_RE.search(next_head_txt))
        next_is_brought = bool(
            re.search(r"\b(?:brought\s+forward|b/f)\b|ยอดยกมา", next_head_txt, re.IGNORECASE)
        )

        if prev_is_carry and (next_is_brought or next_is_bridge):
            stripped_bridge.append(prev_tail_txt)
            cur_prev_rows.pop()
            if cur_next_rows:
                stripped_bridge.append(next_head_txt)
                cur_next_rows.pop(0)
        elif next_is_brought or (prev_is_bridge and next_is_bridge):
            if cur_next_rows:
                stripped_bridge.append(next_head_txt)
                cur_next_rows.pop(0)
        elif prev_is_carry:
            stripped_bridge.append(prev_tail_txt)
            cur_prev_rows.pop()

        # Gate 6: Transitive folding across 3+ pages
        combined_rows = cur_prev_rows + cur_next_rows
        if not combined_rows:
            continue

        owner["rows"] = combined_rows
        owner["nrows"] = len(combined_rows)
        owner["ncols"] = len(combined_rows[0])
        owner["col_bounds_norm"] = aligned["col_bounds_norm"]
        owner["raw_col_bounds_norm"] = aligned["raw_col_bounds_norm"]
        owner["end_page"] = p_next
        if p_next not in owner["pages"]:
            owner["pages"].append(p_next)
        owner["merged"] = True
        if next_item.get("csv_path"):
            owner["superseded_csv_paths"].append(next_item["csv_path"])

        # Remove next_item from p_next's emitted list; if next_item was the ONLY table on p_next,
        # map next_item's slot ID to owner so p_next -> p_next+1 continues folding transitively!
        next_list.pop(0)
        if not next_list:
            page_slots[p_next] = [next_item]
            merged_owner[id(next_item)] = owner

        merge_events.append(
            {
                "from_page": p_prev,
                "to_page": p_next,
                "start_page": owner["start_page"],
                "interstitial_chars": interstitial_chars,
                "has_continuation_signal": has_cont_signal,
                "header_stripped": header_stripped,
                "header_similarity": round(hdr_sim, 4),
                "col_iou": aligned["mean_iou"],
                "col_drift": aligned["median_drift"],
                "blank_col_recovered": aligned["blank_col_recovered"],
                "bridge_detected": bool(prev_is_bridge or next_is_bridge),
                "stripped_bridge_rows": stripped_bridge,
            }
        )

    stitched_tables = []
    per_page_tables = {}
    for p_num in sorted_pages:
        kept = []
        for slot in page_slots[p_num]:
            if id(slot) in merged_owner:
                continue
            slot["nrows"] = len(slot["rows"])
            slot["ncols"] = len(slot["rows"][0]) if slot["rows"] else 0
            stitched_tables.append(slot)
            kept.append(slot)
        per_page_tables[p_num] = kept

    return {
        "stitched_tables": stitched_tables,
        "per_page_tables": per_page_tables,
        "merge_events": merge_events,
    }


def _parse_numeric_cell(val):
    """Parse numeric cell value (supports commas and optional trailing %) or return None."""
    s = normalize_text(str(val or "")).strip()
    if not s or not NUMERIC_CELL_RE.match(s):
        return None
    s_clean = s.rstrip("%").replace(",", "").strip()
    try:
        return float(s_clean)
    except ValueError:
        return None


def _diff_page_atoms(old_atoms, new_atoms, old_rect, new_rect, grid_axes, cols, rows):
    """Tolerance-match vector atoms (<=0.015 norm or <=2.0pt jitter = 0 diff)."""
    o_rx0, o_ry0 = float(old_rect.x0), float(old_rect.y0)
    o_pw = max(1.0, float(abs(old_rect.width)))
    o_ph = max(1.0, float(abs(old_rect.height)))
    n_rx0, n_ry0 = float(new_rect.x0), float(new_rect.y0)
    n_pw = max(1.0, float(abs(new_rect.width)))
    n_ph = max(1.0, float(abs(new_rect.height)))

    def _prep(atoms_list, rx0, ry0, pw, ph):
        out = []
        for a in atoms_list or ():
            txt = re.sub(r"\s+", " ", normalize_text(a.get("text") or "")).strip()
            if not txt:
                continue
            x0, y0, x1, y1 = float(a["x0"]), float(a["y0"]), float(a["x1"]), float(a["y1"])
            cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
            nx0 = max(0.0, min(1.0, (x0 - rx0) / pw))
            ny0 = max(0.0, min(1.0, (y0 - ry0) / ph))
            nx1 = max(0.0, min(1.0, (x1 - rx0) / pw))
            ny1 = max(0.0, min(1.0, (y1 - ry0) / ph))
            nx, ny = 0.5 * (nx0 + nx1), 0.5 * (ny0 + ny1)
            out.append(
                {
                    "text": txt,
                    "cx": cx,
                    "cy": cy,
                    "nx": nx,
                    "ny": ny,
                    "norm_bbox": [round(nx0, 4), round(ny0, 4), round(nx1, 4), round(ny1, 4)],
                    "pt_bbox": [round(x0, 2), round(y0, 2), round(x1, 2), round(y1, 2)],
                }
            )
        return out

    olds = _prep(old_atoms, o_rx0, o_ry0, o_pw, o_ph)
    news = _prep(new_atoms, n_rx0, n_ry0, n_pw, n_ph)

    def _within_tol(a, b):
        return (
            (abs(a["nx"] - b["nx"]) <= 0.015 and abs(a["ny"] - b["ny"]) <= 0.015)
            or (abs(a["cx"] - b["cx"]) <= 2.0 and abs(a["cy"] - b["cy"]) <= 2.0)
        )

    matched_o = set()
    matched_n = set()

    # Pass 1: exact text + tolerance match -> 0 diff
    by_text_n = {}
    for ni, na in enumerate(news):
        by_text_n.setdefault(na["text"], []).append(ni)

    for oi, oa in enumerate(olds):
        cands = by_text_n.get(oa["text"])
        if not cands:
            continue
        best_ni = None
        best_dist = 1e9
        for ni in cands:
            if ni in matched_n:
                continue
            na = news[ni]
            if _within_tol(oa, na):
                d = math.hypot(oa["cx"] - na["cx"], oa["cy"] - na["cy"])
                if d < best_dist:
                    best_dist = d
                    best_ni = ni
        if best_ni is not None:
            matched_o.add(oi)
            matched_n.add(best_ni)

    # Pass 2: same-location text change -> modified
    modified = []
    for oi, oa in enumerate(olds):
        if oi in matched_o:
            continue
        best_ni = None
        best_dist = 1e9
        for ni, na in enumerate(news):
            if ni in matched_n:
                continue
            if _within_tol(oa, na):
                d = math.hypot(oa["cx"] - na["cx"], oa["cy"] - na["cy"])
                if d < best_dist:
                    best_dist = d
                    best_ni = ni
        if best_ni is not None:
            na = news[best_ni]
            matched_o.add(oi)
            matched_n.add(best_ni)
            tid = _tile_id_from_norm_point(na["nx"], na["ny"], cols=cols, rows=rows)
            modified.append(
                {
                    "old_text": oa["text"],
                    "new_text": na["text"],
                    "norm_bbox": na["norm_bbox"],
                    "tile_id": tid,
                    "grid_ref": resolve_grid_ref(na["norm_bbox"], grid_axes),
                }
            )

    removed = []
    for oi, oa in enumerate(olds):
        if oi not in matched_o:
            tid = _tile_id_from_norm_point(oa["nx"], oa["ny"], cols=cols, rows=rows)
            removed.append(
                {
                    "text": oa["text"],
                    "norm_bbox": oa["norm_bbox"],
                    "tile_id": tid,
                    "grid_ref": resolve_grid_ref(oa["norm_bbox"], grid_axes),
                }
            )

    added = []
    for ni, na in enumerate(news):
        if ni not in matched_n:
            tid = _tile_id_from_norm_point(na["nx"], na["ny"], cols=cols, rows=rows)
            added.append(
                {
                    "text": na["text"],
                    "norm_bbox": na["norm_bbox"],
                    "tile_id": tid,
                    "grid_ref": resolve_grid_ref(na["norm_bbox"], grid_axes),
                }
            )

    return {"added": added, "removed": removed, "modified": modified}


def _diff_page_tables(old_tabs, new_tabs, grid_axes, cols, rows):
    """Diff structured tables cell-by-cell and compute numeric_delta when numeric."""
    cell_diffs = []
    used_new = set()
    pairs = []

    for oi, ot in enumerate(old_tabs):
        oh = " | ".join(ot["rows"][0]).lower() if ot.get("rows") else ""
        best_ni = None
        best_sim = 0.0
        for ni, nt in enumerate(new_tabs):
            if ni in used_new:
                continue
            nh = " | ".join(nt["rows"][0]).lower() if nt.get("rows") else ""
            sim = difflib.SequenceMatcher(None, oh, nh).ratio()
            if sim >= 0.70 and sim > best_sim:
                best_sim = sim
                best_ni = ni
        if best_ni is None and oi < len(new_tabs) and oi not in used_new:
            best_ni = oi
        if best_ni is not None:
            used_new.add(best_ni)
            pairs.append((oi, ot, new_tabs[best_ni]))

    for ti, ot, nt in pairs:
        o_rows = ot.get("rows") or []
        n_rows = nt.get("rows") or []
        headers = n_rows[0] if n_rows else (o_rows[0] if o_rows else [])
        nb = nt.get("norm_bbox") or ot.get("norm_bbox")
        tid = (
            _tile_id_from_norm_point(0.5 * (nb[0] + nb[2]), 0.5 * (nb[1] + nb[3]), cols=cols, rows=rows)
            if nb
            else None
        )
        gref = resolve_grid_ref(nb, grid_axes) if nb else None

        # Match rows by unique col-0 key if possible, else by index
        o_keys = [str(r[0]).strip().lower() if r else "" for r in o_rows]
        n_keys = [str(r[0]).strip().lower() if r else "" for r in n_rows]
        use_key_match = (
            len(o_rows) >= 2
            and len(n_rows) >= 2
            and len(set(o_keys)) == len(o_keys)
            and len(set(n_keys)) == len(n_keys)
            and all(o_keys)
            and all(n_keys)
        )
        row_pairs = []
        if use_key_match:
            n_by_k = {n_keys[ri]: (ri, n_rows[ri]) for ri in range(len(n_rows))}
            used_nr = set()
            for ri, rk in enumerate(o_keys):
                if rk in n_by_k:
                    nri, nr = n_by_k[rk]
                    used_nr.add(nri)
                    row_pairs.append((nri, o_rows[ri], nr, o_rows[ri][0]))
                else:
                    cell_diffs.append(
                        {
                            "table_index": ti + 1,
                            "row": ri,
                            "col": None,
                            "kind": "row_removed",
                            "row_key": o_rows[ri][0],
                            "col_header": headers[0] if headers else "col_0",
                            "old_value": " | ".join(str(c or "") for c in o_rows[ri]),
                            "new_value": "",
                            "numeric_delta": None,
                            "tile_id": tid,
                            "grid_ref": gref,
                        }
                    )
            for nri, nr in enumerate(n_rows):
                if nri not in used_nr:
                    cell_diffs.append(
                        {
                            "table_index": ti + 1,
                            "row": nri,
                            "col": None,
                            "kind": "row_added",
                            "row_key": nr[0] if nr else str(nri),
                            "col_header": headers[0] if headers else "col_0",
                            "old_value": "",
                            "new_value": " | ".join(str(c or "") for c in nr),
                            "numeric_delta": None,
                            "tile_id": tid,
                            "grid_ref": gref,
                        }
                    )
        else:
            for ri in range(min(len(o_rows), len(n_rows))):
                rk = o_rows[ri][0] if o_rows[ri] else str(ri)
                row_pairs.append((ri, o_rows[ri], n_rows[ri], rk))

        for ri, r_old, r_new, row_key in row_pairs:
            max_c = max(len(r_old), len(r_new))
            for ci in range(max_c):
                ov = re.sub(r"\s+", " ", str(r_old[ci] if ci < len(r_old) else "")).strip()
                nv = re.sub(r"\s+", " ", str(r_new[ci] if ci < len(r_new) else "")).strip()
                if ov != nv:
                    v_old = _parse_numeric_cell(ov)
                    v_new = _parse_numeric_cell(nv)
                    num_delta = (
                        round(v_new - v_old, 6)
                        if (v_old is not None and v_new is not None)
                        else None
                    )
                    col_hdr = headers[ci] if ci < len(headers) else f"col_{ci}"
                    cell_diffs.append(
                        {
                            "table_index": ti + 1,
                            "row": ri,
                            "col": ci,
                            "row_key": row_key,
                            "col_header": col_hdr,
                            "old_value": ov,
                            "new_value": nv,
                            "numeric_delta": num_delta,
                            "tile_id": tid,
                            "grid_ref": gref,
                        }
                    )
    return cell_diffs


def diff_pdf_drawings(
    old_pdf, new_pdf, pages=None, profile="edge", tile_grid="4x4"
):
    """Compare two PDF drawing revisions by sheet ID, callouts, schedule cells, atoms, and 72-DPI tile MAD."""
    import fitz
    from PIL import Image, ImageChops

    resolve_hardware_profile(profile)
    cols, rows = _parse_tile_grid(tile_grid)

    owns_old = not isinstance(old_pdf, fitz.Document)
    owns_new = not isinstance(new_pdf, fitz.Document)
    if owns_old and not os.path.exists(str(old_pdf)):
        raise FileNotFoundError(f"Old PDF not found for drawing diff: {old_pdf}")
    if owns_new and not os.path.exists(str(new_pdf)):
        raise FileNotFoundError(f"New PDF not found for drawing diff: {new_pdf}")
    doc_old = None
    doc_new = None

    try:
        doc_old = fitz.open(str(old_pdf)) if owns_old else old_pdf
        doc_new = fitz.open(str(new_pdf)) if owns_new else new_pdf

        def _sel_indices(total_p):
            if pages is None:
                return list(range(total_p))
            if isinstance(pages, str):
                return parse_page_selection(pages, total_p)
            return sorted({int(p) - 1 for p in pages if 1 <= int(p) <= total_p})

        def _extract_rev_page(doc_obj, page_idx):
            pg = doc_obj[page_idx]
            raw_t, tdict = _extract_text_and_dict_fast(pg)
            atoms = _extract_clean_text_atoms(pg, text_dict=tdict)
            drws = _safe_probe_drawings(pg)
            g_axes = extract_grid_axes(pg, drawings=drws, atoms=atoms)
            c_info = extract_sheet_callouts(
                pg,
                atoms=atoms,
                drawings=drws,
                grid_axes=g_axes,
                tile_grid=f"{cols}x{rows}",
            )
            vtabs = extract_tables_from_page(
                pg, fitz, raw_text=raw_t, drawings=drws, return_meta=True
            )
            atabs = _extract_aligned_block_tables(pg, atoms=atoms)
            tabs = _dedup_merge_page_tables(vtabs, atabs, return_meta=True)
            return {
                "page": page_idx + 1,
                "page_obj": pg,
                "atoms": atoms,
                "grid_axes": g_axes,
                "primary_sheet_id": c_info["primary_sheet_id"],
                "callouts": c_info["callouts"],
                "revision_deltas": c_info["revision_deltas"],
                "tables": tabs,
            }

        old_pages = [_extract_rev_page(doc_old, i) for i in _sel_indices(len(doc_old))]
        new_pages = [_extract_rev_page(doc_new, i) for i in _sel_indices(len(doc_new))]

        # Match by primary_sheet_id first, then positional fallback for unlabelled pages
        used_old = set()
        used_new = set()
        matched_pairs = []

        new_by_sid = {}
        for ni, npg in enumerate(new_pages):
            sid = npg["primary_sheet_id"]
            if sid:
                new_by_sid.setdefault(str(sid).upper(), []).append(ni)

        for oi, opg in enumerate(old_pages):
            sid = opg["primary_sheet_id"]
            if sid:
                cands = [ni for ni in new_by_sid.get(str(sid).upper(), ()) if ni not in used_new]
                if cands:
                    ni = cands[0]
                    used_old.add(oi)
                    used_new.add(ni)
                    matched_pairs.append(("sheet_id", opg, new_pages[ni]))

        rem_old = [opg for oi, opg in enumerate(old_pages) if oi not in used_old]
        rem_new = [npg for ni, npg in enumerate(new_pages) if ni not in used_new]
        unlabelled_old = [opg for opg in rem_old if not opg.get("primary_sheet_id")]
        unlabelled_new = [npg for npg in rem_new if not npg.get("primary_sheet_id")]
        labelled_rem_old = [opg for opg in rem_old if opg.get("primary_sheet_id")]
        labelled_rem_new = [npg for npg in rem_new if npg.get("primary_sheet_id")]
        for opg, npg in zip(unlabelled_old, unlabelled_new):
            matched_pairs.append(("positional", opg, npg))

        added_sheets = [
            {"page": npg["page"], "primary_sheet_id": npg["primary_sheet_id"]}
            for npg in (labelled_rem_new + unlabelled_new[len(unlabelled_old):])
        ]
        removed_sheets = [
            {"page": opg["page"], "primary_sheet_id": opg["primary_sheet_id"]}
            for opg in (labelled_rem_old + unlabelled_old[len(unlabelled_new):])
        ]

        sheet_diffs = []
        total_atom_diffs = 0
        total_table_diffs = 0
        total_callout_diffs = 0
        total_changed_tiles = 0

        for match_method, opg, npg in matched_pairs:
            g_axes = npg["grid_axes"] if (npg["grid_axes"]["x"] or npg["grid_axes"]["y"]) else opg["grid_axes"]
            atom_diffs = _diff_page_atoms(
                opg["atoms"],
                npg["atoms"],
                opg["page_obj"].rect,
                npg["page_obj"].rect,
                g_axes,
                cols,
                rows,
            )

            def _ckey(c):
                return (
                    str(c.get("kind") or ""),
                    str(c.get("detail_no") or ""),
                    str(c.get("target_sheet") or "").upper(),
                )

            o_cmap = {_ckey(c): c for c in opg["callouts"]}
            n_cmap = {_ckey(c): c for c in npg["callouts"]}
            added_callouts = [c for k, c in n_cmap.items() if k not in o_cmap]
            removed_callouts = [c for k, c in o_cmap.items() if k not in n_cmap]

            def _rkey(r):
                return (str(r.get("kind") or ""), str(r.get("rev_id") or ""), str(r.get("text") or ""))

            o_rmap = {_rkey(r): r for r in opg["revision_deltas"]}
            n_rmap = {_rkey(r): r for r in npg["revision_deltas"]}
            added_revs = [r for k, r in n_rmap.items() if k not in o_rmap]
            removed_revs = [r for k, r in o_rmap.items() if k not in n_rmap]

            table_cell_diffs = _diff_page_tables(
                opg["tables"], npg["tables"], g_axes, cols, rows
            )

            # 72 DPI grayscale tile Mean Absolute Difference (MAD > 0.012)
            opix = opg["page_obj"].get_pixmap(dpi=72, colorspace=fitz.csGRAY, alpha=False)
            npix = npg["page_obj"].get_pixmap(dpi=72, colorspace=fitz.csGRAY, alpha=False)
            o_im = Image.frombytes("L", [opix.width, opix.height], opix.samples)
            n_im = Image.frombytes("L", [npix.width, npix.height], npix.samples)
            if o_im.size != n_im.size:
                n_im = n_im.resize(o_im.size, Image.Resampling.BILINEAR)
            d_im = ImageChops.difference(o_im, n_im)
            iw, ih = d_im.size

            changed_tiles = []
            max_mad = 0.0
            for ri in range(rows):
                for ci in range(cols):
                    nx0, ny0 = ci / float(cols), ri / float(rows)
                    nx1, ny1 = (ci + 1) / float(cols), (ri + 1) / float(rows)
                    px0 = max(0, min(iw - 1, int(round(nx0 * iw))))
                    py0 = max(0, min(ih - 1, int(round(ny0 * ih))))
                    px1 = max(px0 + 1, min(iw, int(round(nx1 * iw))))
                    py1 = max(py0 + 1, min(ih, int(round(ny1 * ih))))
                    tile_crop = d_im.crop((px0, py0, px1, py1))
                    hist = tile_crop.histogram()
                    npx = max(1, (px1 - px0) * (py1 - py0))
                    mad = sum(val * cnt for val, cnt in enumerate(hist)) / (255.0 * npx)
                    if mad > max_mad:
                        max_mad = mad
                    if mad > 0.012:
                        tid = f"{_col_index_to_letters(ci)}{ri + 1}"
                        nb = [round(nx0, 4), round(ny0, 4), round(nx1, 4), round(ny1, 4)]
                        changed_tiles.append(
                            {
                                "tile_id": tid,
                                "mad": round(mad, 6),
                                "norm_bbox": nb,
                                "grid_ref": resolve_grid_ref(nb, g_axes),
                            }
                        )
            changed_tiles.sort(key=lambda t: (-t["mad"], t["tile_id"]))

            n_atom_d = (
                len(atom_diffs["added"])
                + len(atom_diffs["removed"])
                + len(atom_diffs["modified"])
            )
            n_call_d = len(added_callouts) + len(removed_callouts)
            n_rev_d = len(added_revs) + len(removed_revs)
            has_changes = bool(
                n_atom_d > 0
                or n_call_d > 0
                or n_rev_d > 0
                or len(table_cell_diffs) > 0
                or len(changed_tiles) > 0
            )
            total_atom_diffs += n_atom_d
            total_table_diffs += len(table_cell_diffs)
            total_callout_diffs += n_call_d
            total_changed_tiles += len(changed_tiles)

            sheet_diffs.append(
                {
                    "primary_sheet_id": npg["primary_sheet_id"] or opg["primary_sheet_id"],
                    "old_page": opg["page"],
                    "new_page": npg["page"],
                    "match_method": match_method,
                    "has_changes": has_changes,
                    "atom_diffs": atom_diffs,
                    "callout_diffs": {
                        "added": added_callouts,
                        "removed": removed_callouts,
                    },
                    "revision_diffs": {
                        "added": added_revs,
                        "removed": removed_revs,
                    },
                    "table_cell_diffs": table_cell_diffs,
                    "changed_tiles": changed_tiles,
                    "tile_mad_max": round(max_mad, 6),
                }
            )

        return {
            "version": __version__,
            "old_pdf": str(old_pdf) if owns_old else getattr(doc_old, "name", "old_doc"),
            "new_pdf": str(new_pdf) if owns_new else getattr(doc_new, "name", "new_doc"),
            "tile_grid": f"{cols}x{rows}",
            "summary": {
                "matched_sheets": len(sheet_diffs),
                "changed_sheets": sum(1 for s in sheet_diffs if s["has_changes"]),
                "added_sheets": len(added_sheets),
                "removed_sheets": len(removed_sheets),
                "total_atom_diffs": total_atom_diffs,
                "total_table_cell_diffs": total_table_diffs,
                "total_callout_diffs": total_callout_diffs,
                "total_changed_tiles": total_changed_tiles,
            },
            "sheets": sheet_diffs,
            "added_sheets": added_sheets,
            "removed_sheets": removed_sheets,
        }
    finally:
        if owns_old:
            doc_old.close()
        if owns_new:
            doc_new.close()


def _save_page_tables(output_dir, page_num, rec, raw_tables, seen_md=None):
    """Persist deduplicated tables to CSV and track metadata + Markdown entries on rec."""
    added = 0
    seen = seen_md if seen_md is not None else set(rec.get("md_tables") or [])
    entries = rec.setdefault("table_entries", [])
    for item in raw_tables or ():
        is_dict = isinstance(item, dict)
        rows = item.get("rows") if is_dict else item
        if not rows:
            continue
        md_tab = rows_to_markdown(rows)
        if md_tab in seen:
            continue
        seen.add(md_tab)
        rec["table_count"] += 1
        added += 1
        t_idx = rec["table_count"]
        csv_name = f"table_p{page_num}_{t_idx}.csv"
        csv_path = os.path.join(output_dir, csv_name)
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f_csv:
            writer = csv.writer(f_csv)
            writer.writerows(rows)
        rec["md_tables"].append(md_tab)
        meta_entry = {
            "page": page_num,
            "table_index": t_idx,
            "csv_path": csv_path,
            "rows": [list(r) for r in rows],
            "source": item.get("source", "vector_grid") if is_dict else "vector_grid",
        }
        if is_dict:
            for mk in ("norm_bbox", "bbox", "col_bounds_norm", "raw_col_bounds_norm", "keep_cols"):
                if mk in item and item[mk] is not None:
                    meta_entry[mk] = item[mk]
        entries.append(meta_entry)
    return added


def _apply_stitched_tile_result(output_dir, page_num, rec, stitched, spatial_page=None):
    """Apply tile_and_stitch_canvas output into page record, tables, and spatial_index."""
    stitched_text = stitched.get("stitched_text") or ""
    engines = stitched.get("engines") or []
    tile_eng = engines[0] if engines else "tile_ocr"
    warnings = stitched.get("ocr_warnings") or []
    if warnings:
        rec["ocr_warning"] = warnings[0]

    if stitched_text:
        if rec["char_count"] >= 60:
            rec["text"] = f"{rec['text']}\n\n### Visual / Tiled Canvas OCR\n{stitched_text}"
            rec["engine"] = f"pymupdf_vector+{tile_eng}"
        else:
            rec["text"] = stitched_text
            rec["engine"] = tile_eng
        rec["char_count"] = non_ws_count(rec["text"])
    elif warnings and rec["char_count"] < 60:
        rec["engine"] = "skipped_thai_guard"

    added = _save_page_tables(output_dir, page_num, rec, stitched.get("tables") or [])
    if spatial_page is not None and stitched.get("spatial_blocks"):
        _merge_tile_blocks_into_spatial_page(spatial_page, stitched["spatial_blocks"])
    return added


_PAGE_NUM_STAMP_RE = re.compile(
    r"^\s*(?:page\s*)?\d+(?:\s*(?:/|of)\s*\d+)?\s*$", re.IGNORECASE
)


def _compute_page_prose_stats_for_stitch(page_records, stage0_ctx, selected_indices):
    """Measure prose chars above first table and below last table per page for Gate 1."""
    stats = {}
    for p_idx in selected_indices:
        rec = page_records[p_idx]
        p_num = rec["page"]
        entries = rec.get("table_entries") or []
        if not entries:
            continue
        ctx = stage0_ctx.get(p_idx) or {}
        rx0, ry0, rx1, ry1 = ctx.get("page_rect") or (0.0, 0.0, 1000.0, 1000.0)
        ph = max(1.0, float(ry1) - float(ry0))
        atoms = ctx.get("atoms") or []

        sorted_e = sorted(
            entries,
            key=lambda t: (
                float((t.get("norm_bbox") or [0.0, 0.0, 1.0, 1.0])[1]),
                float((t.get("norm_bbox") or [0.0, 0.0, 1.0, 1.0])[0]),
            ),
        )
        first_nb = sorted_e[0].get("norm_bbox") or [0.0, 0.0, 1.0, 1.0]
        last_nb = sorted_e[-1].get("norm_bbox") or [0.0, 0.0, 1.0, 1.0]

        above_texts = []
        below_texts = []
        above_chars = 0
        below_chars = 0
        for a in atoms:
            txt = (a.get("text") or "").strip()
            if not txt:
                continue
            ny0 = (float(a["y0"]) - float(ry0)) / ph
            ny1 = (float(a["y1"]) - float(ry0)) / ph
            nyc = 0.5 * (ny0 + ny1)
            is_stamp = bool(
                _PAGE_NUM_STAMP_RE.match(txt) and (nyc <= 0.07 or nyc >= 0.93)
            )
            if nyc < float(first_nb[1]) - 0.002:
                above_texts.append(txt)
                if not is_stamp:
                    above_chars += non_ws_count(txt)
            elif nyc > float(last_nb[3]) + 0.002:
                below_texts.append(txt)
                if not is_stamp:
                    below_chars += non_ws_count(txt)

        stats[p_num] = {
            "prose_chars_above_first": above_chars,
            "prose_chars_below_last": below_chars,
            "text_above_first": " ".join(above_texts),
            "text_below_last": " ".join(below_texts),
        }
    return stats


def _format_drawing_diff_markdown(diff_res):
    """Format drawing_diff summary into a concise Markdown section."""
    s = diff_res.get("summary") or {}
    lines = [
        "## Drawing Revision Diff",
        "",
        f"- Matched Sheets: `{s.get('matched_sheets', 0)}` "
        f"(Changed: `{s.get('changed_sheets', 0)}`, "
        f"Added: `{s.get('added_sheets', 0)}`, "
        f"Removed: `{s.get('removed_sheets', 0)}`)",
        f"- Atom Diffs: `{s.get('total_atom_diffs', 0)}` | "
        f"Table Cell Diffs: `{s.get('total_table_cell_diffs', 0)}` | "
        f"Callout Diffs: `{s.get('total_callout_diffs', 0)}` | "
        f"Changed Tiles (MAD > 0.012): `{s.get('total_changed_tiles', 0)}`",
    ]
    for sh in diff_res.get("sheets") or ():
        if not sh.get("has_changes"):
            continue
        sid = sh.get("primary_sheet_id") or f"Page {sh.get('new_page')}"
        tiles_str = ", ".join(
            f"{t['tile_id']}(MAD={t['mad']:.4f})"
            for t in (sh.get("changed_tiles") or ())[:6]
        )
        lines.append(
            f"- **{sid}** (old p{sh.get('old_page')} -> new p{sh.get('new_page')}): "
            f"changed_tiles=[{tiles_str or 'none'}], "
            f"table_diffs={len(sh.get('table_cell_diffs') or ())}"
        )
    return "\n".join(lines)


def extract_pdf(
    pdf_path,
    output_dir,
    mode="auto",
    dpi=None,
    pages_arg=None,
    workers=4,
    langs=None,
    vlm_backend="auto",
    profile="auto",
    genomes_file=None,
    drawing_index=False,
    render_mode=None,
    bbox=None,
    query=None,
    tile=None,
    tile_grid="4x4",
    grid_overlay=True,
    sniper_query=None,
    xlaya_bridge=False,
    diff_with=None,
    stitch_tables=True,
):
    """Single-pass C++ PyMuPDF text/table/spatial extractor with profile-gated OCR."""
    t_start = time.time()
    os.makedirs(output_dir, exist_ok=True)
    text_out_path = os.path.join(output_dir, "extracted_text.txt")
    md_out_path = os.path.join(output_dir, "extracted_document.md")
    manifest_path = os.path.join(output_dir, "ocr_manifest.json")
    spatial_index_path = os.path.join(output_dir, "spatial_index.json")
    drawing_diff_path = os.path.join(output_dir, "drawing_diff.json")
    pages_dir = os.path.join(output_dir, "_tmp_pages")

    prof = resolve_hardware_profile(profile)
    genomes = load_xocr_genomes(genomes_file)
    eff_ocr_dpi = int(dpi if dpi is not None else 300)

    import fitz

    if hasattr(fitz, "no_recommend_layout"):
        fitz.no_recommend_layout()

    doc = fitz.open(pdf_path)
    doc_closed = False
    try:
        total_doc_pages = len(doc)
        selected_indices = parse_page_selection(pages_arg, total_doc_pages)

        page_records = {}
        stage0_ctx = {}
        pages_needing_ocr = []
        tables_extracted = 0
        has_fitz_tables = hasattr(fitz.Page, "find_tables")
        spatial_pages = []
        spatial_page_map = {}
        rendered_views_all = []

        for page_idx in selected_indices:
            t_p0 = time.perf_counter()
            page = doc[page_idx]
            page_num = page_idx + 1
            raw_text, text_dict = _extract_text_and_dict_fast(page)
            qual = evaluate_page_quality(raw_text, page)
            regime_info = classify_page_regime(
                page,
                raw_text=raw_text,
                qual=qual,
                genomes=genomes,
                profile=prof["profile"],
                text_dict=text_dict,
            )
            stage0_ms = round((time.perf_counter() - t_p0) * 1000.0, 2)

            vector_tables = []
            if has_fitz_tables:
                vector_tables = extract_tables_from_page(
                    page,
                    fitz,
                    raw_text=raw_text,
                    drawings=regime_info.get("_drawings"),
                    return_meta=True,
                )
            aligned_tables = _extract_aligned_block_tables(
                page, atoms=regime_info.get("_atoms")
            )
            page_tables = _dedup_merge_page_tables(
                vector_tables, aligned_tables, return_meta=True
            )

            page_needs_ocr = bool(qual["needs_ocr"] or regime_info["needs_ocr"])
            if mode == "vlm" or (mode == "auto" and page_needs_ocr):
                pages_needing_ocr.append(page_idx)

            if drawing_index or sniper_query:
                s_idx = extract_spatial_cad_index(
                    page,
                    tile_grid=tile_grid,
                    tables=page_tables,
                    regime_info=regime_info,
                )
                spatial_pages.append(s_idx)
                spatial_page_map[page_idx] = s_idx

            if render_mode:
                r_res = render_drawing_view(
                    doc,
                    page_num=page_num,
                    render_mode=render_mode,
                    bbox=bbox,
                    query=query,
                    tile=tile,
                    tile_grid=tile_grid,
                    dpi=dpi,
                    grid_overlay=grid_overlay,
                    max_bytes=prof["max_bytes"],
                    profile=prof["profile"],
                    out_path=output_dir,
                    cache_dir=os.path.join(output_dir, "_composite_cache"),
                )
                for v in r_res["views"]:
                    rendered_views_all.append(
                        {k: val for k, val in v.items() if k != "png_bytes"}
                    )

            rec = {
                "page": page_num,
                "text": qual["clean_text"],
                "char_count": qual["char_count"],
                "garble_ratio": qual["garble_ratio"],
                "needs_ocr": page_needs_ocr,
                "needs_vision": regime_info["needs_vision"],
                "regime": regime_info["regime"],
                "regime_confidence": regime_info["confidence"],
                "conformal_abstain": regime_info["conformal_abstain"],
                "image_count": qual["image_count"],
                "image_area_ratio": qual["image_area_ratio"],
                "unexplained_canvas_ratio": regime_info["unexplained_canvas_ratio"],
                "exploded_glyphs_suspected": bool(
                    regime_info.get("exploded_glyphs_suspected", False)
                ),
                "short_stroke_ratio": float(
                    regime_info.get("short_stroke_ratio", 0.0)
                ),
                "stage0_ms": stage0_ms,
                "table_count": 0,
                "md_tables": [],
                "table_entries": [],
                "engine": "pymupdf_vector",
            }
            tables_extracted += _save_page_tables(output_dir, page_num, rec, page_tables)
            page_records[page_idx] = rec
            stage0_ctx[page_idx] = {
                "page_rect": (
                    float(page.rect.x0),
                    float(page.rect.y0),
                    float(page.rect.x1),
                    float(page.rect.y1),
                ),
                "page_width_pt": round(float(abs(page.rect.width)), 2),
                "page_height_pt": round(float(abs(page.rect.height)), 2),
                "atoms": regime_info.get("_atoms") or [],
                "tables": list(page_tables),
                "drawing_stats": {
                    "vector_drawing_count": regime_info.get("vector_drawing_count", 0)
                },
                "thai_chars": len(re.findall(r"[\u0e00-\u0e7f]", qual["clean_text"])),
            }

        doc_has_thai = any(
            stage0_ctx[p_idx]["thai_chars"] >= 3 for p_idx in selected_indices
        )

        image_paths = []
        vlm_info = None
        can_run_ocr = prof["allow_vlm"] or (
            prof["allow_local_cpu_ocr"] and prof["has_cpu_ocr"]
        )
        tiled_pages = []
        whole_pages = []
        tile_prep_map = {}

        if pages_needing_ocr and mode in ("auto", "vlm") and can_run_ocr:
            for p_idx in pages_needing_ocr:
                rec = page_records[p_idx]
                ctx = stage0_ctx[p_idx]
                pw = ctx["page_width_pt"]
                ph = ctx["page_height_pt"]
                should_tile = (
                    prof["profile"] != "nano"
                    and rec["needs_ocr"]
                    and (
                        rec["regime"] == "HYBRID_COMPOSITE_DRAWING"
                        or rec.get("exploded_glyphs_suspected")
                        or (
                            rec["regime"]
                            in ("RASTER_DRAWING_OR_MAP", "VECTOR_CAD_DRAWING")
                            and max(pw, ph) >= 1100
                        )
                    )
                )
                if should_tile:
                    c_bbox = compute_unexplained_canvas_bbox(
                        ctx["page_rect"],
                        ctx["atoms"],
                        tables=ctx["tables"],
                        drawing_stats=ctx["drawing_stats"],
                    )
                    prep = tile_and_stitch_canvas(
                        doc,
                        p_idx,
                        c_bbox,
                        prof["profile"],
                        ocr_tile_fn=None,
                        cache_dir=os.path.join(output_dir, "_composite_cache"),
                    )
                    tile_prep_map[p_idx] = prep
                    tiled_pages.append(p_idx)
                    rec["tiled_canvas"] = {
                        "grid": prep["grid"],
                        "canvas_bbox": prep["canvas_bbox"],
                        "tile_count": len(prep["tiles"]),
                    }
                else:
                    whole_pages.append(p_idx)

        doc.close()
        doc_closed = True
    finally:
        if not doc_closed:
            doc.close()

    if not has_fitz_tables:
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                for page_idx in selected_indices:
                    page_num = page_idx + 1
                    raw_tabs = pdf.pages[page_idx].extract_tables() or []
                    cleaned_tabs = [
                        rows
                        for rows in (clean_table_rows(rt) for rt in raw_tabs)
                        if rows
                    ]
                    tables_extracted += _save_page_tables(
                        output_dir, page_num, page_records[page_idx], cleaned_tabs
                    )
        except ImportError:
            pass

    if pages_needing_ocr and mode in ("auto", "vlm") and can_run_ocr:
        whole_map = {}
        if whole_pages:
            os.makedirs(pages_dir, exist_ok=True)
            render_items = [
                (
                    p_idx,
                    os.path.join(pages_dir, f"page_{p_idx + 1:03d}.png"),
                )
                for p_idx in whole_pages
            ]
            max_w = max(1, min(int(workers), len(render_items)))
            batches = [
                (pdf_path, eff_ocr_dpi, render_items[i::max_w])
                for i in range(max_w)
                if render_items[i::max_w]
            ]
            if len(batches) > 1:
                with ThreadPoolExecutor(max_workers=len(batches)) as pool:
                    for batch_res in pool.map(_render_page_batch, batches):
                        for p_idx, out_png in batch_res:
                            whole_map[p_idx] = out_png
            else:
                for p_idx, out_png in _render_page_batch(batches[0]):
                    whole_map[p_idx] = out_png

        whole_image_paths = [whole_map[p_idx] for p_idx in whole_pages]
        tile_image_paths = [
            t["png_path"]
            for p_idx in tiled_pages
            for t in tile_prep_map[p_idx]["tiles"]
        ]
        image_paths = whole_image_paths + tile_image_paths

        vlm_info = run_vlm_engine(
            pdf_path,
            output_dir,
            image_paths=image_paths,
            vlm_backend=vlm_backend,
            profile=prof["profile"],
        )
        if vlm_info.get("vlm_executed"):
            vlm_map = vlm_info.get("vlm_texts") or {}
            vlm_eng = vlm_info.get("engine", "vlm")
            for p_idx in whole_pages:
                img_path = whole_map[p_idx]
                v_txt = vlm_map.get(img_path, "")
                if v_txt:
                    rec = page_records[p_idx]
                    if (
                        rec["regime"] == "HYBRID_COMPOSITE_DRAWING"
                        and rec["char_count"] >= 100
                    ):
                        rec["text"] = f"{rec['text']}\n\n### Visual / Raster Zone OCR\n{v_txt}"
                        rec["engine"] = f"pymupdf_vector+{vlm_eng}"
                    else:
                        rec["text"] = v_txt
                        rec["engine"] = vlm_eng
                    rec["char_count"] = non_ws_count(rec["text"])
                    if rec["table_count"] == 0:
                        html_tabs = extract_html_tables_from_text(v_txt)
                        tables_extracted += _save_page_tables(
                            output_dir, p_idx + 1, rec, html_tabs
                        )
            for p_idx in tiled_pages:
                prep = tile_prep_map[p_idx]
                for t in prep["tiles"]:
                    t["text"] = vlm_map.get(t["png_path"], "")
                    t["engine"] = vlm_eng
                stitched = stitch_tile_results(prep["tiles"])
                tables_extracted += _apply_stitched_tile_result(
                    output_dir,
                    p_idx + 1,
                    page_records[p_idx],
                    stitched,
                    spatial_page=spatial_page_map.get(p_idx),
                )
        else:
            for p_idx in whole_pages:
                page_has_thai = doc_has_thai or stage0_ctx[p_idx]["thai_chars"] >= 3
                ocr_res = ocr_image_local(
                    whole_map[p_idx],
                    langs=langs,
                    profile=prof["profile"],
                    has_thai_hint=page_has_thai,
                )
                rec = page_records[p_idx]
                if ocr_res.get("ocr_warning"):
                    rec["ocr_warning"] = ocr_res["ocr_warning"]
                ocr_nws = non_ws_count(ocr_res["text"])
                if ocr_res["text"] and (
                    ocr_nws > rec["char_count"]
                    or rec["garble_ratio"] > 0.05
                    or rec["regime"] == "HYBRID_COMPOSITE_DRAWING"
                ):
                    if (
                        rec["regime"] == "HYBRID_COMPOSITE_DRAWING"
                        and rec["char_count"] >= 100
                    ):
                        rec["text"] = (
                            f"{rec['text']}\n\n### Visual / Raster Zone OCR\n{ocr_res['text']}"
                        )
                        rec["engine"] = f"pymupdf_vector+{ocr_res['engine']}"
                    else:
                        rec["text"] = ocr_res["text"]
                        rec["engine"] = ocr_res["engine"]
                    rec["char_count"] = non_ws_count(rec["text"])
                elif ocr_res.get("ocr_warning") and rec["char_count"] < 60:
                    rec["engine"] = ocr_res["engine"]

            for p_idx in tiled_pages:
                page_has_thai = doc_has_thai or stage0_ctx[p_idx]["thai_chars"] >= 3
                prep = tile_prep_map[p_idx]
                for t in prep["tiles"]:
                    ocr_res = ocr_image_local(
                        t["png_path"],
                        langs=langs,
                        profile=prof["profile"],
                        has_thai_hint=page_has_thai,
                    )
                    t["text"] = str(ocr_res.get("text") or "")
                    t["engine"] = ocr_res.get("engine")
                    t["ocr_warning"] = ocr_res.get("ocr_warning")
                stitched = stitch_tile_results(prep["tiles"])
                tables_extracted += _apply_stitched_tile_result(
                    output_dir,
                    p_idx + 1,
                    page_records[p_idx],
                    stitched,
                    spatial_page=spatial_page_map.get(p_idx),
                )

    table_merge_events = []
    if stitch_tables:
        all_table_entries = [
            entry
            for p_idx in selected_indices
            for entry in (page_records[p_idx].get("table_entries") or ())
        ]
        if len(all_table_entries) >= 2 and len({e["page"] for e in all_table_entries}) >= 2:
            prose_stats = _compute_page_prose_stats_for_stitch(
                page_records, stage0_ctx, selected_indices
            )
            stitch_res = stitch_multipage_tables(
                all_table_entries, page_prose_stats=prose_stats
            )
            table_merge_events = stitch_res.get("merge_events") or []
            if table_merge_events:
                for st in stitch_res["stitched_tables"]:
                    for sup_path in st.get("superseded_csv_paths") or ():
                        if sup_path and os.path.isfile(sup_path):
                            os.unlink(sup_path)

                per_page_stitched = stitch_res.get("per_page_tables") or {}
                tables_extracted = 0
                for p_idx in selected_indices:
                    rec = page_records[p_idx]
                    p_num = rec["page"]
                    kept_tabs = per_page_stitched.get(p_num, [])
                    # Stage surviving CSV renames/rewrites cleanly so disk table_p{page}_{idx}.csv
                    # always matches Table {page}.{idx} in extracted_document.md 1-to-1 (FALS-R2-07).
                    old_csvs = [
                        t.get("csv_path")
                        for t in kept_tabs
                        if t.get("csv_path") and os.path.isfile(t["csv_path"])
                    ]
                    target_csvs = [
                        os.path.join(output_dir, f"table_p{p_num}_{t_i}.csv")
                        for t_i in range(1, len(kept_tabs) + 1)
                    ]
                    for old_p in old_csvs:
                        if old_p not in target_csvs and os.path.isfile(old_p):
                            os.unlink(old_p)
                    for t_i, (t, target_csv) in enumerate(zip(kept_tabs, target_csvs), start=1):
                        if t.get("rows"):
                            with open(target_csv, "w", encoding="utf-8-sig", newline="") as f_csv:
                                writer = csv.writer(f_csv)
                                writer.writerows(t["rows"])
                        t["table_index"] = t_i
                        t["csv_path"] = target_csv

                    rec["table_entries"] = list(kept_tabs)
                    rec["md_tables"] = [rows_to_markdown(t["rows"]) for t in kept_tabs]
                    rec["md_table_labels"] = [
                        (
                            f"Table {p_num}.{t_i} (Stitched Pages {t['start_page']}..{t['end_page']})"
                            if len(t.get("pages") or ()) > 1
                            else f"Table {p_num}.{t_i}"
                        )
                        for t_i, t in enumerate(kept_tabs, start=1)
                    ]
                    rec["table_count"] = len(kept_tabs)
                    tables_extracted += len(kept_tabs)

    diff_res = None
    if diff_with:
        diff_res = diff_pdf_drawings(
            diff_with,
            pdf_path,
            pages=pages_arg,
            profile=prof["profile"],
            tile_grid=tile_grid,
        )
        with open(drawing_diff_path, "w", encoding="utf-8", newline="\n") as f_diff:
            json.dump(diff_res, f_diff, indent=2, ensure_ascii=False)

    sniper_rois = []
    if sniper_query and spatial_pages:
        sniper_rois = rank_spatial_rois(
            {"pages": spatial_pages},
            sniper_query,
            top_k=5,
            xlaya_bridge=xlaya_bridge,
        )

    if drawing_index:
        with open(spatial_index_path, "w", encoding="utf-8", newline="\n") as f_idx:
            json.dump(
                {
                    "version": __version__,
                    "input": pdf_path,
                    "profile": prof["profile"],
                    "tile_grid": tile_grid,
                    "pages": spatial_pages,
                    "callout_graph": build_callout_graph(spatial_pages),
                },
                f_idx,
                indent=2,
                ensure_ascii=False,
            )

    txt_chunks = []
    md_chunks = []
    manifest_pages = []
    total_chars = 0

    for page_idx in selected_indices:
        rec = page_records[page_idx]
        p_num = rec["page"]
        total_chars += rec["char_count"]
        txt_chunks.append(f"--- PAGE {p_num} ---\n{rec['text']}\n")

        md_sec = [f"## Page {p_num}", "", rec["text"]]
        if rec["md_tables"]:
            md_sec.append(f"\n### Extracted Tables (Page {p_num})")
            md_labels = rec.get("md_table_labels") or [
                f"Table {p_num}.{t_i}" for t_i in range(1, len(rec["md_tables"]) + 1)
            ]
            for lbl, md_tab in zip(md_labels, rec["md_tables"]):
                md_sec.append(f"\n#### {lbl}\n\n{md_tab}")
        md_chunks.append("\n".join(md_sec))

        mpage = {
            "page": p_num,
            "char_count": rec["char_count"],
            "table_count": rec["table_count"],
            "garble_ratio": rec["garble_ratio"],
            "needs_ocr": rec["needs_ocr"],
            "needs_vision": rec["needs_vision"],
            "regime": rec["regime"],
            "regime_confidence": rec["regime_confidence"],
            "conformal_abstain": rec["conformal_abstain"],
            "image_count": rec["image_count"],
            "image_area_ratio": rec["image_area_ratio"],
            "unexplained_canvas_ratio": rec["unexplained_canvas_ratio"],
            "exploded_glyphs_suspected": rec["exploded_glyphs_suspected"],
            "short_stroke_ratio": rec["short_stroke_ratio"],
            "stage0_ms": rec["stage0_ms"],
            "engine": rec["engine"],
        }
        if rec.get("ocr_warning"):
            mpage["ocr_warning"] = rec["ocr_warning"]
        if rec.get("tiled_canvas"):
            mpage["tiled_canvas"] = rec["tiled_canvas"]
        manifest_pages.append(mpage)

    if diff_res is not None:
        md_chunks.append(_format_drawing_diff_markdown(diff_res))

    with open(text_out_path, "w", encoding="utf-8", newline="\n") as f_txt:
        f_txt.write("\n".join(txt_chunks))

    with open(md_out_path, "w", encoding="utf-8", newline="\n") as f_md:
        f_md.write("\n\n---\n\n".join(md_chunks) + "\n")

    elapsed_ms = round((time.time() - t_start) * 1000, 1)
    manifest_data = {
        "version": __version__,
        "profile": prof["profile"],
        "input": pdf_path,
        "total_pdf_pages": total_doc_pages,
        "pages_processed": len(selected_indices),
        "total_chars": total_chars,
        "tables_extracted": tables_extracted,
        "table_merge_events": table_merge_events,
        "low_text_or_ocr_pages": [p + 1 for p in pages_needing_ocr],
        "elapsed_ms": elapsed_ms,
        "pages": manifest_pages,
    }
    if drawing_index:
        manifest_data["spatial_index_path"] = spatial_index_path
    if rendered_views_all:
        manifest_data["rendered_views"] = rendered_views_all
    if sniper_query:
        manifest_data["sniper_query"] = sniper_query
        manifest_data["sniper_rois"] = sniper_rois
    if diff_res is not None:
        manifest_data["drawing_diff_path"] = drawing_diff_path
        manifest_data["drawing_diff_summary"] = diff_res["summary"]

    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f_man:
        json.dump(manifest_data, f_man, indent=2, ensure_ascii=False)

    res = {
        "version": __version__,
        "profile": prof["profile"],
        "pages_processed": len(selected_indices),
        "total_chars": total_chars,
        "tables_extracted": tables_extracted,
        "table_merge_events": table_merge_events,
        "low_text_pages": [p + 1 for p in pages_needing_ocr],
        "elapsed_ms": elapsed_ms,
        "text_path": text_out_path,
        "markdown_path": md_out_path,
        "manifest_path": manifest_path,
        "image_paths": image_paths,
    }
    if drawing_index:
        res["spatial_index_path"] = spatial_index_path
    if rendered_views_all:
        res["rendered_views"] = rendered_views_all
    if sniper_query:
        res["sniper_query"] = sniper_query
        res["sniper_rois"] = sniper_rois
    if diff_res is not None:
        res["drawing_diff_path"] = drawing_diff_path
        res["drawing_diff_summary"] = diff_res["summary"]
    if vlm_info:
        res["vlm"] = vlm_info
    return res


def extract_standalone_image(
    image_path, output_dir, langs=None, vlm_backend="auto", profile="auto"
):
    """Extract text and HTML tables from a standalone image (.png/.jpg/.webp/.tif)."""
    t_start = time.time()
    os.makedirs(output_dir, exist_ok=True)
    text_out_path = os.path.join(output_dir, "extracted_text.txt")
    md_out_path = os.path.join(output_dir, "extracted_document.md")
    manifest_path = os.path.join(output_dir, "ocr_manifest.json")

    prof = resolve_hardware_profile(profile)
    vlm_info = run_vlm_engine(
        image_path,
        output_dir,
        image_paths=[image_path],
        vlm_backend=vlm_backend,
        profile=prof["profile"],
    )
    extracted_text = ""
    engine_used = vlm_info.get("engine", "none")

    if vlm_info.get("vlm_executed"):
        vlm_map = vlm_info.get("vlm_texts") or {}
        extracted_text = vlm_map.get(image_path, "")
    if not extracted_text:
        lang_thai = bool(
            langs and any(str(lg).strip().lower().startswith("th") for lg in langs)
        )
        ocr_res = ocr_image_local(
            image_path,
            langs=langs,
            profile=prof["profile"],
            has_thai_hint=lang_thai,
        )
        extracted_text = ocr_res["text"]
        engine_used = ocr_res["engine"]

    html_tabs = extract_html_tables_from_text(extracted_text)
    md_tables = []
    tables_extracted = 0
    for rows in html_tabs:
        tables_extracted += 1
        csv_name = f"table_p1_{tables_extracted}.csv"
        csv_path = os.path.join(output_dir, csv_name)
        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f_csv:
            writer = csv.writer(f_csv)
            writer.writerows(rows)
        md_tables.append(rows_to_markdown(rows))

    with open(text_out_path, "w", encoding="utf-8") as f_txt:
        f_txt.write(extracted_text + "\n")
    with open(md_out_path, "w", encoding="utf-8") as f_md:
        f_md.write(f"## Image OCR ({os.path.basename(image_path)})\n\n")
        f_md.write(extracted_text + "\n")
        if md_tables:
            f_md.write("\n### Extracted Tables (Page 1)\n")
            for t_i, md_tab in enumerate(md_tables, start=1):
                f_md.write(f"\n#### Table 1.{t_i}\n\n{md_tab}\n")

    elapsed_ms = round((time.time() - t_start) * 1000, 1)
    nws_chars = non_ws_count(extracted_text)
    manifest_data = {
        "version": __version__,
        "profile": prof["profile"],
        "input": image_path,
        "pages_processed": 1,
        "total_chars": nws_chars,
        "tables_extracted": tables_extracted,
        "engine_used": engine_used,
        "elapsed_ms": elapsed_ms,
        "pages": [
            {
                "page": 1,
                "char_count": nws_chars,
                "table_count": tables_extracted,
                "garble_ratio": 0.0,
                "needs_ocr": True,
                "engine": engine_used,
            }
        ],
    }
    with open(manifest_path, "w", encoding="utf-8") as f_man:
        json.dump(manifest_data, f_man, indent=2, ensure_ascii=False)

    return {
        "version": __version__,
        "profile": prof["profile"],
        "status": "success" if extracted_text else "empty_or_failed",
        "pages_processed": 1,
        "total_chars": nws_chars,
        "tables_extracted": tables_extracted,
        "engine_used": engine_used,
        "elapsed_ms": elapsed_ms,
        "text_path": text_out_path,
        "markdown_path": md_out_path,
        "manifest_path": manifest_path,
        "vlm": vlm_info,
    }


def run_self_test(profile="nano", genomes_file=None):
    """Run synthetic validation suite for profiles, Stage 0, regimes, tables, and tiling."""
    import fitz
    from PIL import Image

    t0 = time.perf_counter()
    prof = resolve_hardware_profile(profile)
    if prof["profile"] in ("nano", "edge") and "torch" in sys.modules:
        raise AssertionError(
            f"PyTorch imported unexpectedly under profile={prof['profile']!r}"
        )

    # 1. Verify Thai PUA + Sara Am + Genome Simplex invariants
    sample = "ไร\uf70a สัดส\uf70aวน ก\u0e4d\u0e32ลัง น\u0e4d\u0e49\u0e32\u200b\ufeff"
    norm = normalize_thai_text(sample)
    assert norm == "ไร่ สัดส่วน กำลัง น้ำ", f"Unexpected normalization: {norm!r}"

    genomes = load_xocr_genomes(genomes_file)
    for reg in XOCR_REGIMES:
        w = genomes["weights"][reg]
        assert len(w) == 8, f"Expected 8 weights for {reg}"
        l1 = sum(abs(float(v)) for v in w)
        assert abs(l1 - 1.0) <= 1e-3, f"Simplex L1 != 1 for {reg}: {l1}"
        assert float(w[7]) <= 0.0, f"w[7] must be <= 0 for {reg}: {w[7]}"

    # 2. Verify canonical A1..D4 grid coordinates
    assert _norm_bbox_from_tile("A1", 4, 4) == [0.0, 0.0, 0.25, 0.25]
    assert _norm_bbox_from_tile("D1", 4, 4) == [0.75, 0.0, 1.0, 0.25]
    assert _norm_bbox_from_tile("D4", 4, 4) == [0.75, 0.75, 1.0, 1.0]

    # 3. Synthetic 4-regime + borderless table + multi-layer probe test
    with tempfile.TemporaryDirectory() as tmpdir:
        syn_pdf = os.path.join(tmpdir, "self_test_suite.pdf")
        doc = fitz.open()

        # Page 1: DIGITAL_TEXT_TABLE + 3-rule booktabs table
        p1 = doc.new_page(width=595, height=842)
        p1.insert_text((72, 60), "Engineering Design Specification Report", fontsize=12)
        for y in range(90, 260, 22):
            p1.insert_text(
                (72, y),
                "Detailed structural foundation specification and concrete mix ratios.",
                fontsize=10,
            )
        p1.insert_text((72, 290), "Table 1: Concrete Design Parameters", fontsize=10)
        for y in (305, 325, 385):
            p1.draw_line((72, y), (480, y), width=1.0)
        for y, c1, c2, c3 in [
            (320, "Grade", "f'c (MPa)", "Slump (mm)"),
            (342, "C30/37", "30", "100"),
            (362, "C40/50", "40", "125"),
            (380, "C50/60", "50", "150"),
        ]:
            p1.insert_text((80, y), c1, fontsize=10)
            p1.insert_text((240, y), c2, fontsize=10)
            p1.insert_text((390, y), c3, fontsize=10)

        # Page 2: VECTOR_CAD_DRAWING (Arch D sheet with scattered callouts + vector geometry)
        p2 = doc.new_page(width=1728, height=2592)
        for i in range(180):
            x = 120 + (i % 15) * 95
            y = 140 + (i // 15) * 180
            p2.draw_rect(fitz.Rect(x, y, x + 70, y + 70))
            p2.draw_line((100, y), (1600, y), width=0.5)
        for gx, lbl in [(200, "A"), (600, "B"), (1000, "C"), (1400, "D")]:
            p2.insert_text((gx, 80), f"GRID {lbl}", fontsize=14)
        for gy, lbl in [(300, "1"), (900, "2"), (1500, "3"), (2100, "4")]:
            p2.insert_text((60, gy), f"AX-{lbl}", fontsize=14)
        p2.insert_text((1350, 2420), "SHEET M-101 SCALE 1:100 REV 02", fontsize=14)

        # Page 3: RASTER_DRAWING_OR_MAP (full-page raster image, 0 text)
        p3 = doc.new_page(width=1190, height=842)
        rast_p3 = os.path.join(tmpdir, "raster_map.png")
        Image.new("RGB", (2400, 1700), (235, 242, 238)).save(rast_p3)
        p3.insert_image(p3.rect, filename=rast_p3)

        # Page 4: HYBRID_COMPOSITE_DRAWING (A1 raster map + borderless sidebar table)
        p4 = doc.new_page(width=2384, height=1684)
        rast_p4 = os.path.join(tmpdir, "hybrid_map.png")
        Image.new("RGB", (2200, 1600), (220, 232, 224)).save(rast_p4)
        p4.insert_image(fitz.Rect(0, 0, 1680, 1684), filename=rast_p4)
        sidebar_rows = [
            (1220, ["Category", "Area", "Share"]),
            (1265, ["Green Park", "255", "43.97%"]),
            (1310, ["Waste Plant", "179", "30.86%"]),
            (1355, ["Operations", "95", "16.38%"]),
            (1400, ["Buffer Zone", "51", "8.79%"]),
            (1445, ["Total", "580", "100%"]),
        ]
        for y, cols in sidebar_rows:
            p4.insert_text((1700, y), cols[0], fontsize=18)
            p4.insert_text((2040, y), cols[1], fontsize=18)
            p4.insert_text((2200, y), cols[2], fontsize=18)

        doc.save(syn_pdf)
        doc.close()

        out_dir = os.path.join(tmpdir, "out")
        res = extract_pdf(
            syn_pdf,
            out_dir,
            mode="auto",
            profile=prof["profile"],
            genomes_file=genomes_file,
            drawing_index=True,
            render_mode="overview",
        )
        assert res["tables_extracted"] >= 2, f"Expected >=2 tables, got {res}"
        with open(res["manifest_path"], "r", encoding="utf-8") as fm:
            man = json.load(fm)
        regimes_got = [p["regime"] for p in man["pages"]]
        assert regimes_got[0] == "DIGITAL_TEXT_TABLE", f"P1 regime: {regimes_got}"
        assert regimes_got[1] == "VECTOR_CAD_DRAWING", f"P2 regime: {regimes_got}"
        assert regimes_got[2] == "RASTER_DRAWING_OR_MAP", f"P3 regime: {regimes_got}"
        assert regimes_got[3] == "HYBRID_COMPOSITE_DRAWING", f"P4 regime: {regimes_got}"

        # Verify render_drawing_view modes and <= max_bytes guard
        for rmode, kw in [
            ("overview", {}),
            ("tile", {"tile": "D4"}),
            ("crop", {"bbox": [0.7, 0.7, 1.0, 1.0]}),
            ("around_text", {"query": "M-101"}),
            ("quadrants", {"tile_grid": "2x2"}),
        ]:
            rv = render_drawing_view(
                syn_pdf,
                page_num=2 if rmode != "overview" else 4,
                render_mode=rmode,
                profile=prof["profile"],
                out_path=os.path.join(tmpdir, f"rv_{rmode}"),
                **kw,
            )
            assert rv["views"], f"No views returned for {rmode}"
            for v in rv["views"]:
                assert 0 < v["byte_size"] <= 4_500_000, f"Byte guard failed: {v}"

        # Verify Stage 0 zero-hang guard on mock >10 image page
        class _MockPage:
            rect = fitz.Rect(0, 0, 2384, 1684)

            def get_images(self, full=False):
                return [(i, 0, 9933, 7017, 8) for i in range(163)]

            def get_image_info(self):
                raise AssertionError("get_image_info() MUST NOT be called when imgs > 10!")

            def get_image_rects(self, *a, **kw):
                raise AssertionError("get_image_rects() MUST NOT be called when imgs > 10!")

        m_metrics = _fast_page_image_metrics(_MockPage())
        assert m_metrics["skipped_image_info"] is True
        assert m_metrics["image_count"] == 163

        # 4. Verify v2.4.0 Seam A primitives (natural sort, bracketed grid ref, callout graph, stitching)
        assert _grid_natural_key("2.1") < _grid_natural_key("10")
        assert _grid_natural_key("Z") < _grid_natural_key("AA")
        demo_axes = {
            "x": [
                {"label": "A", "coord_pt": 100.0, "coord_norm": 0.1, "bubble_bboxes": [], "has_ray": True},
                {"label": "B", "coord_pt": 400.0, "coord_norm": 0.4, "bubble_bboxes": [], "has_ray": True},
                {"label": "C", "coord_pt": 700.0, "coord_norm": 0.7, "bubble_bboxes": [], "has_ray": True},
            ],
            "y": [
                {"label": "1", "coord_pt": 100.0, "coord_norm": 0.1, "bubble_bboxes": [], "has_ray": True},
                {"label": "2", "coord_pt": 500.0, "coord_norm": 0.5, "bubble_bboxes": [], "has_ray": True},
            ],
        }
        assert resolve_grid_ref([0.25, 0.30], demo_axes) == "A-B / 1-2"
        assert resolve_grid_ref([0.95, 0.30], demo_axes) is None
        cg = build_callout_graph(
            [
                {
                    "page": 1,
                    "primary_sheet_id": "A-101",
                    "callouts": [{"target_sheet": "S-501", "detail_no": "3", "kind": "detail"}],
                },
                {
                    "page": 2,
                    "primary_sheet_id": "S-501",
                    "callouts": [{"target_sheet": "M-999", "detail_no": None, "kind": "reference"}],
                },
            ]
        )
        assert cg["sheets"]["S-501"] == 2
        assert cg["dangling_targets"] == ["M-999"]
        st_demo = stitch_multipage_tables(
            [
                {"page": 1, "rows": [["Item", "Qty"], ["1", "10"]], "col_bounds_norm": [[0.1, 0.5], [0.5, 0.8]]},
                {"page": 2, "rows": [["Item", "Qty"], ["2", "20"]], "col_bounds_norm": [[0.1, 0.5], [0.5, 0.8]]},
            ]
        )
        assert len(st_demo["merge_events"]) == 1 and len(st_demo["stitched_tables"]) == 1

    if prof["profile"] in ("nano", "edge") and "torch" in sys.modules:
        raise AssertionError(
            f"PyTorch imported during self-test under profile={prof['profile']!r}"
        )

    return {
        "status": "self_test_passed",
        "version": __version__,
        "profile": prof["profile"],
        "torch_loaded": "torch" in sys.modules,
        "regimes_verified": list(XOCR_REGIMES),
        "tables_extracted": int(res["tables_extracted"]),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


def main():
    parser = argparse.ArgumentParser(
        description="XOCR v2.4.0 — 5-Profile PDF, CAD Drawing & Table AI Engine"
    )
    parser.add_argument(
        "input_path", nargs="?", help="Path to target PDF or image file"
    )
    parser.add_argument(
        "--input", "-i", dest="input_flag", help="Path to target PDF or image"
    )
    parser.add_argument(
        "--output", "-o", default="./ocr_output", help="Output directory"
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"xocr {__version__}",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run built-in synthetic verification suite and exit",
    )
    parser.add_argument(
        "--profile",
        choices=list(XOCR_PROFILES),
        default="auto",
        help="Hardware envelope profile (default: auto)",
    )
    parser.add_argument(
        "--genomes-file",
        dest="genomes_file",
        default=None,
        help="Optional path to calibrated xocr_genomes.json",
    )
    parser.add_argument(
        "--drawing-index",
        dest="drawing_index",
        action="store_true",
        help="Emit canonical A1..D4 spatial_index.json for PDF pages",
    )
    parser.add_argument(
        "--render-mode",
        dest="render_mode",
        choices=["overview", "crop", "around_text", "tile", "quadrants"],
        default=None,
        help="Optional multi-scale drawing view render mode",
    )
    parser.add_argument(
        "--bbox",
        default=None,
        help="Normalized crop bbox 'nx0,ny0,nx1,ny1' for --render-mode crop",
    )
    parser.add_argument(
        "--query",
        default=None,
        help="Text query for --render-mode around_text",
    )
    parser.add_argument(
        "--tile",
        default=None,
        help="Grid cell ID (e.g. B2) for --render-mode tile",
    )
    parser.add_argument(
        "--tile-grid",
        dest="tile_grid",
        default="4x4",
        help="Grid dimensions CxR (default: 4x4)",
    )
    parser.add_argument(
        "--no-grid-overlay",
        dest="no_grid_overlay",
        action="store_true",
        help="Disable translucent A1..D4 grid overlay on rendered views",
    )
    parser.add_argument(
        "--sniper-query",
        dest="sniper_query",
        default=None,
        help="Rank top-5 A1..D4 spatial ROIs for the given query in <10 ms",
    )
    parser.add_argument(
        "--xlaya-bridge",
        dest="xlaya_bridge",
        action="store_true",
        help="Enable optional xlaya BM25 lexical fusion in --sniper-query",
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "pdf", "vlm"],
        default="auto",
        help="Extraction mode: auto (default hybrid), pdf (vector), or vlm",
    )
    parser.add_argument(
        "--vlm-backend",
        dest="vlm_backend",
        choices=[
            "auto",
            "typhoon-2b",
            "typhoon-3b-qat",
            "typhoon-3b-4bit",
            "unlimited-ocr",
            "sglang",
        ],
        default="auto",
        help="VLM backend for scanned pages/images (default: auto)",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=None,
        help="Render DPI (default: 300 OCR, 150 overview)",
    )
    parser.add_argument(
        "--pages",
        default=None,
        help="Optional 1-based page range, e.g. '1-5,8,12-15'",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=min(8, os.cpu_count() or 4),
        help="Parallel worker threads for page rasterization",
    )
    parser.add_argument(
        "--langs",
        default="th,en",
        help="Comma-separated language codes for local OCR (default: th,en)",
    )
    parser.add_argument(
        "--diff-with",
        dest="diff_with",
        default=None,
        help="Compare input PDF against an older baseline PDF revision and emit drawing_diff.json",
    )
    parser.add_argument(
        "--no-stitch-tables",
        dest="no_stitch_tables",
        action="store_true",
        help="Disable 6-gate cross-page continuation table stitching",
    )
    args = parser.parse_args()

    if args.self_test:
        try:
            st_res = run_self_test(
                profile=args.profile, genomes_file=args.genomes_file
            )
            print(json.dumps(st_res, ensure_ascii=False))
            sys.exit(0)
        except Exception as exc:
            print(
                json.dumps(
                    {"status": "error", "message": str(exc)},
                    ensure_ascii=False,
                )
            )
            sys.exit(1)

    raw_input = args.input_flag or args.input_path
    if not raw_input:
        parser.error("Provide an input file path positionally or via --input")

    bbox_vals = None
    if args.bbox:
        try:
            bbox_vals = [float(x.strip()) for x in args.bbox.split(",")]
            if len(bbox_vals) != 4:
                raise ValueError("Expected 4 comma-separated floats")
        except ValueError as exc:
            parser.error(f"Invalid --bbox {args.bbox!r}: {exc}")

    input_path = os.path.abspath(raw_input)
    output_dir = os.path.abspath(args.output)
    langs = [lang.strip() for lang in args.langs.split(",") if lang.strip()]

    if not os.path.exists(input_path):
        err = {"status": "error", "message": f"Input not found: {input_path}"}
        print(json.dumps(err))
        sys.exit(1)

    diff_with_path = None
    if args.diff_with:
        diff_with_path = os.path.abspath(args.diff_with)
        if not os.path.exists(diff_with_path):
            err = {"status": "error", "message": f"Diff input not found: {diff_with_path}"}
            print(json.dumps(err, ensure_ascii=False))
            sys.exit(1)

    summary = {
        "status": "success",
        "version": __version__,
        "input": input_path,
        "output_dir": output_dir,
        "mode": args.mode,
        "profile": args.profile,
        "vlm_backend": args.vlm_backend,
    }

    try:
        if input_path.lower().endswith(".pdf"):
            pdf_res = extract_pdf(
                input_path,
                output_dir,
                mode=args.mode,
                dpi=args.dpi,
                pages_arg=args.pages,
                workers=args.workers,
                langs=langs,
                vlm_backend=args.vlm_backend,
                profile=args.profile,
                genomes_file=args.genomes_file,
                drawing_index=args.drawing_index,
                render_mode=args.render_mode,
                bbox=bbox_vals,
                query=args.query,
                tile=args.tile,
                tile_grid=args.tile_grid,
                grid_overlay=not args.no_grid_overlay,
                sniper_query=args.sniper_query,
                xlaya_bridge=args.xlaya_bridge,
                diff_with=diff_with_path,
                stitch_tables=not args.no_stitch_tables,
            )
            summary.update(pdf_res)
        else:
            img_res = extract_standalone_image(
                input_path,
                output_dir,
                langs=langs,
                vlm_backend=args.vlm_backend,
                profile=args.profile,
            )
            summary.update(img_res)
    except (ValueError, FileNotFoundError) as exc:
        err = {"status": "error", "message": str(exc)}
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
