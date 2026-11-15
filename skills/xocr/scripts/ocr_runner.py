#!/usr/bin/env python3
"""High-speed, zero-corruption PDF, CAD Drawing & Image OCR engine for /xocr (v2.2.0).

Features:
1. 5-Profile Hardware Architecture (`--profile auto|nano|edge|workstation|max`)
   with strict zero-PyTorch lazy imports under `nano` and `edge`.
2. Zero-Hang Stage 0 Image Probe (`page.get_images(full=False)`) + 4-Regime
   8D Simplex + Platt + Split-Conformal Page Classifier (`xocr_genomes.json`):
   distinguishes `DIGITAL_TEXT_TABLE`, `VECTOR_CAD_DRAWING`,
   `RASTER_DRAWING_OR_MAP`, and `HYBRID_COMPOSITE_DRAWING`.
3. Single-pass C++ PyMuPDF (`fitz`) coordinate-sorted text (`sort=True`),
   Two-Stage Grid + LaTeX `booktabs` table surgery, and Borderless
   Coordinate-Aligned Table Recovery (`_extract_aligned_block_tables`).
4. Canonical `A1..D4` Spatial CAD Callout Index (`extract_spatial_cad_index`)
   and Multi-Scale Drawing View Renderer (`render_drawing_view`) with
   Single-Composite Tile Cache for multi-layer rasters and `<= 4.5 MiB` guard.
5. Deterministic Thai/English glyph normalization (`U+F700..U+F71A` PUA,
   decomposed Sara Am, zero-width stripping) and 4-Tier VLM/CPU OCR ladder
   (`SGLang`, `Typhoon-OCR v1.5`, `Unlimited-OCR-2`, `RapidOCR`/`EasyOCR`/`pytesseract`).
"""

import argparse
from collections import OrderedDict
import contextlib
import copy
import csv
import gc
import html.parser
import importlib.util
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import warnings
from concurrent.futures import ThreadPoolExecutor

__version__ = "2.2.0"

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

DEFAULT_XOCR_GENOMES = {
    "version": "2.2.0",
    "feature_names": list(XOCR_FEATURE_NAMES),
    "regimes": list(XOCR_REGIMES),
    "alpha": 0.10,
    "conformal_q_hat": 0.4877,
    "weights": {
        "DIGITAL_TEXT_TABLE": [-0.0287, 0.0602, -0.1796, -0.1495, 0.1525, 0.07, 0.057, -0.3025],
        "VECTOR_CAD_DRAWING": [-0.1256, 0.0232, -0.2496, 0.0982, 0.1577, 0.2276, -0.1011, -0.017],
        "RASTER_DRAWING_OR_MAP": [0.1052, 0.0324, 0.2789, 0.1259, 0.178, -0.1892, 0.008, -0.0824],
        "HYBRID_COMPOSITE_DRAWING": [-0.0357, -0.1263, 0.2446, 0.1343, 0.13, -0.0273, -0.0111, -0.2907],
    },
    "platt": {
        "DIGITAL_TEXT_TABLE": {"T": 22.5, "b": 0.075},
        "VECTOR_CAD_DRAWING": {"T": 18.75, "b": -5.55},
        "RASTER_DRAWING_OR_MAP": {"T": 15.0, "b": -4.8},
        "HYBRID_COMPOSITE_DRAWING": {"T": 22.5, "b": -2.925},
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

    has_rapidocr = importlib.util.find_spec("rapidocr_onnxruntime") is not None
    has_tesseract = bool(
        importlib.util.find_spec("pytesseract") is not None
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


def _extract_text_and_dict_fast(page):
    """Extract sorted text and text-only dict in one TextPage pass when possible."""
    if page is None:
        return "", None
    if hasattr(page, "get_textpage"):
        try:
            import fitz

            txt_flags = getattr(fitz, "TEXTFLAGS_TEXT", 0)
            tp = page.get_textpage(flags=txt_flags)
            raw_txt = page.get_text("text", textpage=tp, sort=True) or ""
            pdict = page.get_text("dict", textpage=tp) or {}
            return raw_txt, pdict
        except Exception:  # nosec B110
            pass
    try:
        raw_txt = (
            page.get_text("text", sort=True) if hasattr(page, "get_text") else ""
        )
        return raw_txt or "", None
    except Exception:  # nosec B110
        return "", None


def _extract_clean_text_atoms(page, blocks=None, text_dict=None):
    """Extract normalized, deduplicated text cell/line atoms with exact bboxes."""
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
            for blk in pdict.get("blocks") or []:
                if blk.get("type", 0) != 0:
                    continue
                line_items = []
                for line in blk.get("lines") or []:
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
                        y_diff = abs(
                            0.5 * (sp[1] + sp[3]) - 0.5 * (prev[1] + prev[3])
                        )
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
                    continue

                # Merge same-baseline segments across PyMuPDF lines (e.g. PUA split spans)
                line_items.sort(key=lambda s: (round(s[1], 1), s[0]))
                baseline_merged = [line_items[0]]
                for item in line_items[1:]:
                    prev = baseline_merged[-1]
                    h = max(6.0, min(prev[3] - prev[1], item[3] - item[1]))
                    yc_diff = abs(
                        0.5 * (item[1] + item[3]) - 0.5 * (prev[1] + prev[3])
                    )
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

                # Group lines inside a single block that share an X column band
                col_groups = []
                for item in baseline_merged:
                    norm_line = re.sub(
                        r"\s+", " ", normalize_text(item[4])
                    ).strip()
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


def _append_dedup_atom(atoms, seen, x0, y0, x1, y1, text_val, size_val):
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
    atoms.append(
        {
            "x0": fx0,
            "y0": fy0,
            "x1": fx1,
            "y1": fy1,
            "text": text_val,
            "size": float(size_val),
        }
    )


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
    drawings, drawings_skipped = _probe_drawings_fast(page, img_metrics)

    vector_drawing_count = len(drawings)
    h_rules = 0
    g_rects = 0
    for drw in drawings:
        rect = drw.get("rect")
        if not rect:
            continue
        w = rect.x1 - rect.x0
        h = rect.y1 - rect.y0
        if w >= 120 and h <= 5.0:
            h_rules += 1
        elif w >= 25 and h >= 10 and drw.get("type") != "f":
            g_rects += 1

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

    needs_ocr = bool(
        qual["needs_ocr"]
        or best_regime in ("RASTER_DRAWING_OR_MAP", "HYBRID_COMPOSITE_DRAWING")
    )
    needs_vision = bool(
        best_regime
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

        cleaned = clean_table_rows(grid_rows)
        if not cleaned:
            continue

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
                "rows": cleaned,
                "nrows": nrows,
                "ncols": ncols,
                "source": "aligned_blocks",
            }
        )
    return recovered


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

    aligned_tabs = _extract_aligned_block_tables(page, blocks=blocks)
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
        out_tables.append(t_item)

    for at in aligned_tabs:
        sig = tuple(tuple(r) for r in at["rows"][:4])
        if sig in seen_sigs:
            continue
        seen_sigs.add(sig)
        nb = at["norm_bbox"]
        out_tables.append(
            {
                "bbox": at["bbox"],
                "norm_bbox": nb,
                "tile_id": _tile_id_from_norm_point(
                    0.5 * (nb[0] + nb[2]), 0.5 * (nb[1] + nb[3]), cols=cols, rows=rows
                ),
                "rows": at["rows"],
                "nrows": at["nrows"],
                "ncols": at["ncols"],
                "markdown": rows_to_markdown(at["rows"]),
                "source": "aligned_blocks",
            }
        )

    page_num = getattr(page, "number", 0) + 1
    return {
        "page": page_num,
        "page_width_pt": round(pw, 2),
        "page_height_pt": round(ph, 2),
        "tile_grid": f"{cols}x{rows}",
        "regime": regime_clean["regime"],
        "regime_info": regime_clean,
        "sheet_id_hints": sorted(sheet_ids),
        "titleblock_hints": titleblock_hints,
        "legend_hints": legend_hints,
        "tiles": tiles,
        "blocks": localized_blocks,
        "tables": out_tables,
    }


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


def clean_table_rows(raw_rows):
    """Normalize table cells, prune empty columns/rows, and validate tables."""
    if not raw_rows:
        return []
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
        return []

    ncol = max(len(r) for r in rows)
    keep_cols = [
        ci for ci in range(ncol) if any(ci < len(r) and r[ci] for r in rows)
    ]
    if len(keep_cols) < 2:
        return []

    pruned = [
        [r[ci] if ci < len(r) else "" for ci in keep_cols] for r in rows
    ]
    multi_col_rows = sum(1 for r in pruned if sum(1 for c in r if c) >= 2)
    if multi_col_rows < 2 or (multi_col_rows / len(pruned)) < 0.60:
        return []
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
        return []
    return pruned


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


def extract_tables_from_page(page, fitz_mod, raw_text="", drawings=None):
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

    # Pre-extract rows before any subsequent page.find_tables(clip=...) call,
    # which mutates PyMuPDF's internal table buffers on the same Page object.
    cached_tabs = []
    for tab in sorted(raw_tabs, key=lambda x: (x.bbox[1], x.bbox[0])):
        try:
            cached_tabs.append((list(tab.bbox), tab.extract() or []))
        except Exception:  # nosec B110
            pass

    groups = []
    for box, rows in cached_tabs:
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
        else:
            groups.append(
                {
                    "bbox": box,
                    "rows_list": [rows],
                    "last_rows": rows,
                    "reextract": False,
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
                        "reextract": True,
                    }
                )

    groups.sort(key=lambda g: (g["bbox"][1], g["bbox"][0]))

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
            candidates.append(t0_rows)
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
                    candidates.append(st.extract())
            except Exception:  # nosec B110
                pass
            if not candidates and t0_rows:
                candidates.append(t0_rows)

        for cand in candidates:
            cleaned = clean_table_rows(cand)
            if cleaned:
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
    import torch
    from PIL import Image
    from transformers import AutoModelForImageTextToText, AutoProcessor

    unload_vlm_models()
    device = _get_torch_device()
    use_4bit = bool(load_in_4bit and torch.cuda.is_available())
    load_kwargs = {
        "device_map": "auto" if device == "cuda" else device,
        "attn_implementation": "sdpa",
    }
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
    ).eval()
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


def ocr_image_local(image_path, langs=None, profile="auto"):
    """Run local offline OCR respecting profile (nano=none, edge=RapidOCR/Tesseract)."""
    prof = resolve_hardware_profile(profile)
    if prof["profile"] == "nano" or not prof["allow_local_cpu_ocr"]:
        return {"engine": "none", "text": ""}

    if langs is None:
        langs = ["th", "en"]
    lang_key = tuple(langs)

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


def _dedup_merge_page_tables(vector_tables, aligned_tables):
    """Merge vector/booktabs tables with aligned-block tables without duplicates."""
    merged = list(vector_tables)
    seen_sigs = set()
    vec_sets = []
    for rows in vector_tables:
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

    for item in aligned_tables:
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
        merged.append(rows)
    return merged


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
):
    """Single-pass C++ PyMuPDF text/table/spatial extractor with profile-gated OCR."""
    t_start = time.time()
    os.makedirs(output_dir, exist_ok=True)
    text_out_path = os.path.join(output_dir, "extracted_text.txt")
    md_out_path = os.path.join(output_dir, "extracted_document.md")
    manifest_path = os.path.join(output_dir, "ocr_manifest.json")
    spatial_index_path = os.path.join(output_dir, "spatial_index.json")
    pages_dir = os.path.join(output_dir, "_tmp_pages")

    prof = resolve_hardware_profile(profile)
    genomes = load_xocr_genomes(genomes_file)
    eff_ocr_dpi = int(dpi if dpi is not None else 300)

    import fitz

    if hasattr(fitz, "no_recommend_layout"):
        fitz.no_recommend_layout()

    doc = fitz.open(pdf_path)
    total_doc_pages = len(doc)
    selected_indices = parse_page_selection(pages_arg, total_doc_pages)

    page_records = {}
    pages_needing_ocr = []
    tables_extracted = 0
    has_fitz_tables = hasattr(fitz.Page, "find_tables")
    spatial_pages = []
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

        page_md_tables = []
        page_table_count = 0

        vector_tables = []
        if has_fitz_tables:
            vector_tables = extract_tables_from_page(
                page,
                fitz,
                raw_text=raw_text,
                drawings=regime_info.get("_drawings"),
            )
        aligned_tables = _extract_aligned_block_tables(
            page, atoms=regime_info.get("_atoms")
        )
        page_tables = _dedup_merge_page_tables(vector_tables, aligned_tables)

        for rows in page_tables:
            page_table_count += 1
            tables_extracted += 1
            csv_name = f"table_p{page_num}_{page_table_count}.csv"
            csv_path = os.path.join(output_dir, csv_name)
            with open(
                csv_path, "w", encoding="utf-8-sig", newline=""
            ) as f_csv:
                writer = csv.writer(f_csv)
                writer.writerows(rows)
            page_md_tables.append(rows_to_markdown(rows))

        page_needs_ocr = bool(qual["needs_ocr"] or regime_info["needs_ocr"])
        if mode == "vlm" or (mode == "auto" and page_needs_ocr):
            pages_needing_ocr.append(page_idx)

        if drawing_index:
            aligned_sigs = {tuple(tuple(r) for r in at["rows"][:4]) for at in aligned_tables}
            merged_spatial_tables = list(aligned_tables)
            for vt in vector_tables:
                if tuple(tuple(r) for r in vt[:4]) not in aligned_sigs:
                    merged_spatial_tables.append({"rows": vt, "source": "vector_grid"})
            s_idx = extract_spatial_cad_index(
                page,
                tile_grid=tile_grid,
                tables=merged_spatial_tables,
                regime_info=regime_info,
            )
            spatial_pages.append(s_idx)

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

        page_records[page_idx] = {
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
            "stage0_ms": stage0_ms,
            "table_count": page_table_count,
            "md_tables": page_md_tables,
            "engine": "pymupdf_vector",
        }

    doc.close()

    if not has_fitz_tables:
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                for page_idx in selected_indices:
                    page_num = page_idx + 1
                    raw_tabs = pdf.pages[page_idx].extract_tables() or []
                    for raw_tab in raw_tabs:
                        rows = clean_table_rows(raw_tab)
                        if not rows:
                            continue
                        page_records[page_idx]["table_count"] += 1
                        tables_extracted += 1
                        t_idx = page_records[page_idx]["table_count"]
                        csv_name = f"table_p{page_num}_{t_idx}.csv"
                        csv_path = os.path.join(output_dir, csv_name)
                        with open(
                            csv_path, "w", encoding="utf-8-sig", newline=""
                        ) as f_csv:
                            writer = csv.writer(f_csv)
                            writer.writerows(rows)
                        page_records[page_idx]["md_tables"].append(
                            rows_to_markdown(rows)
                        )
        except ImportError:
            pass

    image_paths = []
    vlm_info = None
    can_run_ocr = prof["allow_vlm"] or (
        prof["allow_local_cpu_ocr"] and prof["has_cpu_ocr"]
    )
    if pages_needing_ocr and mode in ("auto", "vlm") and can_run_ocr:
        os.makedirs(pages_dir, exist_ok=True)
        render_items = [
            (
                p_idx,
                os.path.join(pages_dir, f"page_{p_idx + 1:03d}.png"),
            )
            for p_idx in pages_needing_ocr
        ]
        max_w = max(1, min(int(workers), len(render_items)))
        batches = [
            (pdf_path, eff_ocr_dpi, render_items[i::max_w])
            for i in range(max_w)
            if render_items[i::max_w]
        ]
        rendered_map = {}
        if len(batches) > 1:
            with ThreadPoolExecutor(max_workers=len(batches)) as pool:
                for batch_res in pool.map(_render_page_batch, batches):
                    for p_idx, out_png in batch_res:
                        rendered_map[p_idx] = out_png
        else:
            for p_idx, out_png in _render_page_batch(batches[0]):
                rendered_map[p_idx] = out_png
        image_paths = [rendered_map[p_idx] for p_idx in pages_needing_ocr]

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
            for p_idx, img_path in zip(pages_needing_ocr, image_paths):
                v_txt = vlm_map.get(img_path, "")
                if v_txt:
                    rec = page_records[p_idx]
                    if rec["regime"] == "HYBRID_COMPOSITE_DRAWING" and rec["char_count"] >= 100:
                        rec["text"] = f"{rec['text']}\n\n### Visual / Raster Zone OCR\n{v_txt}"
                        rec["engine"] = f"pymupdf_vector+{vlm_eng}"
                    else:
                        rec["text"] = v_txt
                        rec["engine"] = vlm_eng
                    rec["char_count"] = non_ws_count(rec["text"])
                    if rec["table_count"] == 0:
                        html_tabs = extract_html_tables_from_text(v_txt)
                        page_num = p_idx + 1
                        for rows in html_tabs:
                            rec["table_count"] += 1
                            tables_extracted += 1
                            t_idx = rec["table_count"]
                            csv_name = f"table_p{page_num}_{t_idx}.csv"
                            csv_path = os.path.join(output_dir, csv_name)
                            with open(
                                csv_path, "w", encoding="utf-8-sig", newline=""
                            ) as f_csv:
                                writer = csv.writer(f_csv)
                                writer.writerows(rows)
                            rec["md_tables"].append(rows_to_markdown(rows))
        else:
            for p_idx, img_path in zip(pages_needing_ocr, image_paths):
                ocr_res = ocr_image_local(
                    img_path, langs=langs, profile=prof["profile"]
                )
                ocr_nws = non_ws_count(ocr_res["text"])
                rec = page_records[p_idx]
                if ocr_res["text"] and (
                    ocr_nws > rec["char_count"]
                    or rec["garble_ratio"] > 0.05
                    or rec["regime"] == "HYBRID_COMPOSITE_DRAWING"
                ):
                    if rec["regime"] == "HYBRID_COMPOSITE_DRAWING" and rec["char_count"] >= 100:
                        rec["text"] = f"{rec['text']}\n\n### Visual / Raster Zone OCR\n{ocr_res['text']}"
                        rec["engine"] = f"pymupdf_vector+{ocr_res['engine']}"
                    else:
                        rec["text"] = ocr_res["text"]
                        rec["engine"] = ocr_res["engine"]
                    rec["char_count"] = non_ws_count(rec["text"])

    if drawing_index:
        with open(spatial_index_path, "w", encoding="utf-8") as f_idx:
            json.dump(
                {
                    "version": __version__,
                    "input": pdf_path,
                    "profile": prof["profile"],
                    "tile_grid": tile_grid,
                    "pages": spatial_pages,
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
            for t_i, md_tab in enumerate(rec["md_tables"], start=1):
                md_sec.append(f"\n#### Table {p_num}.{t_i}\n\n{md_tab}")
        md_chunks.append("\n".join(md_sec))

        manifest_pages.append(
            {
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
                "stage0_ms": rec["stage0_ms"],
                "engine": rec["engine"],
            }
        )

    with open(text_out_path, "w", encoding="utf-8") as f_txt:
        f_txt.write("\n".join(txt_chunks))

    with open(md_out_path, "w", encoding="utf-8") as f_md:
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
        "low_text_or_ocr_pages": [p + 1 for p in pages_needing_ocr],
        "elapsed_ms": elapsed_ms,
        "pages": manifest_pages,
    }
    if drawing_index:
        manifest_data["spatial_index_path"] = spatial_index_path
    if rendered_views_all:
        manifest_data["rendered_views"] = rendered_views_all

    with open(manifest_path, "w", encoding="utf-8") as f_man:
        json.dump(manifest_data, f_man, indent=2, ensure_ascii=False)

    res = {
        "version": __version__,
        "profile": prof["profile"],
        "pages_processed": len(selected_indices),
        "total_chars": total_chars,
        "tables_extracted": tables_extracted,
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
        ocr_res = ocr_image_local(image_path, langs=langs, profile=prof["profile"])
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
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


def main():
    parser = argparse.ArgumentParser(
        description="XOCR v2.2.0 — 5-Profile PDF, CAD Drawing & Table AI Engine"
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
    except ValueError as exc:
        err = {"status": "error", "message": str(exc)}
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
