#!/usr/bin/env python3
"""
laya_triage.py — 3-Stage System 1 → System 1.5 Semantic Triage, Adaptive Hardware Profile & Code-Graph Sieve Engine
Part of the XBoost Agent Skill Framework (/xlaya v2.3.0).

Architecture:
- Stage 0 (Deterministic Chunker + Cross-Regime AST Code-Graph & Evolved Matrix Sieve):
  • 4-backtick/tilde fence-safe Markdown parser with 6-level #{1,6} breadcrumb stack
  • O(L) Python AST enclosing def/async def/class chunker, skeleton headers, & 2-Tier source-first pre-ranker
  • Universal pure-stdlib Corpus-IDF seed propagation (f_5_tfidf) + whitened .npz & isolated NetworkX sidecars
  • Smooth realized channel availability renormalization (M_avail, gamma_max=1.45) + 2-Stage When2Call tool gate
  • Evolved 8-feature simplex sieve (sieve_code_graph + sieve_genomes.json) for E4B-Sniper & 31B-Deep budgets
- Stage 1 (ModernBERT Multi-Encoder Jury — english + typed-decisions + mmBERT):
  • Thread-safe resident model cache (_MODEL_CACHE) + offline-first local HF snapshot resolution
  • Support for 'en', 'multi', 'typed' (subfolder='typed-decisions'), and 'ensemble' (0.45*en + 0.55*typed)
  • Per-item inter-model disagreement & model_agreement telemetry for automatic Stage 2 escalation
  • 4-facet decomposed rubric scoring (specificity, completeness, consistency, actionability) + file summaries
- Stage 2 (VegaML Conformal System 1.5 Escalation & Persistent TTT Calibration):
  • Adaptive hardware profiles (--profile auto|nano|edge|workstation|max + --agent-tier auto|e4b-sniper|31b-deep)
  • Multi-view test-time surface debiasing (views=1|2|3 reversing option order & prose templates -> view_agreement)
  • Persistent TTTHead + split-conformal policy training (fit_policy / load_calibration / outbound OOD guard)
  • Local multimodal inference (image, audio, video) through VegaAgent
"""

from __future__ import annotations

import argparse
import ast
import contextlib
import csv
import ctypes
import fnmatch
import gc
import html
import importlib.metadata
import importlib.util
import io
import json
import math
import os
import re
import sys
import tempfile
import threading
import time
import warnings
import zlib
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

__version__ = "2.3.0"

sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
if os.name == "nt":
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

HEADING_RE = re.compile(r"^ {0,3}(#{1,6})\s+(.+?)\s*$")
FENCE_OPEN_RE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HTML_HEADING_RE = re.compile(r"<h([1-6])\b[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
HTML_NOISE_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]+>")

THAI_RUN_RE = re.compile(r"[\u0E00-\u0E7F]+")
CJK_RUN_RE = re.compile(r"[\u3040-\u30FF\u4E00-\u9FFF]+")
NON_ENGLISH_SCRIPT_RE = re.compile(
    r"[\u0E00-\u0E7F\u3040-\u30FF\u3400-\u9FFF\uAC00-\uD7AF\u0600-\u06FF\u0400-\u04FF\u0900-\u097F]"
)
LATIN_TOKEN_RE = re.compile(r"[a-z0-9]+")
BACKTICK_SPAN_RE = re.compile(r"`([^`\n]{2,80})`")
CLI_FLAG_RE = re.compile(r"(?:^|(?<=\s))(--[a-zA-Z0-9][a-zA-Z0-9_-]*)")
IDENT_RE = re.compile(
    r"\b(?:[a-zA-Z0-9]+_[a-zA-Z0-9_]+|[a-z]+(?:[A-Z][a-z0-9]+)+|"
    r"[A-Z][a-z0-9]+(?:[A-Z][a-z0-9]+)+|v?\d+\.\d+(?:\.\d+)?|"
    r"[A-Za-z]+-[A-Za-z0-9.-]+)\b"
)
NUMBER_TOKEN_RE = re.compile(r"\b\d+(?:\.\d+)?\b")
LINE_INDEX_PREFIX_RE = re.compile(r"^\s*\d+\.\s+")

STOPWORDS = frozenset(
    {
        "the", "and", "for", "that", "this", "with", "from", "are", "was", "were",
        "have", "has", "had", "not", "but", "what", "which", "when", "where", "who",
        "how", "why", "can", "will", "into", "about", "than", "then", "them", "they",
        "their", "there", "here", "does", "did", "its", "any", "all", "only", "also",
    }
)

EXCLUDED_DIRS = frozenset(
    {
        ".git", "node_modules", ".venv", "venv", "env", "dist", "build",
        "__pycache__", ".obsidian", ".pytest_cache", ".mypy_cache", ".ruff_cache",
        ".tox", ".nox", ".eggs", "site-packages",
    }
)

DEFAULT_PATTERN = "*.md,*.html,*.txt,*.json,*.jsonl,*.csv"
CODE_PATTERN = "*.md,*.html,*.txt,*.json,*.jsonl,*.csv,*.py,*.pyi,*.toml,*.yaml,*.yml"
XLAYA_PROFILES = ("auto", "nano", "edge", "workstation", "max")
XLAYA_AGENT_TIERS = ("auto", "e4b-sniper", "31b-deep")
SIEVE_FEATURE_NAMES = (
    "bm25",
    "ident_exact",
    "ast_enclosing_def",
    "call_graph_hop1",
    "async_depends_hop2",
    "emb_256d_cos",
    "test_file_penalty",
    "traceback_line_boost",
)
SIEVE_NEG_INDICES = frozenset({6})  # test_file_penalty is non-positive on the L1 simplex

DEFAULT_SIEVE_GENOMES: Dict[str, Any] = {
    "schema_version": "2.3.0",
    "feature_names": list(SIEVE_FEATURE_NAMES),
    "gamma_max": 1.45,
    "e4b_sniper_p1": {
        "w_core": [0.17836, 0.228133, 0.08187, 0.166449, 0.065469, 0.053293, -0.151443, 0.074983],
        "w_halo": [0.17836, 0.228133, 0.08187, 0.166449, 0.065469, 0.053293, -0.151443, 0.074983],
        "lambda_file_div": 0.35,
        "platt_T": 1.67,
        "platt_b": -0.795,
        "conformal_q_hat": 0.5885,
        "token_budget": 800,
        "top_k": 3,
    },
    "e4b_sniper_distilled": {
        "w_core": [0.167068, 0.296999, 0.045851, 0.155435, 0.067317, 0.062147, -0.151591, 0.053592],
        "w_halo": [0.167068, 0.296999, 0.045851, 0.155435, 0.067317, 0.062147, -0.151591, 0.053592],
        "lambda_file_div": 0.35,
        "platt_T": 1.67,
        "platt_b": -0.795,
        "conformal_q_hat": 0.5885,
        "token_budget": 800,
        "top_k": 3,
    },
    "31b_deep": {
        "w_core": [0.167068, 0.296999, 0.045851, 0.155435, 0.067317, 0.062147, -0.151591, 0.053592],
        "w_halo": [0.098415, 0.159503, 0.185096, 0.128404, 0.01622, 0.18358, -0.178304, 0.050476],
        "anchor_slots": 3,
        "lambda_file_div": 0.16,
        "platt_T": 1.67,
        "platt_b": -0.795,
        "conformal_q_hat": 0.5885,
        "token_budget": 4096,
        "top_k": 8,
    },
    "tool_gate": {
        "schema": "factorized_2stage_v23",
        "tau_tool_call": 0.345,
        "temp_rel": 1.3239,
        "temp_slot": 0.75,
        "rel_w1": [
            [0.34198, 0.37987, 0.9929, 0.08553, 0.02598, 0.04005, 0.02253],
            [0.23083, 0.26423, 1.30163, 0.14012, 0.01714, 0.05001, 0.02236],
            [0.23029, 0.34235, 1.25417, 0.13582, 0.02046, 0.05734, 0.01996],
            [0.25638, 0.35981, 1.24085, 0.17128, 0.02972, 0.05399, 0.02714],
            [0.30637, 0.32293, 0.88903, 0.18943, 0.01902, 0.0523, 0.02572],
            [0.40419, 0.3075, 0.749, 0.15349, 0.02026, 0.04659, 0.02016],
            [0.34479, 0.31181, 0.92635, 0.14946, 0.02925, 0.04881, 0.01893],
            [0.31611, 0.2522, 0.97719, 0.19655, 0.02646, 0.05299, 0.02211],
        ],
        "rel_b1": [-0.50511, -0.46209, -0.47055, -0.42028, -0.48737, -0.5569, -0.46662, -0.46446],
        "rel_w2": [0.93938, 1.09745, 0.94605, 0.93955, 1.03502, 0.92325, 0.75509, 0.9352],
        "rel_b2": -0.46756,
        "slot_w1": [
            [2.31203, 0.16985, -0.14598, -0.16849, -0.50253, -0.10321, 0.19972, 0.61083, 0.20748, -0.21331, -1.29212],
            [2.27175, 0.21759, -0.07601, -0.08156, -0.25666, -0.07834, 0.30082, 0.72833, 0.18577, -0.08771, -1.04199],
            [0.97987, 0.08668, -0.03106, -0.02007, -0.04297, -0.48435, 5.352, 0.42469, 0.84874, -0.01858, -0.60401],
            [2.13322, 0.17683, -0.06814, -0.05952, -0.21174, -0.06085, 0.36346, 0.65339, 0.23195, -0.05766, -0.81323],
            [1.55528, 0.08354, -0.03804, -0.01651, -0.07002, -0.06679, 1.50322, 0.26005, 0.45668, -0.01495, -0.54949],
            [2.08538, 0.13845, -0.04093, -0.01998, -0.14983, -0.03999, 0.98921, 0.47423, 0.29548, -0.03289, -0.50002],
            [1.97388, 0.14195, -0.0403, -0.02331, -0.16564, -0.04718, 0.64221, 0.74331, 0.20343, -0.03471, -0.49288],
            [2.06836, 0.13131, -0.06637, -0.05002, -0.19182, -0.04897, 0.3022, 0.78903, 0.19947, -0.07609, -0.93425],
        ],
        "slot_b1": [-1.32144, -1.53527, -0.39146, -1.46922, -1.11846, -1.1449, -1.31111, -1.3259],
        "slot_w2": [0.28035, 0.32349, 1.05236, 0.41561, 0.41898, 0.41078, 0.39769, 0.29727],
        "slot_b2": -0.25657,
    },
}

DEFAULT_LABELS_SPEC = (
    "architecture:Architecture & specs|cli:CLI scripts & commands|docs:General prose & guides"
)

DEFAULT_RUBRIC_CRITERIA = [
    "Single-sentence stub lacking concrete versions, CLI commands, or architectural details",
    "Brief overview with minimal technical specificity",
    "Moderate specification covering partial workflow or schema details",
    "Detailed specification with concrete architecture, parameters, and rules",
    "Exhaustive production specification with exact versions, CLI engines, and locked invariants",
]

DEFAULT_RELEVANCE_CRITERIA = [
    "Unrelated to the target query or topic",
    "Tangentially mentions a keyword without substantive detail",
    "Moderately relevant background context",
    "Directly relevant section addressing key aspects of the query",
    "Primary authoritative specification directly answering the target query",
]

VALID_MODES = frozenset({"rubric", "contradiction", "shortlist", "classify"})
VALID_VEGA_MODELS = frozenset({"auto", "none", "0.8b", "08b", "4b", "gemma-1b", "27b"})

FACET_WEIGHTS: Dict[str, float] = {
    "specificity": 0.30,
    "completeness": 0.30,
    "consistency": 0.20,
    "actionability": 0.20,
}

RUBRIC_PRESETS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "default": {
        "specificity": {
            "instructions": "Rate the technical specificity, concrete parameters, versions, and exact identifiers.",
            "criteria": [
                "Vague prose with no concrete identifiers, parameters, or versions",
                "Mentions general concepts with minimal technical specifics",
                "Includes partial parameters, commands, or module references",
                "Detailed technical specification with concrete parameters and versions",
                "Exhaustive specification with exact signatures, constants, and CLI parameters",
            ],
        },
        "completeness": {
            "instructions": "Rate the structural completeness, boundary coverage, and edge-case handling.",
            "criteria": [
                "Incomplete fragment or stub missing core workflow steps",
                "Covers only basic happy path without boundaries or edge cases",
                "Covers primary workflow with partial boundary conditions",
                "Comprehensive coverage of workflow, boundaries, and fallback rules",
                "Complete end-to-end specification covering all branches, edge cases, and invariants",
            ],
        },
        "consistency": {
            "instructions": "Rate the internal coherence, invariant clarity, and absence of ambiguous claims.",
            "criteria": [
                "Internally contradictory or severely ambiguous statements",
                "Contains loosely defined terms or potential terminology drift",
                "Generally coherent with minor unstated assumptions",
                "Internally consistent with explicit constraints and definitions",
                "Strictly coherent with locked mathematical or architectural invariants",
            ],
        },
        "actionability": {
            "instructions": "Rate the execution and verification readiness with concrete, falsifiable checks.",
            "criteria": [
                "Purely aspirational with no actionable steps or verification criteria",
                "High-level guidance requiring substantial interpretation to execute",
                "Moderately actionable with basic usage examples",
                "Directly actionable with clear execution steps and expected outputs",
                "Immediately executable and verifiable with exact Red-to-Green probes and receipts",
            ],
        },
    },
    "architecture": {
        "specificity": {
            "instructions": "Rate how clearly module boundaries, interfaces, and seam signatures are specified.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
        "completeness": {
            "instructions": "Rate coverage of data flow, resource lifecycle, and failure recovery boundaries.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
        "consistency": {
            "instructions": "Rate adherence to deep-module invariants and single-source-of-truth contracts.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
        "actionability": {
            "instructions": "Rate readiness for surgical implementation and end-to-end integration testing.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
    },
    "code_audit": {
        "specificity": {
            "instructions": "Rate the precision of type contracts, numerical bounds, and error handling.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
        "completeness": {
            "instructions": "Rate coverage of boundary inputs, null/empty guards, and peer branches.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
        "consistency": {
            "instructions": "Rate conservation laws, causal ordering, and absence of silent fallbacks.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
        "actionability": {
            "instructions": "Rate testability and presence of deterministic runtime verification probes.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
    },
    "doc_sync": {
        "specificity": {
            "instructions": "Rate accuracy of version numbers, CLI flags, file links, and schema tables.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
        "completeness": {
            "instructions": "Rate completeness of feature documentation across all supported modes and tools.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
        "consistency": {
            "instructions": "Rate alignment with canonical SSOT metrics and absence of stale legacy references.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
        "actionability": {
            "instructions": "Rate clarity of copy-paste CLI commands and quick-start examples.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
    },
    "research": {
        "specificity": {
            "instructions": "Rate primary-source citation depth, exact benchmark numbers, and dataset sizes.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
        "completeness": {
            "instructions": "Rate coverage of competing baselines, trade-offs, and hardware constraints.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
        "consistency": {
            "instructions": "Rate methodological rigor, calibration metrics (ECE/AURC), and fair comparisons.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
        "actionability": {
            "instructions": "Rate how directly the findings translate into concrete engineering decisions.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        },
    },
}
VALID_RUBRIC_PRESETS = frozenset(RUBRIC_PRESETS.keys())

_CACHE_LOCK = threading.RLock()
_MODEL_CACHE: Dict[str, Tuple[Any, str]] = {}


# ---------------------------------------------------------------------------
# Runtime Environment, Device & Model Cache Management
# ---------------------------------------------------------------------------


def _pkg_version(dist_name: str, module_name: Optional[str] = None) -> Tuple[bool, Optional[str]]:
    mod = module_name or dist_name
    spec = importlib.util.find_spec(mod)
    if spec is None:
        return False, None
    try:
        return True, importlib.metadata.version(dist_name)
    except importlib.metadata.PackageNotFoundError:
        return True, "unknown"


def _recommended_cpu_threads() -> int:
    env_val = os.environ.get("LAYA_THREADS", "").strip()
    if env_val.isdigit() and int(env_val) >= 1:
        return int(env_val)
    return max(1, min(10, (os.cpu_count() or 2) // 2))


def _configure_cpu_threads(torch_mod: Any) -> int:
    target = _recommended_cpu_threads()
    try:
        if torch_mod.get_num_threads() != target:
            torch_mod.set_num_threads(target)
    except RuntimeError as exc:
        print(f"[XLaya] Warning: could not set torch CPU threads: {exc}", file=sys.stderr)
    return int(torch_mod.get_num_threads())


def _host_ram_gb() -> float:
    """Estimate total host system RAM in GiB using stdlib without third-party imports."""
    if os.name == "nt":
        try:
            class _MemStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = _MemStatusEx()
            stat.dwLength = ctypes.sizeof(_MemStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):  # type: ignore[attr-defined]
                return round(stat.ullTotalPhys / (1024 ** 3), 2)
        except Exception:  # nosec B110
            pass
    else:
        try:
            meminfo = Path("/proc/meminfo")
            if meminfo.is_file():
                for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if line.startswith("MemTotal:"):
                        kb = int(line.split()[1])
                        return round(kb / (1024 ** 2), 2)
            if hasattr(os, "sysconf"):
                pages = os.sysconf("SC_PHYS_PAGES")
                page_size = os.sysconf("SC_PAGE_SIZE")
                if pages > 0 and page_size > 0:
                    return round((pages * page_size) / (1024 ** 3), 2)
        except Exception:  # nosec B110
            pass
    return 8.0


def _resolve_device(device: str = "auto") -> str:
    req = (device or "auto").strip().lower()
    if req == "cpu" or os.environ.get("XLAYA_PROFILE", "").strip().lower() == "nano":
        return "cpu"
    try:
        import torch  # type: ignore
    except ImportError:
        return "cpu"

    mps_ok = bool(hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
    if req in ("", "auto"):
        resolved = "cuda" if torch.cuda.is_available() else ("mps" if mps_ok else "cpu")
    elif req.startswith("cuda") and not torch.cuda.is_available():
        print("[XLaya] Warning: CUDA requested but unavailable; falling back to CPU.", file=sys.stderr)
        resolved = "cpu"
    elif req == "mps" and not mps_ok:
        print("[XLaya] Warning: MPS requested but unavailable; falling back to CPU.", file=sys.stderr)
        resolved = "cpu"
    else:
        resolved = req

    if resolved == "cpu":
        _configure_cpu_threads(torch)
    return resolved


def _resolve_hardware_profile(
    profile: str = "auto",
    agent_tier: str = "auto",
    device: str = "auto",
) -> Dict[str, Any]:
    """Resolve adaptive hardware envelope (--profile) and agent token/slot tier (--agent-tier)."""
    raw_prof = (profile or "").strip().lower()
    if not raw_prof or raw_prof == "auto":
        env_prof = os.environ.get("XLAYA_PROFILE", "").strip().lower()
        eff_prof = env_prof if env_prof else "auto"
    else:
        eff_prof = raw_prof

    if eff_prof not in XLAYA_PROFILES:
        raise ValueError(
            f"Unsupported profile {profile!r}; expected one of {list(XLAYA_PROFILES)}."
        )

    raw_tier = (agent_tier or "").strip().lower()
    if not raw_tier or raw_tier == "auto":
        env_tier = os.environ.get("XLAYA_AGENT_TIER", "").strip().lower()
        eff_tier = env_tier if env_tier else "auto"
    else:
        eff_tier = raw_tier

    if eff_tier not in XLAYA_AGENT_TIERS:
        raise ValueError(
            f"Unsupported agent_tier {agent_tier!r}; expected one of {list(XLAYA_AGENT_TIERS)}."
        )

    profile_explicit = eff_prof != "auto"
    tier_explicit = eff_tier != "auto"

    # Strict zero-torch fast path for 'nano' (guarantees 'torch' not in sys.modules)
    if eff_prof == "nano":
        res_tier = "e4b-sniper" if eff_tier == "auto" else eff_tier
        return {
            "profile": "nano",
            "profile_explicit": True,
            "agent_tier": res_tier,
            "agent_tier_explicit": tier_explicit,
            "device": "cpu",
            "stage0_only": True,
            "single_encoder_only": False,
            "vega_allowed": False,
            "recommended_vega_model": "none",
            "rss_budget_mb": 25,
            "latency_budget_ms": 200,
            "token_budget": 800 if res_tier == "e4b-sniper" else 4096,
            "default_top_k": 3 if res_tier == "e4b-sniper" else 8,
            "batch_size_cap": 16,
            "cuda_device_count": 0,
            "vram_single_gb": 0.0,
            "vram_cluster_gb": 0.0,
            "host_ram_gb": _host_ram_gb(),
        }

    ram_gb = _host_ram_gb()
    laya_ok, _ = _pkg_version("laya", "laya")
    cuda_count = 0
    vram_single_gb = 0.0
    vram_cluster_gb = 0.0
    resolved_dev = "cpu"

    if eff_prof == "edge" and (device or "auto").strip().lower() in ("", "auto", "cpu"):
        resolved_dev = "cpu"
    elif laya_ok or importlib.util.find_spec("torch") is not None:
        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                cuda_count = int(torch.cuda.device_count())
                per_dev_gb: List[float] = []
                for dev_idx in range(cuda_count):
                    props = torch.cuda.get_device_properties(dev_idx)
                    per_dev_gb.append(float(props.total_memory) / (1024 ** 3))
                vram_single_gb = round(per_dev_gb[0], 2) if per_dev_gb else 0.0
                vram_cluster_gb = round(sum(per_dev_gb), 2)
            resolved_dev = _resolve_device(device)
        except Exception:  # nosec B110
            resolved_dev = "cpu"

    if eff_prof == "auto":
        if not laya_ok:
            res_prof = "nano"
        elif resolved_dev.startswith("cuda") and (vram_cluster_gb >= 48.0 or vram_single_gb >= 22.0):
            res_prof = "max"
        elif resolved_dev.startswith("cuda") and vram_single_gb >= 8.0:
            res_prof = "workstation"
        elif ram_gb <= 3.0 and not resolved_dev.startswith("cuda"):
            res_prof = "nano"
        else:
            res_prof = "edge"
    else:
        res_prof = eff_prof

    if res_prof == "nano":
        res_tier = "e4b-sniper" if eff_tier == "auto" else eff_tier
        return {
            "profile": "nano",
            "profile_explicit": profile_explicit,
            "agent_tier": res_tier,
            "agent_tier_explicit": tier_explicit,
            "device": "cpu",
            "stage0_only": True,
            "single_encoder_only": False,
            "vega_allowed": False,
            "recommended_vega_model": "none",
            "rss_budget_mb": 25,
            "latency_budget_ms": 200,
            "token_budget": 800 if res_tier == "e4b-sniper" else 4096,
            "default_top_k": 3 if res_tier == "e4b-sniper" else 8,
            "batch_size_cap": 16,
            "cuda_device_count": cuda_count,
            "vram_single_gb": vram_single_gb,
            "vram_cluster_gb": vram_cluster_gb,
            "host_ram_gb": ram_gb,
        }

    if res_prof == "edge":
        res_tier = "e4b-sniper" if eff_tier == "auto" else eff_tier
        edge_dev = "cpu" if (device or "auto").strip().lower() in ("", "auto") else resolved_dev
        return {
            "profile": "edge",
            "profile_explicit": profile_explicit,
            "agent_tier": res_tier,
            "agent_tier_explicit": tier_explicit,
            "device": edge_dev,
            "stage0_only": False,
            "single_encoder_only": True,
            "vega_allowed": False,
            "recommended_vega_model": "none",
            "rss_budget_mb": 350,
            "latency_budget_ms": 1500,
            "token_budget": 800 if res_tier == "e4b-sniper" else 4096,
            "default_top_k": 3 if res_tier == "e4b-sniper" else 8,
            "batch_size_cap": 16,
            "cuda_device_count": cuda_count,
            "vram_single_gb": vram_single_gb,
            "vram_cluster_gb": vram_cluster_gb,
            "host_ram_gb": ram_gb,
        }

    if res_prof == "max":
        res_tier = "31b-deep" if eff_tier == "auto" else eff_tier
        return {
            "profile": "max",
            "profile_explicit": profile_explicit,
            "agent_tier": res_tier,
            "agent_tier_explicit": tier_explicit,
            "device": resolved_dev,
            "stage0_only": False,
            "single_encoder_only": False,
            "vega_allowed": True,
            "recommended_vega_model": _resolve_vega_model("auto", resolved_dev),
            "rss_budget_mb": 16384,
            "latency_budget_ms": 5000,
            "token_budget": 800 if res_tier == "e4b-sniper" else 4096,
            "default_top_k": 3 if res_tier == "e4b-sniper" else 8,
            "batch_size_cap": 64,
            "cuda_device_count": cuda_count,
            "vram_single_gb": vram_single_gb,
            "vram_cluster_gb": vram_cluster_gb,
            "host_ram_gb": ram_gb,
        }

    res_tier = "31b-deep" if eff_tier == "auto" else eff_tier
    return {
        "profile": "workstation",
        "profile_explicit": profile_explicit,
        "agent_tier": res_tier,
        "agent_tier_explicit": tier_explicit,
        "device": resolved_dev,
        "stage0_only": False,
        "single_encoder_only": False,
        "vega_allowed": True,
        "recommended_vega_model": _resolve_vega_model("auto", resolved_dev),
        "rss_budget_mb": 4096,
        "latency_budget_ms": 3000,
        "token_budget": 800 if res_tier == "e4b-sniper" else 4096,
        "default_top_k": 3 if res_tier == "e4b-sniper" else 8,
        "batch_size_cap": 32,
        "cuda_device_count": cuda_count,
        "vram_single_gb": vram_single_gb,
        "vram_cluster_gb": vram_cluster_gb,
        "host_ram_gb": ram_gb,
    }


def _normalize_model_key(name: str) -> str:
    raw = name.strip().lower()
    if raw in ("en", "english"):
        return "english"
    if raw in ("multi", "multilingual", "ml"):
        return "multilingual"
    if raw in ("typed", "typed-decisions", "typed_decisions"):
        return "typed-decisions"
    if raw == "ensemble":
        return "ensemble"
    if raw.startswith("vega:"):
        return raw
    raise ValueError(
        f"Unsupported model key {name!r}; expected 'en', 'english', 'multi', "
        "'multilingual', 'typed', 'typed-decisions', or 'ensemble'."
    )


def _has_valid_laya_checkpoint(snap_dir: str, subfolder: Optional[str]) -> bool:
    base = Path(snap_dir) / subfolder if subfolder else Path(snap_dir)
    return (base / "rl_agent_config.json").is_file() and (base / "model.safetensors").is_file()


def _resolve_local_laya_snapshot(subfolder: Optional[str]) -> Optional[str]:
    prefix = f"{subfolder}/" if subfolder else ""
    hf_cache = os.environ.get("HF_HUB_CACHE") or os.path.join(
        os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface"),
        "hub",
    )
    repo_dir = Path(hf_cache) / "models--convaiinnovations--laya"
    snaps_dir = repo_dir / "snapshots"

    if snaps_dir.is_dir():
        ref_main = repo_dir / "refs" / "main"
        if ref_main.is_file():
            try:
                rev = ref_main.read_text(encoding="utf-8").strip()
                cand = snaps_dir / rev
                if cand.is_dir() and _has_valid_laya_checkpoint(str(cand), subfolder):
                    return str(cand)
            except OSError as exc:
                print(f"[XLaya] Warning: could not read HF refs/main: {exc}", file=sys.stderr)

        try:
            candidates = sorted(
                (p for p in snaps_dir.iterdir() if p.is_dir()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            for cand in candidates:
                if _has_valid_laya_checkpoint(str(cand), subfolder):
                    return str(cand)
        except OSError as exc:
            print(f"[XLaya] Warning: could not scan HF snapshots: {exc}", file=sys.stderr)

    try:
        from huggingface_hub import snapshot_download  # type: ignore

        allow = [prefix + p for p in ("rl_agent_config.json", "model.safetensors", "tokenizer/*", "encoder/*")]
        snap_dir = snapshot_download(
            "convaiinnovations/laya",
            local_files_only=True,
            allow_patterns=allow,
        )
        if snap_dir and _has_valid_laya_checkpoint(snap_dir, subfolder):
            return snap_dir
    except Exception:  # nosec B110 - offline snapshot miss falls back cleanly to laya.load
        return None
    return None


def _load_laya_checkpoint(canon_key: str, resolved_device: str, cache: bool = True) -> Any:
    import laya  # type: ignore

    with _CACHE_LOCK:
        cached = _MODEL_CACHE.get(canon_key)
        if cached is not None and cached[1] == resolved_device:
            return cached[0]

        subfolder_map: Dict[str, Optional[str]] = {
            "english": None,
            "multilingual": "multilingual",
            "typed-decisions": "typed-decisions",
        }
        if canon_key not in subfolder_map:
            raise ValueError(f"Unsupported Stage 1 checkpoint key: {canon_key!r}")
        subfolder = subfolder_map[canon_key]
        local_snap = _resolve_local_laya_snapshot(subfolder)
        target_id = local_snap if local_snap is not None else "convaiinnovations/laya"

        with warnings.catch_warnings(), contextlib.redirect_stdout(sys.stderr):
            warnings.simplefilter("ignore", RuntimeWarning)
            warnings.simplefilter("ignore", UserWarning)
            try:
                agent = laya.load(target_id, subfolder=subfolder, device=resolved_device)
            except Exception as exc:
                if local_snap is not None:
                    print(
                        f"[XLaya] Local snapshot load failed ({exc}); retrying via repo id.",
                        file=sys.stderr,
                    )
                    agent = laya.load("convaiinnovations/laya", subfolder=subfolder, device=resolved_device)
                else:
                    raise

        if cache:
            _MODEL_CACHE[canon_key] = (agent, resolved_device)
        return agent


def _is_hf_repo_cached(repo_id: str) -> bool:
    hf_cache = os.environ.get("HF_HUB_CACHE") or os.path.join(
        os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface"),
        "hub",
    )
    folder_name = "models--" + repo_id.replace("/", "--")
    snaps_dir = Path(hf_cache) / folder_name / "snapshots"
    if not snaps_dir.is_dir():
        return False
    try:
        for snap in snaps_dir.iterdir():
            if snap.is_dir() and any(snap.glob("*.safetensors")):
                return True
    except OSError:
        return False
    return False


def _resolve_vega_model(vega_model: str, resolved_device: str) -> str:
    raw = (vega_model or "auto").strip().lower()
    if raw == "08b":
        return "0.8b"
    if raw not in VALID_VEGA_MODELS:
        raise ValueError(
            f"Unsupported vega_model {vega_model!r}; expected one of {sorted(VALID_VEGA_MODELS)}."
        )
    if raw != "auto":
        return raw

    # Single-GPU VRAM + verified local snapshot check (prevents uncached HF downloads or multi-GPU sum errors)
    if (
        resolved_device.startswith("cuda")
        and _is_hf_repo_cached("Qwen/Qwen3.5-4B")
        and _resolve_local_vega_snapshot("4b") is not None
    ):
        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                dev_idx = 0
                if ":" in resolved_device:
                    try:
                        dev_idx = int(resolved_device.split(":", 1)[1])
                    except ValueError:
                        dev_idx = 0
                free_b, total_b = torch.cuda.mem_get_info(dev_idx)
                if free_b >= int(9.5 * (1024 ** 3)) or total_b >= int(14.0 * (1024 ** 3)):
                    return "4b"
        except Exception:  # nosec B110
            pass
    return "0.8b"


def _resolve_local_vega_snapshot(vega_model: str) -> Optional[str]:
    variant_map = {
        "0.8b": "",
        "08b": "",
        "4b": "Qwen3.5-4B",
        "gemma-1b": "gemma-3-1b-it",
        "27b": "Qwen3.8-27B",
    }
    key = (vega_model or "0.8b").strip().lower()
    if key not in variant_map:
        return None
    subfolder = variant_map[key]
    hf_cache = os.environ.get("HF_HUB_CACHE") or os.path.join(
        os.environ.get("HF_HOME") or os.path.expanduser("~/.cache/huggingface"),
        "hub",
    )
    snaps_dir = Path(hf_cache) / "models--nandakishorm--vega-U" / "snapshots"
    if not snaps_dir.is_dir():
        return None
    try:
        candidates = sorted(
            (p for p in snaps_dir.iterdir() if p.is_dir()),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for cand in candidates:
            target = cand / subfolder if subfolder else cand
            if (target / "vega_config.json").is_file() and (target / "engine.safetensors").is_file():
                return str(target)
    except OSError as exc:
        print(f"[XLaya] Warning: could not scan Vega HF snapshots: {exc}", file=sys.stderr)
    return None


def _apply_vega_policy_state(agent: Any, policy_path: str) -> None:
    norm_policy = str(Path(policy_path).resolve()) if policy_path and policy_path.strip() else ""
    current_policy = getattr(agent, "_xlaya_policy_path", "")
    if norm_policy:
        if current_policy != norm_policy:
            agent.vega.heads.clear()
            agent.calibration = None
            agent._novelty = None
            agent.load_calibration(norm_policy, verify=True)
            agent._xlaya_policy_path = norm_policy
    elif current_policy:
        agent.vega.heads.clear()
        agent.calibration = None
        agent._novelty = None
        agent._xlaya_policy_path = ""


def _load_vega_checkpoint(
    vega_model: str,
    resolved_device: str,
    cache: bool = True,
    policy_path: str = "",
) -> Any:
    import laya  # type: ignore

    eff_model = _resolve_vega_model(vega_model, resolved_device)
    cache_key = f"vega:{eff_model}"
    with _CACHE_LOCK:
        cached = _MODEL_CACHE.get(cache_key)
        if cached is not None and cached[1] == resolved_device:
            agent = cached[0]
            _apply_vega_policy_state(agent, policy_path)
            return agent

        local_vega = _resolve_local_vega_snapshot(eff_model)
        vega_target = local_vega if local_vega is not None else eff_model
        with warnings.catch_warnings(), contextlib.redirect_stdout(sys.stderr):
            warnings.simplefilter("ignore", RuntimeWarning)
            warnings.simplefilter("ignore", UserWarning)
            try:
                if eff_model == "27b" and local_vega is None:
                    agent = laya.load(
                        vegaml="0.8b",
                        backbone="Qwen/Qwen3.8-27B",
                        device=resolved_device,
                    )
                else:
                    agent = laya.load(vegaml=vega_target, device=resolved_device)
            except Exception as exc:
                if local_vega is not None:
                    print(
                        f"[XLaya] Local Vega snapshot load failed ({exc}); retrying via hub id.",
                        file=sys.stderr,
                    )
                    if eff_model == "27b":
                        agent = laya.load(
                            vegaml="0.8b",
                            backbone="Qwen/Qwen3.8-27B",
                            device=resolved_device,
                        )
                    else:
                        agent = laya.load(vegaml=eff_model, device=resolved_device)
                else:
                    raise

        agent._xlaya_policy_path = ""
        _apply_vega_policy_state(agent, policy_path)
        if cache:
            _MODEL_CACHE[cache_key] = (agent, resolved_device)
        return agent


def fit_policy(
    rows: Any,
    questions: Dict[str, Dict[str, Any]],
    policy_path: str,
    *,
    vega_model: str = "0.8b",
    device: str = "auto",
    folds: int = 5,
    calibrate: bool = True,
    target_precision: float = 0.95,
    resident_cache: bool = True,
) -> Dict[str, Any]:
    """Train TTT linear readout heads and split-conformal calibration, saving a reloadable policy."""
    if not questions or not isinstance(questions, dict):
        raise ValueError("fit_policy requires a non-empty 'questions' dictionary.")
    if not policy_path or not str(policy_path).strip():
        raise ValueError("fit_policy requires a non-empty 'policy_path' directory.")

    t0 = time.perf_counter()
    resolved_device = _resolve_device(device)
    eff_vega = _resolve_vega_model(vega_model, resolved_device)
    v_questions = _strip_noul_labels_for_vega(questions)

    v_agent = _load_vega_checkpoint(eff_vega, resolved_device, cache=resident_cache, policy_path="")
    with _CACHE_LOCK:
        v_agent.vega.heads.clear()
        v_agent.calibration = None
        v_agent._novelty = None
        v_agent._xlaya_policy_path = ""

        # Auto-adapt folds down to >=2 when small calibration sets (<35 rows) are supplied
        parsed_rows = v_agent.load_rows(rows, v_questions) if isinstance(rows, (str, os.PathLike)) else list(rows)
        n_rows = len(parsed_rows)
        eff_folds = max(2, int(folds))
        while eff_folds > 2 and n_rows < v_agent.min_rows(v_questions, folds=eff_folds, calibrate=calibrate):
            eff_folds -= 1

        eff_calibrate = bool(calibrate)
        if eff_calibrate and n_rows < v_agent.min_rows(v_questions, folds=eff_folds, calibrate=True):
            if n_rows >= v_agent.min_rows(v_questions, folds=eff_folds, calibrate=False):
                eff_calibrate = False

        fit_rep = v_agent.fit(
            parsed_rows,
            v_questions,
            folds=eff_folds,
            calibrate=eff_calibrate,
            target_precision=float(target_precision),
        )
        out_dir = str(Path(policy_path).resolve())
        save_rep = v_agent.save_calibration(out_dir)

        # Persist questions.json and refresh manifest.json so load_calibration(verify=True) succeeds
        q_file = os.path.join(out_dir, "questions.json")
        with open(q_file, "w", encoding="utf-8") as f:
            json.dump(v_questions, f, indent=2, ensure_ascii=False)

        from laya import policy as _laya_policy  # type: ignore

        tracked_names = ("heads.npz", "calibration.json", "questions.json")
        files_bytes = {
            n: open(os.path.join(out_dir, n), "rb").read()
            for n in tracked_names
            if os.path.exists(os.path.join(out_dir, n))
        }
        try:
            engine_sha = v_agent.vega.engine.base_sha256()
        except Exception:
            engine_sha = None
        with open(os.path.join(out_dir, "manifest.json"), "wb") as f:
            f.write(
                _laya_policy.manifest_for(
                    files_bytes,
                    format="laya-policy/1",
                    engine_sha256=engine_sha,
                    model=v_agent.model_id,
                )
            )
        v_agent._xlaya_policy_path = out_dir

    return {
        "ok": True,
        "policy_path": out_dir,
        "vega_model": eff_vega,
        "device": resolved_device,
        "folds_used": eff_folds,
        "calibrated": bool(save_rep.get("calibrated")),
        "heads": save_rep.get("heads", []),
        "fit_report": fit_rep,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


def get_status(profile: str = "auto", agent_tier: str = "auto") -> Dict[str, Any]:
    """Return current runtime, hardware profile, GPU/CPU, Laya/VegaML availability, and cache status."""
    hw = _resolve_hardware_profile(profile=profile, agent_tier=agent_tier, device="auto")
    laya_ok, laya_ver = _pkg_version("laya", "laya")
    vega_ok, vega_ver = _pkg_version("vegaml", "vegaml")

    torch_ver: Optional[str] = None
    cuda_ok = False
    mps_ok = False
    gpu_name: Optional[str] = None
    vram_total_gb: Optional[float] = None
    vram_free_gb: Optional[float] = None
    cpu_threads = _recommended_cpu_threads()
    default_dev = hw["device"]

    if hw["profile"] != "nano":
        try:
            import torch  # type: ignore

            torch_ver = str(torch.__version__)
            cuda_ok = bool(torch.cuda.is_available())
            mps_ok = bool(hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
            cpu_threads = _configure_cpu_threads(torch)
            if cuda_ok:
                if default_dev == "auto":
                    default_dev = "cuda"
                gpu_name = str(torch.cuda.get_device_name(0))
                try:
                    free_b, total_b = torch.cuda.mem_get_info(0)
                    vram_free_gb = round(free_b / (1024 ** 3), 2)
                    vram_total_gb = round(total_b / (1024 ** 3), 2)
                except Exception:  # nosec B110
                    pass
            elif mps_ok and default_dev == "auto":
                default_dev = "mps"
        except ImportError:
            pass

    with _CACHE_LOCK:
        loaded = list(_MODEL_CACHE.keys())

    rec_vega = "none" if hw["profile"] in ("nano", "edge") else _resolve_vega_model("auto", default_dev)
    return {
        "ok": True,
        "version": __version__,
        "profile": hw["profile"],
        "agent_tier": hw["agent_tier"],
        "python": sys.version.split()[0],
        "laya_available": laya_ok,
        "laya_version": laya_ver,
        "vegaml_available": vega_ok,
        "vegaml_version": vega_ver,
        "torch_version": torch_ver,
        "cuda_available": cuda_ok,
        "cuda_device_count": hw["cuda_device_count"],
        "mps_available": mps_ok,
        "device": default_dev,
        "gpu_name": gpu_name,
        "vram_total_gb": vram_total_gb,
        "vram_free_gb": vram_free_gb,
        "vram_cluster_gb": hw["vram_cluster_gb"],
        "host_ram_gb": hw["host_ram_gb"],
        "recommended_vega_model": rec_vega,
        "cpu_threads": cpu_threads,
        "loaded_models": loaded,
    }


def preload_models(
    models: Optional[Sequence[str]] = None,
    vega: bool = False,
    vega_model: str = "auto",
    device: str = "auto",
) -> Dict[str, Any]:
    """Preload requested ModernBERT and/or VegaML models into the thread-safe cache."""
    t0 = time.perf_counter()
    resolved_device = _resolve_device(device)
    req_models = ["english"] if models is None else list(models)
    loaded_now: List[str] = []

    laya_ok, _ = _pkg_version("laya", "laya")
    if not laya_ok:
        return {
            "ok": False,
            "error": "laya package is not installed in this Python environment.",
            "loaded": [],
            "loaded_models": [],
            "device": resolved_device,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }

    with _CACHE_LOCK:
        for item in req_models:
            key = _normalize_model_key(item)
            if key.startswith("vega:"):
                v_name = _resolve_vega_model(key.split(":", 1)[1], resolved_device)
                _load_vega_checkpoint(v_name, resolved_device, cache=True)
                loaded_now.append(f"vega:{v_name}")
            elif key == "ensemble":
                for sub_key in ("english", "typed-decisions"):
                    _load_laya_checkpoint(sub_key, resolved_device, cache=True)
                    if sub_key not in loaded_now:
                        loaded_now.append(sub_key)
            else:
                _load_laya_checkpoint(key, resolved_device, cache=True)
                if key not in loaded_now:
                    loaded_now.append(key)

        if vega:
            eff_vega = _resolve_vega_model(vega_model, resolved_device)
            v_key = f"vega:{eff_vega}"
            if v_key not in loaded_now:
                _load_vega_checkpoint(eff_vega, resolved_device, cache=True)
                loaded_now.append(v_key)

        all_loaded = list(_MODEL_CACHE.keys())

    return {
        "ok": True,
        "loaded": loaded_now,
        "loaded_models": all_loaded,
        "device": resolved_device,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


def unload_models() -> Dict[str, Any]:
    """Evict all cached models and reclaim CPU RAM and CUDA VRAM."""
    with _CACHE_LOCK:
        unloaded = list(_MODEL_CACHE.keys())
        _MODEL_CACHE.clear()

    gc.collect()
    try:
        import torch  # type: ignore

        if torch.cuda.is_available():
            torch.cuda.empty_cache()
    except ImportError:
        pass

    return {
        "ok": True,
        "unloaded": unloaded,
        "loaded_models": [],
    }


# ---------------------------------------------------------------------------
# Language Detection & Answer Sanitization Helpers
# ---------------------------------------------------------------------------


def _flatten_text(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, dict):
        return " ".join(f"{_flatten_text(k)} {_flatten_text(v)}" for k, v in obj.items())
    if isinstance(obj, (list, tuple, set)):
        return " ".join(_flatten_text(x) for x in obj)
    return str(obj)


def _strip_code_and_cli_tokens(text: str) -> str:
    no_fences = re.sub(r"(?ms)^[ ]{0,3}(`{3,}|~{3,})[^\n]*\n.*?\n[ ]{0,3}\1[ \t]*$", " ", text)
    no_inline = re.sub(r"`[^`\n]+`", " ", no_fences)
    no_flags = re.sub(r"(?:--[A-Za-z0-9_-]+|<[A-Za-z0-9_./:-]+>|\*\.[\w]+)", " ", no_inline)
    return no_flags


def _is_english_text(state_or_text: Any) -> bool:
    flat = _flatten_text(state_or_text)
    if not flat.strip():
        return True
    if NON_ENGLISH_SCRIPT_RE.search(flat):
        return False
    prose = _strip_code_and_cli_tokens(flat)
    has_non_ascii_alpha = any(ord(ch) >= 128 and ch.isalpha() for ch in prose)
    if not has_non_ascii_alpha:
        prose_words = re.findall(r"\b[A-Za-z]{2,}\b", prose)
        if len(prose_words) < 6:
            return True
    if "laya" not in sys.modules:
        # Avoid paying ~2.5s cold `import laya` + `torch` inside Stage 0 chunking;
        # `NON_ENGLISH_SCRIPT_RE` + Latin diacritic check (`has_non_ascii_alpha`) covers offline Stage 0.
        return not has_non_ascii_alpha
    try:
        import laya  # type: ignore

        probe = prose if prose.strip() else flat
        return bool(laya.is_english(probe))
    except ImportError:
        return True


def _questions_head_text(questions: Dict[str, Dict[str, Any]]) -> str:
    parts: List[str] = []
    for qdef in questions.values():
        if not isinstance(qdef, dict):
            continue
        instr = qdef.get("instructions")
        if instr:
            parts.append(str(instr))
        crit = qdef.get("criteria")
        if isinstance(crit, dict):
            for k, v in crit.items():
                parts.append(str(k))
                if v is not None:
                    parts.append(str(v))
        elif isinstance(crit, (list, tuple)):
            parts.extend(str(x) for x in crit if x is not None)
    return " ".join(parts)


def _entropy_conf_from_probs(probs: Mapping[str, float]) -> float:
    vals = [float(v) for v in probs.values() if float(v) > 0.0]
    k = len(probs)
    if k < 2 or not vals:
        return 1.0
    h = -sum(v * math.log(v) for v in vals)
    return round(max(0.0, min(1.0, 1.0 - h / math.log(k))), 4)


def _blend_two_predictions(
    pred_a: Dict[str, Any],
    pred_b: Dict[str, Any],
    questions: Mapping[str, Mapping[str, Any]],
    w_a: float = 0.45,
    w_b: float = 0.55,
) -> Dict[str, Any]:
    """Blend two Stage 1 Laya predictions and compute inter-model disagreement & agreement."""
    out = dict(pred_a)
    ans_a_map = pred_a.get("answers") or {}
    ans_b_map = pred_b.get("answers") or {}
    blended_answers: Dict[str, Any] = {}

    for qid, qdef in questions.items():
        qa = dict(ans_a_map.get(qid) or {})
        qb = dict(ans_b_map.get(qid) or {})
        if not qa and not qb:
            continue
        if not qb:
            qa["disagreement"] = 0.0
            qa["model_agreement"] = 1.0
            qa["label_agree"] = True
            blended_answers[qid] = qa
            continue

        qtype = str(qdef.get("type", qa.get("type", "noul")))
        probs_a = qa.get("probabilities") or {}
        probs_b = qb.get("probabilities") or {}
        all_keys = list(dict.fromkeys(list(probs_a.keys()) + list(probs_b.keys())))

        raw_blend: Dict[str, float] = {}
        for k in all_keys:
            raw_blend[k] = float(w_a) * float(probs_a.get(k, 0.0)) + float(w_b) * float(probs_b.get(k, 0.0))
        total_p = sum(raw_blend.values())
        if total_p > 0.0:
            norm_probs = {k: round(v / total_p, 6) for k, v in raw_blend.items()}
            # Adjust rounding residual on top key so sum(norm_probs) == 1.0 exactly
            top_k_key = max(norm_probs, key=norm_probs.get)
            residual = round(1.0 - sum(norm_probs.values()), 6)
            norm_probs[top_k_key] = round(max(0.0, min(1.0, norm_probs[top_k_key] + residual)), 6)
        else:
            norm_probs = {k: round(1.0 / max(1, len(all_keys)), 6) for k in all_keys}

        merged_q = dict(qa)
        merged_q["probabilities"] = norm_probs
        merged_q["confidence"] = _entropy_conf_from_probs(norm_probs)
        merged_q["answer_confidence"] = round(max(norm_probs.values()), 6) if norm_probs else 0.0

        if qtype == "noul":
            noul_a = float(qa.get("noul", probs_a.get("true", 0.0)))
            noul_b = float(qb.get("noul", probs_b.get("true", 0.0)))
            noul_blend = round(float(w_a) * noul_a + float(w_b) * noul_b, 6)
            merged_q["noul"] = noul_blend
            disagree = abs(noul_a - noul_b)
            agree = (noul_a >= 0.5) == (noul_b >= 0.5)
        elif qtype == "score":
            exp_a = float(qa.get("expected_score", qa.get("score", 0.0)))
            exp_b = float(qb.get("expected_score", qb.get("score", 0.0)))
            exp_blend = round(float(w_a) * exp_a + float(w_b) * exp_b, 4)
            best_lvl = int(max(norm_probs, key=lambda k: norm_probs[k])) if norm_probs else int(round(exp_blend))
            merged_q["score"] = best_lvl
            merged_q["expected_score"] = exp_blend
            max_lvl = max(1.0, float(len(norm_probs) - 1))
            disagree = abs(exp_a - exp_b) / max_lvl
            agree = int(qa.get("score", round(exp_a))) == int(qb.get("score", round(exp_b)))
        else:
            best_choice = max(norm_probs, key=lambda k: norm_probs[k]) if norm_probs else qa.get("choice")
            merged_q["choice"] = best_choice
            disagree = 0.5 * sum(
                abs(float(probs_a.get(k, 0.0)) - float(probs_b.get(k, 0.0))) for k in all_keys
            )
            agree = qa.get("choice") == qb.get("choice")

        dis_round = round(float(disagree), 4)
        merged_q["disagreement"] = dis_round
        merged_q["model_agreement"] = round(1.0 - dis_round, 4)
        merged_q["label_agree"] = bool(agree)
        blended_answers[qid] = merged_q

    out["answers"] = blended_answers
    return out


def _run_laya_agent_on_states(
    agent: Any,
    states_list: List[Any],
    questions: Dict[str, Dict[str, Any]],
    needs_tournament: bool,
    batch_size: int,
    group_size: int = 16,
) -> List[Dict[str, Any]]:
    import laya  # type: ignore

    if not states_list:
        return []
    if needs_tournament:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            return [
                laya.predict_tournament(agent, s, questions, group_size=group_size)
                for s in states_list
            ]
    if len(states_list) == 1:
        return [agent.predict(states_list[0], questions)]
    return agent.predict_batch(
        states_list,
        questions,
        batch_size=batch_size,
        sort_by_length=True,
    )


def _sanitize_prediction(pred: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(pred)
    raw_answers = pred.get("answers")
    if isinstance(raw_answers, dict):
        clean_answers: Dict[str, Any] = {}
        for qid, ans in raw_answers.items():
            if isinstance(ans, dict):
                clean_ans = {k: v for k, v in ans.items() if k not in ("unbound", "action")}
                if "route" in clean_ans or "calibrated" in clean_ans or "outbound" in pred:
                    clean_ans["outbound"] = bool(ans.get("outbound", pred.get("outbound", False)))
                    clean_ans["ood_score"] = round(
                        float(ans.get("ood_score", pred.get("ood_score", ans.get("energy", 0.0)))),
                        4,
                    )
                clean_answers[qid] = clean_ans
            else:
                clean_answers[qid] = ans
        out["answers"] = clean_answers
    return out


def _strip_noul_labels_for_vega(questions: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    cleaned: Dict[str, Dict[str, Any]] = {}
    for qid, qdef in questions.items():
        if isinstance(qdef, dict) and "labels" in qdef:
            cleaned[qid] = {k: v for k, v in qdef.items() if k != "labels"}
        else:
            cleaned[qid] = qdef
    return cleaned


# ---------------------------------------------------------------------------
# Direct Prediction Seam (MCP Server & Programmatic Python Entry Point)
# ---------------------------------------------------------------------------


def predict_direct(
    state: Any = None,
    questions: Optional[Dict[str, Dict[str, Any]]] = None,
    *,
    states: Optional[List[Any]] = None,
    model: str = "auto",
    profile: str = "auto",
    vega: bool = False,
    vega_model: str = "auto",
    views: int = 1,
    policy_path: str = "",
    image: Optional[str] = None,
    audio: Optional[str] = None,
    video: Optional[str] = None,
    device: str = "auto",
    batch_size: int = 32,
    group_size: int = 16,
) -> Dict[str, Any]:
    """Run direct single-state, batched, or local multimodal neural/conformal prediction."""
    if not questions or not isinstance(questions, dict):
        raise ValueError("predict_direct requires a non-empty 'questions' dictionary.")

    hw = _resolve_hardware_profile(profile=profile, agent_tier="auto", device=device)
    eff_views = max(1, min(3, int(views or 1)))
    if hw["profile"] == "max" and vega and int(views or 1) == 1:
        eff_views = 3
    has_multimodal = any(x is not None and str(x).strip() != "" for x in (image, audio, video))
    is_batch = states is not None
    if not is_batch and state is None and not has_multimodal:
        raise ValueError(
            "predict_direct requires 'state', 'states', or a multimodal input ('image', 'audio', 'video')."
        )

    t0 = time.perf_counter()

    # Strict zero-torch guard for profile == 'nano' (multimodal requires VegaAgent/torch)
    if hw["profile"] == "nano":
        if has_multimodal:
            raise ValueError(
                "Multimodal inputs ('image', 'audio', 'video') are not supported under zero-torch profile='nano'."
            )
        prompt_framing = {
            "does", "mention", "mentions", "report", "text", "passage", "rate", "score",
            "relevance", "classify", "select", "category", "whether", "state", "states",
        }

        def _nano_affinity(doc_txt: str, target_txt: str) -> float:
            doc_low = doc_txt.lower()
            doc_toks = set(_extract_lexical_tokens(doc_txt))
            tgt_toks = [t for t in dict.fromkeys(_extract_lexical_tokens(target_txt)) if t not in prompt_framing]
            anchors = _extract_technical_anchors(target_txt)
            cov = (sum(1 for t in tgt_toks if t in doc_toks or t in doc_low) / len(tgt_toks)) if tgt_toks else 0.0
            anc = (sum(1 for a in anchors if a in doc_low) / len(anchors)) if anchors else cov
            cos = _cosine_256d(_hashed_256d_vec(doc_txt), _hashed_256d_vec(target_txt))
            return max(0.0, min(1.0, 0.45 * cov + 0.35 * anc + 0.20 * cos))

        items_nano: List[Any] = list(states) if is_batch else [state]
        nano_preds: List[Dict[str, Any]] = []
        for st_item in items_nano:
            st_txt = st_item if isinstance(st_item, str) else _format_record(st_item)
            ans_map: Dict[str, Any] = {}
            for qid, qdef in questions.items():
                qtype = str(qdef.get("type", "noul"))
                instr = str(qdef.get("instructions", ""))
                crit = qdef.get("criteria")
                aff = _nano_affinity(st_txt, instr)
                if qtype == "choice" and isinstance(crit, dict) and crit:
                    best_k = next(iter(crit.keys()))
                    best_v = -1.0
                    for ck, cv in crit.items():
                        sc = _nano_affinity(st_txt, f"{ck} {cv}")
                        if sc > best_v:
                            best_v = sc
                            best_k = str(ck)
                    ans_map[qid] = {"choice": best_k, "confidence": round(0.45 + 0.50 * max(0.0, best_v), 4)}
                elif qtype == "score":
                    sc_val = round(min(4.0, aff * 4.0), 4)
                    ans_map[qid] = {"score": int(round(sc_val)), "expected_score": sc_val, "confidence": 0.60}
                else:
                    ans_map[qid] = {"noul": round(min(1.0, aff), 4), "confidence": 0.60}
            nano_preds.append({"answers": ans_map})
        out_nano: Dict[str, Any] = {
            "ok": True,
            "stage": "stage0_nano",
            "profile": "nano",
            "model": "pure-python-nano",
            "device": "cpu",
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }
        if is_batch:
            out_nano["results"] = nano_preds
        else:
            out_nano["result"] = nano_preds[0] if nano_preds else {}
        return out_nano

    resolved_device = hw["device"] if hw["profile_explicit"] else _resolve_device(device)
    if hw["profile"] == "edge" and not has_multimodal:
        vega = False
        if (model or "auto").strip().lower() == "ensemble":
            model = "typed"

    # Automatically route to VegaAgent when vega=True, policy_path is set, or multimodal inputs are given
    use_vega = bool(vega or (policy_path and str(policy_path).strip()) or has_multimodal)
    if use_vega:
        eff_vega = _resolve_vega_model(vega_model, resolved_device)
        v_agent = _load_vega_checkpoint(
            eff_vega,
            resolved_device,
            cache=True,
            policy_path=policy_path,
        )
        v_questions = _strip_noul_labels_for_vega(questions)
        if has_multimodal:
            mm_kwargs: Dict[str, Any] = {"questions": v_questions, "views": eff_views}
            if image is not None and str(image).strip():
                mm_kwargs["image"] = str(image).strip()
            elif audio is not None and str(audio).strip():
                mm_kwargs["audio"] = str(audio).strip()
            elif video is not None and str(video).strip():
                mm_kwargs["video"] = str(video).strip()
            raw_preds: List[Dict[str, Any]] = [v_agent.predict(**mm_kwargs)]
        else:
            items_vega: List[Any] = list(states) if is_batch else [state]
            if not items_vega:
                raw_preds = []
            elif len(items_vega) == 1:
                raw_preds = [v_agent.predict(items_vega[0], v_questions, views=eff_views)]
            else:
                raw_preds = v_agent.predict_batch(
                    items_vega,
                    v_questions,
                    batch_size=batch_size,
                    views=eff_views,
                )
        sanitized = [_sanitize_prediction(p) for p in raw_preds]
        payload: Dict[str, Any] = {
            "ok": True,
            "stage": "stage2_vega",
            "model": f"vega:{eff_vega}",
            "views": eff_views,
            "calibrated": bool(getattr(v_agent, "calibration", None) is not None),
            "device": resolved_device,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }
        if policy_path and str(policy_path).strip():
            payload["policy_path"] = str(Path(policy_path).resolve())
        if is_batch and not has_multimodal:
            payload["results"] = sanitized
        else:
            payload["result"] = sanitized[0] if sanitized else {}
        return payload

    items: List[Any] = list(states) if is_batch else [state]
    needs_tournament = any(
        isinstance(qdef, dict)
        and qdef.get("type") == "choice"
        and len(qdef.get("criteria") or {}) > 20
        for qdef in questions.values()
    )

    req_model = (model or "auto").strip().lower()
    if req_model not in ("", "auto"):
        norm_req = _normalize_model_key(req_model)
        if norm_req not in ("english", "multilingual", "typed-decisions", "ensemble"):
            raise ValueError(
                f"Unsupported predict_direct model {model!r}; expected 'auto', 'en', 'multi', 'typed', or 'ensemble'."
            )
    else:
        req_model = "auto"
        norm_req = "auto"
    head_en = _is_english_text(_questions_head_text(questions))

    if norm_req == "typed-decisions":
        agent_td = _load_laya_checkpoint("typed-decisions", resolved_device, cache=True)
        td_preds = _run_laya_agent_on_states(agent_td, items, questions, needs_tournament, batch_size, group_size)
        final_preds = [_sanitize_prediction(p) for p in td_preds]
        payload = {
            "ok": True,
            "stage": "stage1_laya",
            "model": "typed-decisions",
            "language_routing": {
                "english": 0,
                "multilingual": 0,
                "typed_decisions": len(items),
                "head_guard_multilingual": False,
            },
            "device": resolved_device,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        }
        if is_batch:
            payload["results"] = final_preds
        else:
            payload["result"] = final_preds[0]
        return payload

    en_indices: List[int] = []
    ml_indices: List[int] = []
    if norm_req == "english":
        en_indices = list(range(len(items)))
    elif norm_req == "multilingual":
        ml_indices = list(range(len(items)))
    elif not head_en:
        ml_indices = list(range(len(items)))
    else:
        for idx, item in enumerate(items):
            if _is_english_text(item):
                en_indices.append(idx)
            else:
                ml_indices.append(idx)

    merged: List[Optional[Dict[str, Any]]] = [None] * len(items)
    if norm_req == "ensemble":
        agent_td = _load_laya_checkpoint("typed-decisions", resolved_device, cache=True)
        if en_indices:
            agent_en = _load_laya_checkpoint("english", resolved_device, cache=True)
            en_states = [items[i] for i in en_indices]
            preds_en = _run_laya_agent_on_states(
                agent_en, en_states, questions, needs_tournament, batch_size, group_size
            )
            preds_td = _run_laya_agent_on_states(
                agent_td, en_states, questions, needs_tournament, batch_size, group_size
            )
            for orig_i, p_en, p_td in zip(en_indices, preds_en, preds_td):
                blended = _blend_two_predictions(p_en, p_td, questions, w_a=0.45, w_b=0.55)
                merged[orig_i] = _sanitize_prediction(blended)
        if ml_indices:
            agent_ml = _load_laya_checkpoint("multilingual", resolved_device, cache=True)
            ml_states = [items[i] for i in ml_indices]
            preds_ml = _run_laya_agent_on_states(
                agent_ml, ml_states, questions, needs_tournament, batch_size, group_size
            )
            preds_td_ml = _run_laya_agent_on_states(
                agent_td, ml_states, questions, needs_tournament, batch_size, group_size
            )
            w_ml, w_td = (0.75, 0.25) if head_en else (1.0, 0.0)
            for orig_i, p_ml, p_td in zip(ml_indices, preds_ml, preds_td_ml):
                blended = _blend_two_predictions(p_ml, p_td, questions, w_a=w_ml, w_b=w_td)
                merged[orig_i] = _sanitize_prediction(blended)
        used_model = "ensemble(en+typed-decisions)" if not ml_indices else "ensemble(en+typed+multilingual)"
    else:
        for bucket_key, bucket_idxs in (("english", en_indices), ("multilingual", ml_indices)):
            if not bucket_idxs:
                continue
            agent = _load_laya_checkpoint(bucket_key, resolved_device, cache=True)
            bucket_states = [items[i] for i in bucket_idxs]
            bucket_preds = _run_laya_agent_on_states(
                agent, bucket_states, questions, needs_tournament, batch_size, group_size
            )
            for orig_i, pred in zip(bucket_idxs, bucket_preds):
                merged[orig_i] = _sanitize_prediction(pred)
        used_model = (
            "english"
            if not ml_indices
            else ("multilingual" if not en_indices else "bilingual(per-state)")
        )

    final_preds = [p for p in merged if p is not None]
    payload = {
        "ok": True,
        "stage": "stage1_laya",
        "model": used_model,
        "language_routing": {
            "english": len(en_indices),
            "multilingual": len(ml_indices),
            "head_guard_multilingual": not head_en and req_model in ("auto", "ensemble"),
        },
        "device": resolved_device,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }
    if is_batch:
        payload["results"] = final_preds
    else:
        payload["result"] = final_preds[0]
    return payload


# ---------------------------------------------------------------------------
# Stage 0: Multi-Format Fence-Safe Chunker & Breadcrumb Engine
# ---------------------------------------------------------------------------


_PUNCT_TOKEN_CHARS = "|`{}[]()<>:;=/\\_-*#~"
_PUNCT_DEL_TABLE = str.maketrans("", "", _PUNCT_TOKEN_CHARS)


def _estimate_tokens(text: str) -> float:
    if text.isascii():
        ascii_count = len(text)
        non_ascii = 0
    else:
        ascii_count = sum(1 for ch in text if ord(ch) < 128)
        non_ascii = len(text) - ascii_count
    punct = len(text) - len(text.translate(_PUNCT_DEL_TABLE))
    return (ascii_count / 3.8) + (non_ascii * 0.9) + (punct * 0.35)


def _token_budget_for_text(text: str) -> float:
    return 380.0 if _is_english_text(text) else 780.0


def _fits_budget(text: str, max_chars: int) -> bool:
    if len(text) > max_chars:
        return False
    est = _estimate_tokens(text)
    if est <= 380.0:
        return True
    if est > 780.0:
        return False
    return est <= _token_budget_for_text(text)


def _check_fence_transition(
    line: str,
    fence_state: Optional[Tuple[str, int]],
) -> Optional[Tuple[str, int]]:
    m = FENCE_OPEN_RE.match(line)
    if not m:
        return fence_state
    run, rest = m.group(1), m.group(2)
    ch = run[0]
    run_len = len(run)
    if fence_state is None:
        if ch == "`" and "`" in rest:
            return None
        return (ch, run_len)
    open_ch, open_len = fence_state
    if ch == open_ch and run_len >= open_len and not rest.strip():
        return None
    return fence_state


def _make_chunk(
    file_path: Path,
    rel_prefix: str,
    heading: str,
    start_line: int,
    end_line: int,
    text: str,
    ref_suffix: Optional[str] = None,
) -> Dict[str, Any]:
    suffix = ref_suffix if ref_suffix is not None else f"#L{start_line}-L{end_line}"
    return {
        "file": str(file_path.as_posix()),
        "name": file_path.name,
        "heading": heading,
        "start_line": start_line,
        "end_line": end_line,
        "ref": f"{rel_prefix}{suffix}",
        "text": text,
    }


def _split_section_lines(
    file_path: Path,
    rel_prefix: str,
    full_breadcrumb: str,
    parent_breadcrumb: str,
    start_ln: int,
    s_lines: List[str],
    max_chars: int,
    is_code: bool = False,
) -> List[Dict[str, Any]]:
    raw_body = "\n".join(s_lines).strip()
    if not raw_body:
        return []

    first_prefix = f"[{parent_breadcrumb}]\n" if parent_breadcrumb else ""
    cont_prefix = f"[{full_breadcrumb}]\n" if full_breadcrumb else ""

    def _fast_fits(txt: str) -> bool:
        if len(txt) > max_chars:
            return False
        est = _estimate_tokens(txt)
        if is_code:
            return est <= 380.0
        if est <= 380.0:
            return True
        if est > 780.0:
            return False
        return est <= _token_budget_for_text(txt)

    first_candidate = first_prefix + raw_body
    if _fast_fits(first_candidate):
        return [
            _make_chunk(
                file_path,
                rel_prefix,
                full_breadcrumb,
                start_ln,
                start_ln + len(s_lines) - 1,
                first_candidate,
            )
        ]

    # Group lines into fence-safe paragraph blocks separated by blank lines outside fences
    blocks: List[Tuple[int, int, List[str]]] = []
    cur_lines: List[str] = []
    cur_start = start_ln
    fence_state: Optional[Tuple[str, int]] = None

    for idx_off, line in enumerate(s_lines):
        ln_no = start_ln + idx_off
        was_in_fence = fence_state is not None
        fence_state = _check_fence_transition(line, fence_state)
        is_blank_outside = (not was_in_fence) and (fence_state is None) and (not line.strip())

        if is_blank_outside:
            if cur_lines:
                blocks.append((cur_start, ln_no - 1, cur_lines))
                cur_lines = []
            cur_start = ln_no + 1
        else:
            if not cur_lines:
                cur_start = ln_no
            cur_lines.append(line)

    if cur_lines:
        blocks.append((cur_start, start_ln + len(s_lines) - 1, cur_lines))

    chunks: List[Dict[str, Any]] = []
    acc_lines: List[str] = []
    acc_chars = 0
    acc_toks = 0.0
    acc_non_en = False
    acc_start = start_ln
    acc_end = start_ln
    is_first_emit = True
    first_pfx_toks = _estimate_tokens(first_prefix) if first_prefix else 0.0
    cont_pfx_toks = _estimate_tokens(cont_prefix) if cont_prefix else 0.0
    newline_tok = 1.0 / 3.8

    def emit_accumulated() -> None:
        nonlocal acc_lines, acc_chars, acc_toks, acc_non_en, is_first_emit
        if not acc_lines:
            return
        body = "\n".join(acc_lines).strip()
        acc_lines = []
        acc_chars = 0
        acc_toks = 0.0
        acc_non_en = False
        if not body:
            return
        pfx = first_prefix if is_first_emit else cont_prefix
        is_first_emit = False
        chunks.append(
            _make_chunk(
                file_path,
                rel_prefix,
                full_breadcrumb,
                acc_start,
                acc_end,
                (pfx + body)[:max_chars],
            )
        )

    for b_start, b_end, b_lines in blocks:
        b_text = "\n".join(b_lines)
        b_strip = b_text.strip()
        b_tok = _estimate_tokens(b_strip)
        b_non_en = False if is_code else bool(NON_ENGLISH_SCRIPT_RE.search(b_strip))
        pfx = first_prefix if (is_first_emit and not acc_lines) else cont_prefix
        pfx_tok = first_pfx_toks if (is_first_emit and not acc_lines) else cont_pfx_toks

        if acc_lines:
            comb_chars = len(pfx) + acc_chars + 2 + len(b_strip)
            comb_toks = pfx_tok + acc_toks + 2.0 * newline_tok + b_tok
            comb_non_en = acc_non_en or b_non_en
            tok_lim = 380.0 if (is_code or not comb_non_en) else 780.0
            fits_comb = (comb_chars <= max_chars) and (comb_toks <= tok_lim)
        else:
            tok_lim = 380.0 if (is_code or not b_non_en) else 780.0
            fits_comb = ((len(pfx) + len(b_strip)) <= max_chars) and ((pfx_tok + b_tok) <= tok_lim)

        if fits_comb:
            if not acc_lines:
                acc_start = b_start
                acc_lines = list(b_lines)
                acc_chars = len(b_strip)
                acc_toks = b_tok
                acc_non_en = b_non_en
            else:
                acc_lines.append("")
                acc_lines.extend(b_lines)
                acc_chars += 2 + len(b_strip)
                acc_toks += 2.0 * newline_tok + b_tok
                acc_non_en = acc_non_en or b_non_en
            acc_end = b_end
            continue

        emit_accumulated()
        pfx = first_prefix if is_first_emit else cont_prefix
        pfx_tok = first_pfx_toks if is_first_emit else cont_pfx_toks
        tok_lim_single = 380.0 if (is_code or not b_non_en) else 780.0
        if ((len(pfx) + len(b_strip)) <= max_chars) and ((pfx_tok + b_tok) <= tok_lim_single):
            acc_start = b_start
            acc_end = b_end
            acc_lines = list(b_lines)
            acc_chars = len(b_strip)
            acc_toks = b_tok
            acc_non_en = b_non_en
            continue

        # Oversized single block: O(L) incremental line accumulator (zero O(L^2) string re-joining)
        line_buf: List[str] = []
        buf_chars = 0
        buf_toks = 0.0
        buf_non_en = False
        lb_start = b_start
        for l_off, single_line in enumerate(b_lines):
            cur_ln = b_start + l_off
            pfx = first_prefix if is_first_emit else cont_prefix
            pfx_tok = first_pfx_toks if is_first_emit else cont_pfx_toks
            line_budget = max(128, max_chars - len(pfx))

            if len(single_line) > line_budget:
                if line_buf:
                    body = "\n".join(line_buf).strip()
                    if body:
                        chunks.append(
                            _make_chunk(
                                file_path,
                                rel_prefix,
                                full_breadcrumb,
                                lb_start,
                                cur_ln - 1,
                                (pfx + body)[:max_chars],
                            )
                        )
                        is_first_emit = False
                    line_buf = []
                    buf_chars = 0
                    buf_toks = 0.0
                    buf_non_en = False

                s_strip = single_line.lstrip()
                row_head = (
                    ("|" + s_strip.split("|")[1] + " | ")[:60]
                    if s_strip.startswith("|") and len(s_strip.split("|")) > 1
                    else ""
                )
                for pos in range(0, len(single_line), max(96, line_budget - len(row_head))):
                    pfx = first_prefix if is_first_emit else cont_prefix
                    step = max(96, max_chars - len(pfx) - len(row_head))
                    seg = single_line[pos:pos + step]
                    seg_txt = (pfx + seg) if pos == 0 else (pfx + row_head + seg)
                    chunks.append(
                        _make_chunk(
                            file_path,
                            rel_prefix,
                            full_breadcrumb,
                            cur_ln,
                            cur_ln,
                            seg_txt[:max_chars],
                        )
                    )
                    is_first_emit = False
                lb_start = cur_ln + 1
                continue

            ln_tok = _estimate_tokens(single_line)
            ln_non_en = False if is_code else bool(NON_ENGLISH_SCRIPT_RE.search(single_line))
            trial_chars = (buf_chars + 1 + len(single_line)) if line_buf else len(single_line)
            trial_toks = (buf_toks + newline_tok + ln_tok) if line_buf else ln_tok
            trial_non_en = buf_non_en or ln_non_en
            tok_lim_ln = 380.0 if (is_code or not trial_non_en) else 780.0
            fits_ln = ((len(pfx) + trial_chars) <= max_chars) and ((pfx_tok + trial_toks) <= tok_lim_ln)

            if line_buf and not fits_ln:
                body = "\n".join(line_buf).strip()
                if body:
                    chunks.append(
                        _make_chunk(
                            file_path,
                            rel_prefix,
                            full_breadcrumb,
                            lb_start,
                            cur_ln - 1,
                            (pfx + body)[:max_chars],
                        )
                    )
                    is_first_emit = False
                line_buf = [single_line]
                buf_chars = len(single_line)
                buf_toks = ln_tok
                buf_non_en = ln_non_en
                lb_start = cur_ln
            else:
                if not line_buf:
                    lb_start = cur_ln
                    buf_chars = len(single_line)
                    buf_toks = ln_tok
                    buf_non_en = ln_non_en
                else:
                    buf_chars = trial_chars
                    buf_toks = trial_toks
                    buf_non_en = trial_non_en
                line_buf.append(single_line)

        if line_buf:
            pfx = first_prefix if is_first_emit else cont_prefix
            body = "\n".join(line_buf).strip()
            if body:
                chunks.append(
                    _make_chunk(
                        file_path,
                        rel_prefix,
                        full_breadcrumb,
                        lb_start,
                        b_end,
                        (pfx + body)[:max_chars],
                    )
                )
                is_first_emit = False

    emit_accumulated()
    return chunks


def _chunk_markdown_or_text(
    file_path: Path,
    raw_text: str,
    rel_prefix: str,
    max_chars: int,
    min_merge_chars: int = 180,
) -> List[Dict[str, Any]]:
    lines = raw_text.splitlines()
    if not lines:
        return []

    raw_sections: List[Tuple[str, str, int, int, List[str]]] = []
    heading_stack: Dict[int, str] = {}
    cur_full = file_path.name
    cur_parent = ""
    sec_start = 1
    sec_lines: List[str] = []
    fence_state: Optional[Tuple[str, int]] = None

    for idx, line in enumerate(lines, start=1):
        was_in_fence = fence_state is not None
        fence_state = _check_fence_transition(line, fence_state)
        in_fence_now = was_in_fence or (fence_state is not None)

        h_match = None if in_fence_now else HEADING_RE.match(line)
        if h_match:
            if sec_lines and any(x.strip() for x in sec_lines):
                raw_sections.append((cur_full, cur_parent, sec_start, idx - 1, sec_lines))
            level = len(h_match.group(1))
            title = h_match.group(2).rstrip("#").strip() or file_path.name
            for k in [existing for existing in heading_stack if existing >= level]:
                del heading_stack[k]
            heading_stack[level] = title
            ordered_levels = sorted(heading_stack)
            cur_full = " > ".join(heading_stack[k] for k in ordered_levels)
            cur_parent = " > ".join(heading_stack[k] for k in ordered_levels if k < level)
            sec_start = idx
            sec_lines = [line]
        else:
            sec_lines.append(line)

    if sec_lines and any(x.strip() for x in sec_lines):
        raw_sections.append((cur_full, cur_parent, sec_start, len(lines), sec_lines))

    # Merge pre-heading frontmatter stubs or drop empty parent-heading-only stubs covered by breadcrumb
    merged_sections: List[Tuple[str, str, int, int, List[str]]] = []
    i = 0
    while i < len(raw_sections):
        full_h, parent_h, s_ln, e_ln, s_lns = raw_sections[i]
        starts_with_heading = bool(s_lns and HEADING_RE.match(s_lns[0]))
        non_rule_body = [
            ln for ln in (s_lns[1:] if starts_with_heading else s_lns)
            if ln.strip() and not (len(ln.strip()) >= 3 and set(ln.strip()) <= {"-", "*", "_"})
        ]
        if starts_with_heading and not non_rule_body and (i + 1) < len(raw_sections):
            n_full, n_parent, _, ne_ln, ns_lns = raw_sections[i + 1]
            if n_parent.startswith(full_h):
                i += 1
                continue
            combined_text = "\n".join(s_lns + ns_lns)
            pfx = f"[{parent_h}]\n" if parent_h else ""
            if _fits_budget(pfx + combined_text, max_chars):
                raw_sections[i + 1] = (n_full, parent_h or n_parent, s_ln, ne_ln, s_lns + ns_lns)
                i += 1
                continue
        elif (
            not starts_with_heading
            and sum(len(x) + 1 for x in s_lns) < min_merge_chars
            and (i + 1) < len(raw_sections)
        ):
            n_full, n_parent, _, ne_ln, ns_lns = raw_sections[i + 1]
            combined_text = "\n".join(s_lns + ns_lns)
            pfx = f"[{parent_h}]\n" if parent_h else ""
            if _fits_budget(pfx + combined_text, max_chars):
                raw_sections[i + 1] = (n_full, parent_h or n_parent, s_ln, ne_ln, s_lns + ns_lns)
                i += 1
                continue
        merged_sections.append((full_h, parent_h, s_ln, e_ln, s_lns))
        i += 1

    chunks: List[Dict[str, Any]] = []
    for full_h, parent_h, s_ln, _e_ln, s_lns in merged_sections:
        chunks.extend(
            _split_section_lines(
                file_path=file_path,
                rel_prefix=rel_prefix,
                full_breadcrumb=full_h,
                parent_breadcrumb=parent_h,
                start_ln=s_ln,
                s_lines=s_lns,
                max_chars=max_chars,
            )
        )
    return chunks


def _strip_html_fragment(fragment: str) -> str:
    cleaned = HTML_NOISE_RE.sub(" ", fragment)
    cleaned = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"</(p|div|li|tr|section|article|h[1-6])>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = HTML_TAG_RE.sub(" ", cleaned)
    cleaned = html.unescape(cleaned)
    out_lines = [" ".join(ln.split()) for ln in cleaned.splitlines()]
    return "\n".join(ln for ln in out_lines if ln)


def _chunk_html(
    file_path: Path,
    raw_text: str,
    rel_prefix: str,
    max_chars: int,
) -> List[Dict[str, Any]]:
    total_lines = max(1, len(raw_text.splitlines()))
    matches = list(HTML_HEADING_RE.finditer(raw_text))
    if not matches:
        plain = _strip_html_fragment(raw_text)
        if not plain:
            return []
        return _split_section_lines(
            file_path,
            rel_prefix,
            file_path.name,
            "",
            1,
            plain.splitlines(),
            max_chars,
        )

    chunks: List[Dict[str, Any]] = []
    heading_stack: Dict[int, str] = {}

    if matches[0].start() > 0:
        intro_html = raw_text[: matches[0].start()]
        intro_txt = _strip_html_fragment(intro_html)
        if intro_txt:
            end_ln = max(1, raw_text.count("\n", 0, matches[0].start()) + 1)
            chunks.append(
                _make_chunk(file_path, rel_prefix, file_path.name, 1, end_ln, intro_txt[:max_chars])
            )

    for idx, m in enumerate(matches):
        level = int(m.group(1))
        h_title = _strip_html_fragment(m.group(2)).replace("\n", " ").strip() or file_path.name
        for k in [existing for existing in heading_stack if existing >= level]:
            del heading_stack[k]
        heading_stack[level] = h_title
        ordered = sorted(heading_stack)
        full_b = " > ".join(heading_stack[k] for k in ordered)
        parent_b = " > ".join(heading_stack[k] for k in ordered if k < level)

        seg_start = m.start()
        seg_end = matches[idx + 1].start() if (idx + 1) < len(matches) else len(raw_text)
        start_ln = raw_text.count("\n", 0, seg_start) + 1
        end_ln = min(total_lines, max(start_ln, raw_text.count("\n", 0, seg_end) + 1))

        body_txt = _strip_html_fragment(raw_text[seg_start:seg_end])
        if not body_txt:
            continue
        pfx = f"[{parent_b}]\n" if parent_b else ""
        full_txt = pfx + body_txt
        if _fits_budget(full_txt, max_chars):
            chunks.append(_make_chunk(file_path, rel_prefix, full_b, start_ln, end_ln, full_txt))
        else:
            for pos in range(0, len(body_txt), max(256, max_chars - len(f"[{full_b}]\n"))):
                sub_pfx = pfx if pos == 0 else f"[{full_b}]\n"
                step = max(256, max_chars - len(sub_pfx))
                sub = (sub_pfx + body_txt[pos:pos + step])[:max_chars]
                chunks.append(_make_chunk(file_path, rel_prefix, full_b, start_ln, end_ln, sub))
    return chunks


def _format_record(obj: Any) -> str:
    if isinstance(obj, dict):
        parts: List[str] = []
        for k, v in obj.items():
            val_str = json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v)
            parts.append(f"{k}: {val_str}")
        return " | ".join(parts)
    return json.dumps(obj, ensure_ascii=False)


def _chunk_jsonl(
    file_path: Path,
    raw_text: str,
    rel_prefix: str,
    max_chars: int,
    limit_hint: int = 0,
) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    for ln_no, raw_line in enumerate(raw_text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        heading = f"{file_path.name} [L{ln_no}]"
        try:
            parsed = json.loads(stripped)
            formatted = _format_record(parsed)
            if isinstance(parsed, dict):
                for key_cand in ("id", "name", "title", "heading", "slug"):
                    if key_cand in parsed and parsed[key_cand]:
                        heading = f"{file_path.name} [{parsed[key_cand]}]"
                        break
        except ValueError:
            formatted = stripped

        chunks.append(
            _make_chunk(file_path, rel_prefix, heading, ln_no, ln_no, formatted[:max_chars])
        )
        if limit_hint > 0 and len(chunks) >= limit_hint:
            break
    return chunks


def _chunk_json(
    file_path: Path,
    raw_text: str,
    rel_prefix: str,
    max_chars: int,
    limit_hint: int = 0,
) -> List[Dict[str, Any]]:
    total_lines = max(1, len(raw_text.splitlines()))
    try:
        data = json.loads(raw_text)
    except ValueError:
        return _chunk_markdown_or_text(file_path, raw_text, rel_prefix, max_chars)

    if isinstance(data, list) and data and all(isinstance(x, dict) for x in data):
        chunks: List[Dict[str, Any]] = []
        for idx, item in enumerate(data):
            label = str(item.get("id") or item.get("name") or item.get("title") or f"item-{idx}")
            heading = f"{file_path.name} [{label}]"
            formatted = _format_record(item)[:max_chars]
            chunks.append(
                _make_chunk(
                    file_path,
                    rel_prefix,
                    heading,
                    1,
                    total_lines,
                    formatted,
                    ref_suffix=f"#item-{idx}",
                )
            )
            if limit_hint > 0 and len(chunks) >= limit_hint:
                break
        return chunks

    pretty = json.dumps(data, indent=2, ensure_ascii=False)
    return _chunk_markdown_or_text(file_path, pretty, rel_prefix, max_chars)


def _chunk_csv(
    file_path: Path,
    raw_text: str,
    rel_prefix: str,
    max_chars: int,
    limit_hint: int = 0,
) -> List[Dict[str, Any]]:
    chunks: List[Dict[str, Any]] = []
    sio = io.StringIO(raw_text)
    reader = csv.DictReader(sio)
    if not reader.fieldnames:
        return []
    prev_line = 1
    for row_idx, row in enumerate(reader, start=1):
        end_ln = max(prev_line + 1, reader.line_num)
        start_ln = prev_line + 1
        prev_line = reader.line_num
        clean_row = {str(k): ("" if v is None else str(v)) for k, v in row.items() if k is not None}
        formatted = _format_record(clean_row).strip()
        if not formatted:
            continue
        heading = f"{file_path.name} [row {row_idx}]"
        chunks.append(
            _make_chunk(file_path, rel_prefix, heading, start_ln, end_ln, formatted[:max_chars])
        )
        if limit_hint > 0 and len(chunks) >= limit_hint:
            break
    return chunks


def _extract_ast_chunk_meta(
    node: ast.AST,
    symbol_name: str,
    node_kind: str,
    imported_symbols: List[str],
) -> Dict[str, Any]:
    defined: Dict[str, None] = {}
    params_anns: Dict[str, None] = {}
    calls: Dict[str, None] = {}
    async_di: Dict[str, None] = {}
    exceptions: Dict[str, None] = {}

    def _add_unique(dst: Dict[str, None], val: str) -> None:
        low = val.strip().lower()
        if len(low) >= 2:
            dst[low] = None

    for part in symbol_name.replace(".", " ").split():
        _add_unique(defined, part)

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        _add_unique(defined, node.name)
        if isinstance(node, ast.AsyncFunctionDef):
            _add_unique(async_di, node.name)
        all_args = (
            list(node.args.posonlyargs)
            + list(node.args.args)
            + list(node.args.kwonlyargs)
        )
        if node.args.vararg:
            all_args.append(node.args.vararg)
        if node.args.kwarg:
            all_args.append(node.args.kwarg)
        for arg in all_args:
            _add_unique(params_anns, arg.arg)
            if arg.annotation is not None:
                for sub in ast.walk(arg.annotation):
                    if isinstance(sub, ast.Name):
                        _add_unique(params_anns, sub.id)
                    elif isinstance(sub, ast.Attribute):
                        _add_unique(params_anns, sub.attr)
        for dflt in list(node.args.defaults) + [d for d in node.args.kw_defaults if d is not None]:
            for sub in ast.walk(dflt):
                if isinstance(sub, ast.Call):
                    fn_name = ""
                    if isinstance(sub.func, ast.Name):
                        fn_name = sub.func.id
                    elif isinstance(sub.func, ast.Attribute):
                        fn_name = sub.func.attr
                    if fn_name.lower() in ("depends", "security"):
                        for call_arg in sub.args:
                            if isinstance(call_arg, ast.Name):
                                _add_unique(async_di, call_arg.id)
                            elif isinstance(call_arg, ast.Attribute):
                                _add_unique(async_di, call_arg.attr)
        for dec in node.decorator_list:
            for sub in ast.walk(dec):
                if isinstance(sub, ast.Name):
                    _add_unique(params_anns, sub.id)
                    _add_unique(async_di, sub.id)
                elif isinstance(sub, ast.Attribute):
                    _add_unique(params_anns, sub.attr)
                    _add_unique(async_di, sub.attr)
    elif isinstance(node, ast.ClassDef):
        _add_unique(defined, node.name)
        for base in node.bases:
            if isinstance(base, ast.Name):
                _add_unique(params_anns, base.id)
            elif isinstance(base, ast.Attribute):
                _add_unique(params_anns, base.attr)

    def _collect_expr_targets(expr: Optional[ast.AST], dst: Dict[str, None]) -> None:
        if expr is None:
            return
        for inner in ast.walk(expr):
            if isinstance(inner, ast.Call):
                if isinstance(inner.func, ast.Name):
                    _add_unique(dst, inner.func.id)
                elif isinstance(inner.func, ast.Attribute):
                    _add_unique(dst, inner.func.attr)
            elif isinstance(inner, ast.Name):
                _add_unique(dst, inner.id)

    for sub in ast.walk(node):
        if isinstance(sub, ast.Call):
            if isinstance(sub.func, ast.Name):
                _add_unique(calls, sub.func.id)
                if sub.func.id.lower() in ("depends", "security"):
                    for call_arg in sub.args:
                        if isinstance(call_arg, ast.Name):
                            _add_unique(async_di, call_arg.id)
                        elif isinstance(call_arg, ast.Attribute):
                            _add_unique(async_di, call_arg.attr)
            elif isinstance(sub.func, ast.Attribute):
                _add_unique(calls, sub.func.attr)
                if isinstance(sub.func.value, ast.Name):
                    _add_unique(calls, f"{sub.func.value.id}.{sub.func.attr}")
        elif isinstance(sub, (ast.Await, ast.Yield, ast.YieldFrom)):
            _collect_expr_targets(sub.value, async_di)
        elif isinstance(sub, ast.AsyncFor):
            _collect_expr_targets(sub.iter, async_di)
        elif isinstance(sub, ast.AsyncWith):
            for item in sub.items:
                _collect_expr_targets(item.context_expr, async_di)
        elif isinstance(sub, ast.Raise) and sub.exc is not None:
            if isinstance(sub.exc, ast.Call):
                if isinstance(sub.exc.func, ast.Name):
                    _add_unique(exceptions, sub.exc.func.id)
                elif isinstance(sub.exc.func, ast.Attribute):
                    _add_unique(exceptions, sub.exc.func.attr)
            elif isinstance(sub.exc, ast.Name):
                _add_unique(exceptions, sub.exc.id)
        elif isinstance(sub, ast.ExceptHandler) and sub.type is not None:
            _collect_expr_targets(sub.type, exceptions)

    return {
        "symbol": symbol_name,
        "node_kind": node_kind,
        "defined_symbols": list(defined)[:48],
        "param_and_ann_tokens": list(params_anns)[:64],
        "called_symbols": list(calls)[:96],
        "async_or_di_symbols": list(async_di)[:64],
        "raised_exceptions": list(exceptions)[:32],
        "imported_symbols": imported_symbols[:64],
    }


def _build_compact_skeleton_header(
    import_stmt_map: Mapping[str, str],
    referenced_names: Sequence[str],
    *,
    class_sig: str = "",
    self_attrs: Sequence[str] = (),
) -> str:
    """Synthesize a compact zero-bloat AST skeleton header (<= 85 tokens) for split methods/functions."""
    hdr_lines: List[str] = []
    seen_imp: set[str] = set()
    for nm in referenced_names:
        imp_ln = import_stmt_map.get(nm.lower())
        if imp_ln and imp_ln not in seen_imp:
            seen_imp.add(imp_ln)
            hdr_lines.append(imp_ln[:92])
            if len(hdr_lines) >= 3:
                break
    if class_sig:
        hdr_lines.append(class_sig[:100])
        if self_attrs:
            attrs_str = ", ".join(f"self.{a}" for a in list(dict.fromkeys(self_attrs))[:6])
            hdr_lines.append(f"    # attrs: {attrs_str}"[:100])

    if not hdr_lines:
        return ""

    out_lines: List[str] = []
    for ln in hdr_lines:
        cand = "\n".join(out_lines + [ln])
        if _estimate_tokens(cand) > 85.0 or len(cand) > 290:
            break
        out_lines.append(ln)
    return "\n".join(out_lines)


def _chunk_python_ast(
    file_path: Path,
    raw_text: str,
    rel_prefix: str,
    max_chars: int,
    limit_hint: int = 0,
) -> List[Dict[str, Any]]:
    """Parse Python source into enclosing AST class/function/method spans with DI, bases & skeleton headers."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(raw_text)
    except (SyntaxError, ValueError):
        return _chunk_markdown_or_text(file_path, raw_text, rel_prefix, max_chars)

    lines = raw_text.splitlines()
    if not lines:
        return []

    norm_rel = rel_prefix.replace("\\", "/")
    if norm_rel.startswith("src/"):
        norm_rel = norm_rel[4:]
    mod_label = norm_rel if ("/" in norm_rel and len(norm_rel) <= 72) else file_path.name

    imported_symbols: List[str] = []
    import_stmt_map: Dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            names_short = []
            for alias in node.names:
                mod_tail = alias.name.split(".")[-1].lower()
                if mod_tail and mod_tail not in imported_symbols:
                    imported_symbols.append(mod_tail)
                bound = (alias.asname or alias.name.split(".")[-1]).strip()
                names_short.append(f"{alias.name} as {alias.asname}" if alias.asname else alias.name)
                if alias.asname and alias.asname.lower() not in imported_symbols:
                    imported_symbols.append(alias.asname.lower())
                if bound:
                    import_stmt_map.setdefault(bound.lower(), f"import {', '.join(names_short[:3])}")
        elif isinstance(node, ast.ImportFrom):
            mod_name = node.module or ""
            if mod_name:
                mod_tail = mod_name.split(".")[-1].lower()
                if mod_tail and mod_tail not in imported_symbols:
                    imported_symbols.append(mod_tail)
            alias_strs = [
                f"{a.name} as {a.asname}" if a.asname else a.name
                for a in node.names[:5]
                if a.name != "*"
            ]
            stmt_short = (
                f"from {'.' * (node.level or 0)}{mod_name} import {', '.join(alias_strs)}"
                if alias_strs
                else ""
            )
            for alias in node.names:
                nm = alias.name.lower()
                if nm != "*" and nm not in imported_symbols:
                    imported_symbols.append(nm)
                bound_low = (alias.asname or alias.name).lower()
                if stmt_short and bound_low != "*":
                    import_stmt_map.setdefault(bound_low, stmt_short)

    def _node_span(n: ast.AST) -> Tuple[int, int]:
        decs = getattr(n, "decorator_list", None) or []
        s_ln = min([getattr(n, "lineno", 1)] + [getattr(d, "lineno", 1) for d in decs])
        e_ln = getattr(n, "end_lineno", s_ln) or s_ln
        return max(1, s_ln), min(len(lines), max(s_ln, e_ln))

    chunks: List[Dict[str, Any]] = []
    covered = [False] * (len(lines) + 1)

    def _emit_ast_span(
        breadcrumb: str,
        parent_b: str,
        s_ln: int,
        e_ln: int,
        meta: Dict[str, Any],
    ) -> None:
        s_idx = s_ln - 1
        seg_lines = lines[s_idx:e_ln]
        if not any(ln.strip() for ln in seg_lines):
            return
        sub_chunks = _split_section_lines(
            file_path=file_path,
            rel_prefix=rel_prefix,
            full_breadcrumb=breadcrumb,
            parent_breadcrumb=parent_b,
            start_ln=s_ln,
            s_lines=seg_lines,
            max_chars=max_chars,
            is_code=True,
        )
        for sc in sub_chunks:
            sc["_ast_meta"] = meta
            chunks.append(sc)

    for top_node in tree.body:
        if isinstance(top_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            s_ln, e_ln = _node_span(top_node)
            for ln_i in range(s_ln, e_ln + 1):
                covered[ln_i] = True
            kind = "async_def" if isinstance(top_node, ast.AsyncFunctionDef) else "def"
            prefix_kw = "async def" if kind == "async_def" else "def"
            bcrumb = f"{mod_label} > {prefix_kw} {top_node.name}"
            meta = _extract_ast_chunk_meta(top_node, top_node.name, kind, imported_symbols)
            meta["canonical_symbol"] = top_node.name
            ref_syms = list(meta.get("param_and_ann_tokens") or []) + list(meta.get("called_symbols") or [])
            meta["skeleton_header"] = _build_compact_skeleton_header(import_stmt_map, ref_syms)
            _emit_ast_span(bcrumb, mod_label, s_ln, e_ln, meta)
        elif isinstance(top_node, ast.ClassDef):
            cs_ln, ce_ln = _node_span(top_node)
            for ln_i in range(cs_ln, ce_ln + 1):
                covered[ln_i] = True
            cls_text_len = sum(len(lines[i - 1]) + 1 for i in range(cs_ln, ce_ln + 1))
            methods = [
                m for m in top_node.body if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))
            ]

            # Extract class bases, class docstring summary, and self.<attr> fields once
            cls_bases_raw: List[str] = []
            for base in top_node.bases:
                if isinstance(base, ast.Name):
                    cls_bases_raw.append(base.id)
                elif isinstance(base, ast.Attribute):
                    cls_bases_raw.append(base.attr)
                elif hasattr(ast, "unparse"):
                    with contextlib.suppress(Exception):
                        cls_bases_raw.append(ast.unparse(base)[:36])
            cls_sig = (
                f"class {top_node.name}({', '.join(cls_bases_raw[:4])}):"
                if cls_bases_raw
                else f"class {top_node.name}:"
            )
            cls_doc = (ast.get_docstring(top_node) or "").strip().splitlines()
            cls_doc_first = cls_doc[0].strip()[:120] if cls_doc else ""
            self_attrs: List[str] = []
            for sub_n in ast.walk(top_node):
                if isinstance(sub_n, (ast.Assign, ast.AnnAssign)):
                    targets = sub_n.targets if isinstance(sub_n, ast.Assign) else [sub_n.target]
                    for t_expr in targets:
                        if (
                            isinstance(t_expr, ast.Attribute)
                            and isinstance(t_expr.value, ast.Name)
                            and t_expr.value.id == "self"
                            and t_expr.attr not in self_attrs
                        ):
                            self_attrs.append(t_expr.attr)

            if cls_text_len <= max_chars or not methods:
                meta = _extract_ast_chunk_meta(top_node, top_node.name, "class", imported_symbols)
                meta["canonical_symbol"] = top_node.name
                ref_syms = cls_bases_raw + list(meta.get("param_and_ann_tokens") or [])
                meta["skeleton_header"] = _build_compact_skeleton_header(import_stmt_map, ref_syms)
                _emit_ast_span(
                    f"{mod_label} > class {top_node.name}",
                    mod_label,
                    cs_ln,
                    ce_ln,
                    meta,
                )
            else:
                first_m_start, _ = _node_span(methods[0])
                if first_m_start > cs_ln:
                    hdr_node = ast.ClassDef(
                        name=top_node.name,
                        bases=top_node.bases,
                        keywords=top_node.keywords,
                        body=[
                            s
                            for s in top_node.body
                            if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))
                        ],
                        decorator_list=top_node.decorator_list,
                    )
                    hdr_meta = _extract_ast_chunk_meta(
                        hdr_node, top_node.name, "class", imported_symbols
                    )
                    hdr_meta["canonical_symbol"] = top_node.name
                    hdr_meta["skeleton_header"] = _build_compact_skeleton_header(
                        import_stmt_map, cls_bases_raw
                    )
                    _emit_ast_span(
                        f"{mod_label} > class {top_node.name}",
                        mod_label,
                        cs_ln,
                        first_m_start - 1,
                        hdr_meta,
                    )
                cls_base_lows = [b.lower() for b in cls_bases_raw if len(b) >= 2]
                parent_hdr = f"{mod_label} > {cls_sig}"
                if cls_doc_first:
                    parent_hdr = f"{parent_hdr} {cls_doc_first}"[:140]
                for m_node in methods:
                    ms_ln, me_ln = _node_span(m_node)
                    mkind = "async_def" if isinstance(m_node, ast.AsyncFunctionDef) else "def"
                    sym = f"{top_node.name}.{m_node.name}"
                    m_meta = _extract_ast_chunk_meta(m_node, sym, mkind, imported_symbols)
                    m_meta["canonical_symbol"] = sym
                    # Inherit enclosing ClassDef.bases so symptom queries on base/protocol types hit split methods!
                    merged_params = list(
                        dict.fromkeys((m_meta.get("param_and_ann_tokens") or []) + cls_base_lows)
                    )[:64]
                    m_meta["param_and_ann_tokens"] = merged_params
                    ref_syms = cls_bases_raw + merged_params + list(m_meta.get("called_symbols") or [])
                    m_meta["skeleton_header"] = _build_compact_skeleton_header(
                        import_stmt_map,
                        ref_syms,
                        class_sig=cls_sig,
                        self_attrs=self_attrs,
                    )
                    _emit_ast_span(
                        f"{mod_label} > class {top_node.name} > {m_node.name}",
                        parent_hdr,
                        ms_ln,
                        me_ln,
                        m_meta,
                    )
        if limit_hint > 0 and len(chunks) >= limit_hint:
            break

    # Emit uncovered module-level constants / router registrations / preamble blocks (compute AST walk once)
    if limit_hint <= 0 or len(chunks) < limit_hint:
        mod_meta_base: Optional[Dict[str, Any]] = None

        def _get_mod_meta() -> Dict[str, Any]:
            nonlocal mod_meta_base
            if mod_meta_base is None:
                shallow_mod = ast.Module(
                    body=[
                        s
                        for s in tree.body
                        if not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    ],
                    type_ignores=[],
                )
                mod_meta_base = _extract_ast_chunk_meta(shallow_mod, "<module>", "module", imported_symbols)
                mod_meta_base["canonical_symbol"] = "<module>"
                mod_meta_base["skeleton_header"] = ""
            return dict(mod_meta_base)

        run_start: Optional[int] = None
        for ln_i in range(1, len(lines) + 1):
            if not covered[ln_i]:
                if run_start is None:
                    run_start = ln_i
            else:
                if run_start is not None:
                    rs_idx = run_start - 1
                    re_idx = ln_i - 1
                    seg = lines[rs_idx:re_idx]
                    if any(x.strip() and not x.lstrip().startswith("#") for x in seg):
                        _emit_ast_span(
                            f"{mod_label} [<module>]",
                            "",
                            run_start,
                            ln_i - 1,
                            _get_mod_meta(),
                        )
                    run_start = None
        if run_start is not None:
            rs_idx = run_start - 1
            seg = lines[rs_idx:]
            if any(x.strip() and not x.lstrip().startswith("#") for x in seg):
                _emit_ast_span(
                    f"{mod_label} [<module>]",
                    "",
                    run_start,
                    len(lines),
                    _get_mod_meta(),
                )

    chunks.sort(key=lambda c: (c["start_line"], c["end_line"]))
    if limit_hint > 0 and len(chunks) > limit_hint:
        return chunks[:limit_hint]
    return chunks


_AST_CHUNK_CACHE: Dict[Tuple[str, int, int], List[Dict[str, Any]]] = {}


def chunk_file(
    file_path: Path,
    max_chars: int = 1600,
    whole_file: bool = False,
    rel_prefix: Optional[str] = None,
    limit_hint: int = 0,
) -> List[Dict[str, Any]]:
    """Split a supported file into fence-safe, AST-aware, or structured chunks with line/item refs."""
    ref_base = rel_prefix if rel_prefix is not None else file_path.name
    ext = file_path.suffix.lower()
    if not whole_file and ext in (".py", ".pyi"):
        ckey = (str(file_path), max_chars, limit_hint)
        cached_chs = _AST_CHUNK_CACHE.get(ckey)
        if cached_chs is not None:
            out_chs: List[Dict[str, Any]] = []
            for c in cached_chs:
                cp = dict(c)
                cp["ref"] = f"{ref_base}#L{cp['start_line']}-L{cp['end_line']}"
                out_chs.append(cp)
            return out_chs

    try:
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"[XLaya] Warning: could not read {file_path}: {exc}", file=sys.stderr)
        return []

    if not raw_text.strip():
        return []

    lines = raw_text.splitlines()

    if whole_file:
        body = _strip_html_fragment(raw_text) if ext in (".html", ".htm") else raw_text
        if not body.strip():
            return []
        ch = _make_chunk(
            file_path,
            ref_base,
            file_path.name,
            1,
            max(1, len(lines)),
            body[:max_chars],
        )
        ch["_full_text"] = body[:240000]
        return [ch]

    if ext in (".py", ".pyi"):
        fp_str = str(file_path)
        if fp_str not in _PRERANK_FILE_TOKEN_CACHE:
            head_txt = raw_text[:20480]
            h_all = frozenset(_extract_lexical_tokens(head_txt))
            d_all: set[str] = set()
            for dm in re.finditer(
                r"(?:^|\n)\s*(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", head_txt
            ):
                sym_nm = dm.group(1)
                d_all.update({sym_nm.lower()} | set(_split_ident_parts(sym_nm)))
            if len(_PRERANK_FILE_TOKEN_CACHE) > 16384:
                _PRERANK_FILE_TOKEN_CACHE.clear()
            _PRERANK_FILE_TOKEN_CACHE[fp_str] = (h_all, frozenset(d_all))
        res_chs = _chunk_python_ast(file_path, raw_text, ref_base, max_chars, limit_hint=limit_hint)
        if len(_AST_CHUNK_CACHE) > 4096:
            _AST_CHUNK_CACHE.clear()
        _AST_CHUNK_CACHE[(fp_str, max_chars, limit_hint)] = [dict(c) for c in res_chs]
        return res_chs
    if ext in (".html", ".htm"):
        return _chunk_html(file_path, raw_text, ref_base, max_chars)
    if ext == ".jsonl":
        return _chunk_jsonl(file_path, raw_text, ref_base, max_chars, limit_hint=limit_hint)
    if ext == ".json":
        return _chunk_json(file_path, raw_text, ref_base, max_chars, limit_hint=limit_hint)
    if ext == ".csv":
        return _chunk_csv(file_path, raw_text, ref_base, max_chars, limit_hint=limit_hint)
    return _chunk_markdown_or_text(file_path, raw_text, ref_base, max_chars)


def chunk_markdown_file(
    file_path: Path,
    max_chars: int = 1600,
    min_merge_chars: int = 180,
    whole_file: bool = False,
) -> List[Dict[str, Any]]:
    """Backward-compatible wrapper around chunk_file."""
    if whole_file or file_path.suffix.lower() in (".html", ".htm", ".jsonl", ".json", ".csv"):
        return chunk_file(file_path, max_chars=max_chars, whole_file=whole_file)
    try:
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"[XLaya] Warning: could not read {file_path}: {exc}", file=sys.stderr)
        return []
    if not raw_text.strip():
        return []
    return _chunk_markdown_or_text(
        file_path,
        raw_text,
        file_path.name,
        max_chars=max_chars,
        min_merge_chars=min_merge_chars,
    )


def collect_target_files(paths: Sequence[str], pattern: str = DEFAULT_PATTERN) -> Tuple[List[Path], Optional[Path]]:
    """Resolve input files/directories into sorted unique file paths and common scan root."""
    globs = [g.strip().lower() for g in pattern.split(",") if g.strip()] or ["*.md"]
    resolved_files: List[Path] = []
    seen: set[Path] = set()
    raw_resolved_inputs: List[Path] = []
    has_directory_input = False

    for raw in paths:
        p = Path(raw).resolve()
        if not p.exists():
            continue
        raw_resolved_inputs.append(p)
        if p.is_file():
            if p not in seen:
                seen.add(p)
                resolved_files.append(p)
        elif p.is_dir():
            has_directory_input = True
            for root_str, dirnames, filenames in os.walk(p):
                dirnames[:] = sorted(d for d in dirnames if d not in EXCLUDED_DIRS)
                root_path = Path(root_str)
                for fname in sorted(filenames):
                    fname_low = fname.lower()
                    if any(fnmatch.fnmatch(fname_low, g) for g in globs):
                        child = root_path / fname
                        if child not in seen:
                            seen.add(child)
                            resolved_files.append(child)

    is_single_file = (
        not has_directory_input
        and len(raw_resolved_inputs) == 1
        and len(resolved_files) == 1
    )
    if is_single_file or not resolved_files:
        return resolved_files, None

    anchors: List[str] = []
    for inp in raw_resolved_inputs:
        anchors.append(str(inp if inp.is_dir() else inp.parent))
    try:
        common = Path(os.path.commonpath(anchors))
        return resolved_files, common
    except ValueError:
        return resolved_files, None


def _rel_ref_prefix(file_path: Path, scan_root: Optional[Path]) -> str:
    if scan_root is None:
        return file_path.name
    try:
        rel = file_path.relative_to(scan_root).as_posix()
        return rel if rel else file_path.name
    except ValueError:
        return file_path.as_posix()


# ---------------------------------------------------------------------------
# Stage 0: Lexical BM25 + Code-Span / Identifier + Thai 3-Gram Engine
# ---------------------------------------------------------------------------


_CAMEL_IDENT_FIND_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*[A-Z][A-Za-z0-9]*\b")
_CAMEL_SPLIT_STEP1_RE = re.compile(r"([A-Z]+)([A-Z][a-z])")
_CAMEL_SPLIT_STEP2_RE = re.compile(r"([a-z0-9])([A-Z])")
_CODE_ANCHOR_NOISE = frozenset(
    {
        "true", "false", "none", "null", "nan", "inf", "self", "cls",
        "python", "python3", "pip", "pip install", "pytest", "bash", "sh",
        "json", "yaml", "yml", "toml", "http", "https", "utf-8", "utf8",
    }
)
_PROSE_HYPHEN_PREFIXES = frozenset(
    {
        "built", "auto", "non", "read", "write", "end", "step", "out", "up",
        "double", "single", "real", "user", "command", "high", "low", "third",
        "first", "second", "long", "short", "client", "server", "case", "cross",
        "multi", "sub", "pre", "post", "re", "co", "well", "in", "on", "off",
        "backwards", "backward", "forward", "thread", "type", "zero", "one", "two",
    }
)
_TIER2_AUX_DIRS = frozenset(
    {
        "docs_src", "docs", "doc", "tests", "test", "testing",
        "examples", "example", "benchmarks", "benchmark",
        "scripts", "devtools", "tutorials",
    }
)


_CAMEL_SPLIT_CACHE: Dict[str, Tuple[str, ...]] = {}


def _extract_lexical_tokens(text: str) -> List[str]:
    lower = text.lower()
    tokens = [w for w in LATIN_TOKEN_RE.findall(lower) if len(w) >= 2 and w not in STOPWORDS]

    for cam in _CAMEL_IDENT_FIND_RE.findall(text):
        pts = _CAMEL_SPLIT_CACHE.get(cam)
        if pts is None:
            s1 = _CAMEL_SPLIT_STEP1_RE.sub(r"\1 \2", cam)
            s2 = _CAMEL_SPLIT_STEP2_RE.sub(r"\1 \2", s1)
            cam_low = cam.lower()
            pts = tuple(
                pl
                for pt in s2.split()
                if len(pl := pt.lower()) >= 2 and pl not in STOPWORDS and pl != cam_low
            )
            if len(_CAMEL_SPLIT_CACHE) < 16384:
                _CAMEL_SPLIT_CACHE[cam] = pts
        if pts:
            tokens.extend(pts)

    if not text.isascii():
        for run in THAI_RUN_RE.findall(text):
            if len(run) < 3:
                tokens.append(run)
            else:
                tokens.extend(run[i:i + 3] for i in range(len(run) - 2))

        for cjk in CJK_RUN_RE.findall(text):
            if len(cjk) == 1:
                tokens.append(cjk)
            else:
                tokens.extend(cjk[i:i + 2] for i in range(len(cjk) - 1))

    return tokens


def _extract_technical_anchors(text: str) -> List[str]:
    anchors: List[str] = []
    seen: set[str] = set()
    for pat in (BACKTICK_SPAN_RE, CLI_FLAG_RE, IDENT_RE):
        for m in pat.finditer(text):
            val = (m.group(1) if m.lastindex else m.group(0)).strip().lower()
            if len(val) >= 2 and val not in seen:
                seen.add(val)
                anchors.append(val)
    return anchors


def _extract_code_anchors(text: str) -> List[str]:
    """Extract clean code/symbol anchors while stripping bare version decimals and prose hyphenations."""
    anchors: List[str] = []
    seen: set[str] = set()
    for is_bt, pat in ((True, BACKTICK_SPAN_RE), (True, CLI_FLAG_RE), (False, IDENT_RE)):
        for m in pat.finditer(text):
            raw_v = (m.group(1) if m.lastindex else m.group(0)).strip()
            val = raw_v.lower()
            if len(val) < 2 or len(val) > 72 or val in seen or val in _CODE_ANCHOR_NOISE:
                continue
            if not re.search(r"[a-z]{2,}", val):
                continue
            if re.fullmatch(r"v?\d+(?:\.\d+)+(?:[a-z0-9.-]*)?", val):
                continue
            if not is_bt and "-" in val and "_" not in val and not val.startswith("--"):
                parts = [p for p in val.split("-") if p]
                if parts and (parts[0] in _PROSE_HYPHEN_PREFIXES or all(p.isalpha() for p in parts)):
                    continue
            if is_bt and " " in val and not any(ch in val for ch in ("(", ".", "_", "/", "=")):
                continue
            seen.add(val)
            anchors.append(val)
    return anchors


def compute_lexical_scores(chunks: Sequence[Dict[str, Any]], query_text: str) -> List[float]:
    """Compute calibrated [0.0, 1.0] lexical relevance using BM25 + code anchors + Thai 3-grams."""
    if not chunks or not query_text.strip():
        return [0.0] * len(chunks)

    q_tokens = _extract_lexical_tokens(query_text)
    q_unique = list(dict.fromkeys(q_tokens))
    q_anchors = _extract_technical_anchors(query_text)

    if not q_unique and not q_anchors:
        return [0.0] * len(chunks)

    n_docs = len(chunks)
    doc_counters: List[Counter[str]] = []
    doc_lengths: List[int] = []
    df: Counter[str] = Counter()

    for ch in chunks:
        toks = _extract_lexical_tokens(ch["text"])
        cnt = Counter(toks)
        doc_counters.append(cnt)
        doc_lengths.append(max(1, len(toks)))
        for qt in q_unique:
            if qt in cnt:
                df[qt] += 1

    avgdl = sum(doc_lengths) / max(1, n_docs)
    k1 = 1.5
    b = 0.75

    idfs: Dict[str, float] = {
        qt: math.log(1.0 + (n_docs - df[qt] + 0.5) / (df[qt] + 0.5))
        for qt in q_unique
    }
    theoretical_max = sum(idfs[qt] * (k1 + 1.0) for qt in q_unique)

    raw_bm25: List[float] = []
    anchor_ratios: List[float] = []

    for ch, cnt, dl in zip(chunks, doc_counters, doc_lengths):
        score = 0.0
        for qt in q_unique:
            tf = cnt.get(qt, 0)
            if tf > 0:
                denom = tf + k1 * (1.0 - b + b * (dl / avgdl))
                score += idfs[qt] * ((tf * (k1 + 1.0)) / denom)
        raw_bm25.append(score)

        if q_anchors:
            ch_low = ch["text"].lower()
            hits = sum(1 for a in q_anchors if a in ch_low)
            anchor_ratios.append(hits / len(q_anchors))
        else:
            anchor_ratios.append(0.0)

    max_observed = max(raw_bm25) if raw_bm25 else 0.0
    norm_denom = max(max_observed, theoretical_max * 0.40, 1e-6)

    scores: List[float] = []
    for bm, ar in zip(raw_bm25, anchor_ratios):
        bm_norm = min(1.0, bm / norm_denom) if theoretical_max > 0 else 0.0
        if q_anchors:
            blended = min(1.0, 0.72 * bm_norm + 0.28 * ar)
        else:
            blended = bm_norm
        scores.append(round(blended, 4))
    return scores


# ---------------------------------------------------------------------------
# Stage 0+: Evolved 8-Feature Code-Graph Matrix Sieve (v2.2.0, Zero Torch Dep)
# ---------------------------------------------------------------------------

_TRACEBACK_LINE_RE = re.compile(
    r'(?:file\s+"?([^"\n]+\.[a-z0-9]{1,5})"?\s*,\s*line\s+(\d+))|'
    r"\b([A-Za-z0-9_./\\-]+\.[a-z0-9]{1,5})(?::|#L)(\d+)\b",
    re.IGNORECASE,
)
_EXCEPTION_TOKEN_RE = re.compile(r"\b([A-Z][A-Za-z0-9]*(?:Error|Exception|Warning|Timeout|Fault))\b")
_TEST_PATH_MARKERS = ("/tests/", "/test/", "\\tests\\", "\\test\\", "conftest.py")


def project_sieve_weights_simplex(weights: Sequence[float]) -> List[float]:
    """Project an 8-element weight vector onto the sign-constrained L1 simplex (sum(|w|)=1, w_6<=0)."""
    if len(weights) != len(SIEVE_FEATURE_NAMES):
        raise ValueError(
            f"Expected {len(SIEVE_FEATURE_NAMES)} sieve weights, got {len(weights)}."
        )
    constrained: List[float] = []
    for idx, val in enumerate(weights):
        fval = float(val)
        if not math.isfinite(fval):
            fval = 0.0
        if idx in SIEVE_NEG_INDICES:
            constrained.append(min(0.0, fval))
        else:
            constrained.append(max(0.0, fval))
    l1_norm = sum(abs(x) for x in constrained)
    if l1_norm < 1e-12:
        fallback = DEFAULT_SIEVE_GENOMES["e4b_sniper_distilled"]["w_core"]
        fb_norm = sum(abs(float(x)) for x in fallback)
        return [round(float(x) / fb_norm, 6) for x in fallback]
    return [round(x / l1_norm, 6) for x in constrained]


def load_sieve_genomes(
    sieve_weights: Optional[Union[str, Path, Mapping[str, Any]]] = None,
) -> Tuple[Dict[str, Any], str]:
    """Load evolved JSON sieve genomes from dict, explicit path, co-located policies/, or builtin default."""
    if isinstance(sieve_weights, Mapping):
        return dict(sieve_weights), "in_memory_dict"

    cand_paths: List[Path] = []
    raw_arg = str(sieve_weights).strip() if sieve_weights is not None else ""
    if not raw_arg:
        raw_arg = os.environ.get("XLAYA_SIEVE_WEIGHTS", "").strip()
    if raw_arg:
        p = Path(raw_arg)
        if not p.is_file():
            raise ValueError(f"Sieve weights JSON file not found: {raw_arg}")
        cand_paths.append(p)
    else:
        here = Path(__file__).resolve().parent
        cand_paths.extend(
            [
                here / "policies" / "sieve_genomes.json",
                here.parent / "policies" / "sieve_genomes.json",
                here.parent / "assets" / "sieve_genomes.json",
                here / "assets" / "sieve_genomes.json",
                here.parent / "resources" / "sieve_genomes.json",
                here / "resources" / "sieve_genomes.json",
            ]
        )

    for cp in cand_paths:
        if cp.is_file():
            data = json.loads(cp.read_text(encoding="utf-8"))
            if isinstance(data, dict) and ("e4b_sniper_distilled" in data or "w_core" in data):
                return data, f"file:{cp.name}"
    return dict(DEFAULT_SIEVE_GENOMES), "builtin_default"


def _hashed_256d_vec(text: str) -> List[float]:
    """Deterministic L2-normalized 256D signed subword/identifier sketch (zero external dependencies)."""
    vec = [0.0] * 256
    low = text.lower()
    tokens = LATIN_TOKEN_RE.findall(low)
    crc32 = zlib.crc32
    has_any = False

    for tok in tokens[:128]:
        if len(tok) < 2 or tok in STOPWORDS:
            continue
        has_any = True
        h = crc32(b"w:" + tok.encode("ascii", errors="ignore"))
        vec[h & 0xFF] += 1.5 if ((h >> 8) & 1) == 0 else -1.5
        if len(tok) >= 5:
            tb = tok.encode("ascii", errors="ignore")
            limit = min(len(tb) - 3, 6)
            for i in range(limit):
                end_i = i + 4
                hg = crc32(tb[i:end_i], 0x9E37)
                vec[hg & 0xFF] += 0.65 if ((hg >> 8) & 1) == 0 else -0.65

    for ident in IDENT_RE.findall(text)[:48]:
        has_any = True
        hi = crc32(b"id:" + ident.lower().encode("ascii", errors="ignore"))
        vec[hi & 0xFF] += 2.0 if ((hi >> 8) & 1) == 0 else -2.0

    if not has_any:
        return vec

    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 1e-12:
        inv = 1.0 / norm
        return [v * inv for v in vec]
    return vec


def _cosine_256d(va: Sequence[float], vb: Sequence[float]) -> float:
    dot = sum(a * b for a, b in zip(va, vb))
    return max(0.0, min(1.0, dot))


def _span_iou(ch_a: Mapping[str, Any], ch_b: Mapping[str, Any]) -> float:
    if ch_a.get("file") != ch_b.get("file"):
        return 0.0
    a0, a1 = int(ch_a.get("start_line", 1)), int(ch_a.get("end_line", 1))
    b0, b1 = int(ch_b.get("start_line", 1)), int(ch_b.get("end_line", 1))
    inter = max(0, min(a1, b1) - max(a0, b0) + 1)
    if inter <= 0:
        return 0.0
    union = max(1, (a1 - a0 + 1) + (b1 - b0 + 1) - inter)
    return inter / union


def _split_ident_parts(raw: str) -> List[str]:
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", raw)
    return [p.lower() for p in re.split(r"[^A-Za-z0-9]+", spaced) if len(p) >= 3]


def _is_same_symbol_or_overlap(ch_a: Mapping[str, Any], ch_b: Mapping[str, Any]) -> bool:
    """Guard against split-subchunk self-echo on the same AST symbol or overlapping line span."""
    if _span_iou(ch_a, ch_b) > 0.30:
        return True
    if ch_a.get("file") != ch_b.get("file"):
        return False
    ma = ch_a.get("_ast_meta") or {}
    mb = ch_b.get("_ast_meta") or {}
    sa = str(ma.get("canonical_symbol") or ma.get("symbol") or "").strip()
    sb = str(mb.get("canonical_symbol") or mb.get("symbol") or "").strip()
    if sa and sb and sa != "<module>" and sa == sb:
        return True
    return False


def _is_tier2_aux_relpath(rel_posix: str) -> bool:
    parts = [p.lower() for p in rel_posix.replace("\\", "/").split("/") if p]
    if any(p in _TIER2_AUX_DIRS for p in parts[:-1]):
        return True
    fname = parts[-1] if parts else ""
    return fname.startswith("test_") or fname.endswith("_test.py") or fname == "conftest.py"


_PRERANK_FILE_TOKEN_CACHE: Dict[str, Tuple[frozenset[str], frozenset[str]]] = {}


def _select_file_top_chunks(
    chs: List[Dict[str, Any]],
    query: str,
    limit: int,
) -> List[Dict[str, Any]]:
    if limit <= 0 or len(chs) <= limit:
        return chs
    q_toks = {t for t in _extract_lexical_tokens(query) if len(t) >= 3}
    q_ancs = _extract_code_anchors(query)
    tb_lines: set[int] = set()
    for m in _TRACEBACK_LINE_RE.finditer(query):
        ln_s = m.group(2) or m.group(4)
        if ln_s and ln_s.isdigit():
            tb_lines.add(int(ln_s))
    scored: List[Tuple[float, int]] = []
    for idx_c, c in enumerate(chs):
        sc = 0.0
        s_ln = int(c.get("start_line", 0))
        e_ln = int(c.get("end_line", 0))
        if tb_lines and any(s_ln <= tl <= e_ln for tl in tb_lines):
            sc += 120.0
        meta = c.get("_ast_meta") or {}
        sym_low = str(meta.get("symbol") or "").lower()
        if sym_low:
            if sym_low in q_ancs:
                sc += 25.0
            sym_parts = {sym_low} | set(_split_ident_parts(sym_low))
            sc += 4.5 * len(q_toks & sym_parts)
        txt_low = str(c.get("text") or "").lower()
        for qt in q_toks:
            if qt in txt_low:
                sc += 1.0
        scored.append((-sc, idx_c))
    scored.sort()
    keep_idxs = sorted(idx_c for _, idx_c in scored[:limit])
    return [chs[i] for i in keep_idxs]


def _prerank_repo_files(
    files: Sequence[Path],
    scan_root: Optional[Path],
    query: str,
) -> List[Path]:
    """
    2-Tier Source-First Lexical Pre-Ranker (F-08):
      - Returns `files` untouched when 0 `.py`/`.pyi` files exist (preserving .md/.json parity).
      - Prioritizes Tier-1 core package modules over Tier-2 `docs_src/`, `tests/`, `examples/`, `scripts/`,
        while promoting explicitly referenced or high-overlap Tier-2 files so `max_chunks` never starves core source.
    """
    py_exts = (".py", ".pyi")
    if len(files) <= 48 or not any(f.suffix.lower() in py_exts for f in files):
        return list(files)

    q_low = query.lower()
    q_toks = list(dict.fromkeys(_extract_lexical_tokens(query)))
    q_ancs = _extract_code_anchors(query)
    tb_files: set[str] = set()
    for m in _TRACEBACK_LINE_RE.finditer(query):
        rf = (m.group(1) or m.group(3) or "").replace("\\", "/").lower()
        if rf:
            tb_files.add(rf)
    for m_f in re.finditer(r"\b([A-Za-z0-9_./\\-]+\.(?:py|pyi))\b", query):
        tb_files.add(m_f.group(1).replace("\\", "/").lower())

    wants_docs = any(k in q_low for k in ("docs_src", "tutorial", "example", "docs/"))
    wants_scripts = any(
        k in q_low
        for k in ("scripts/", "prepare_release", "release notes", "bump version", "mkdocs", "build script")
    )
    wants_tests = any(k in q_low for k in ("pytest", "conftest", "unit test", "test_", "_test.py"))

    q_set = {t for t in q_toks if len(t) >= 3}
    wants_rubi = "rubi" in q_low
    tier1_candidates: List[Tuple[int, Path, str, set[str], set[str], set[str]]] = []
    tier2_scored: List[Tuple[float, int, Path]] = []
    other_files: List[Path] = []
    df_t1: Counter[str] = Counter()

    need_head_scan = len(files) > 90
    if len(_PRERANK_FILE_TOKEN_CACHE) > 16384:
        _PRERANK_FILE_TOKEN_CACHE.clear()

    for idx_f, fp in enumerate(files):
        if fp.suffix.lower() not in py_exts:
            other_files.append(fp)
            continue
        rel = _rel_ref_prefix(fp, scan_root).replace("\\", "/")
        rel_clean = rel[4:] if rel.startswith("src/") else rel
        rel_low = rel_clean.lower()
        is_t2 = _is_tier2_aux_relpath(rel_clean)
        path_toks = set(_extract_lexical_tokens(rel_clean.replace("/", " ").replace(".", " "))) & q_set

        if is_t2:
            sc = 0.0
            for tf in tb_files:
                if rel_low.endswith(tf) or fp.name.lower() == tf:
                    sc += 60.0
            if path_toks:
                sc += 5.5 * len(path_toks)
            for anc in q_ancs:
                if anc in rel_low:
                    sc += 8.0
            do_t2_head = need_head_scan and (
                sc > 0.0
                or (wants_scripts and ("scripts/" in rel_low or "devtools/" in rel_low))
                or (wants_docs and ("docs_src/" in rel_low or "examples/" in rel_low))
            )
            if do_t2_head and q_set:
                ckey_t2 = f"t2:{fp}"
                t2_toks = _PRERANK_FILE_TOKEN_CACHE.get(ckey_t2)
                if t2_toks is None:
                    try:
                        with fp.open("rb") as fh:
                            head_txt = fh.read(6144).decode("utf-8", errors="ignore")
                        t2_toks = (frozenset(_extract_lexical_tokens(head_txt)), frozenset())
                        _PRERANK_FILE_TOKEN_CACHE[ckey_t2] = t2_toks
                    except OSError:
                        t2_toks = (frozenset(), frozenset())
                sc += 1.35 * len(q_set & t2_toks[0])
            if wants_scripts and ("scripts/" in rel_low or "devtools/" in rel_low):
                sc += 18.0
            if wants_docs and ("docs_src/" in rel_low or "examples/" in rel_low):
                sc += 14.0
            if wants_tests and ("test" in rel_low):
                sc += 14.0
            tier2_scored.append((-sc, idx_f, fp))
        else:
            head_hits: set[str] = set()
            def_hits: set[str] = set()
            if need_head_scan and q_set and (wants_rubi or "integrals/rubi/" not in rel_low):
                ckey = str(fp)
                cached_pair = _PRERANK_FILE_TOKEN_CACHE.get(ckey)
                if cached_pair is None:
                    try:
                        with fp.open("rb") as fh:
                            head_txt = fh.read(20480).decode("utf-8", errors="ignore")
                        h_all = frozenset(_extract_lexical_tokens(head_txt))
                        d_all: set[str] = set()
                        for dm in re.finditer(
                            r"(?:^|\n)\s*(?:async\s+def|def|class)\s+([A-Za-z_][A-Za-z0-9_]*)", head_txt
                        ):
                            sym_nm = dm.group(1)
                            d_all.update({sym_nm.lower()} | set(_split_ident_parts(sym_nm)))
                        cached_pair = (h_all, frozenset(d_all))
                        _PRERANK_FILE_TOKEN_CACHE[ckey] = cached_pair
                    except OSError:
                        cached_pair = (frozenset(), frozenset())
                head_hits = q_set & cached_pair[0]
                def_hits = q_set & cached_pair[1]
            for qt in (path_toks | head_hits | def_hits):
                df_t1[qt] += 1
            tier1_candidates.append((idx_f, fp, rel_low, path_toks, head_hits, def_hits))

    n_t1 = max(1, len(tier1_candidates))
    idf_t1 = {qt: math.log(1.4 + n_t1 / (1.0 + df_t1[qt])) for qt in q_set}

    tier1_scored: List[Tuple[float, int, Path]] = []
    for idx_f, fp, rel_low, path_toks, head_hits, def_hits in tier1_candidates:
        sc = 1.5 if fp.name != "__init__.py" else 0.0
        if not wants_rubi and "integrals/rubi/" in rel_low:
            sc -= 15.0
        for tf in tb_files:
            if rel_low.endswith(tf) or fp.name.lower() == tf:
                sc += 65.0
        for anc in q_ancs:
            if anc in rel_low:
                sc += 9.0
        for qt in path_toks:
            sc += 3.8 * idf_t1.get(qt, 1.0)
        for qt in def_hits:
            sc += 3.2 * idf_t1.get(qt, 1.0)
        for qt in head_hits:
            sc += 1.15 * idf_t1.get(qt, 1.0)
        tier1_scored.append((-sc, idx_f, fp))

    tier1_scored.sort()
    tier2_scored.sort()

    # Interleave any explicitly high-scoring Tier-2 files (e.g. scripts/prepare_release.py or tutorial target)
    promoted_t2 = [fp for neg_sc, _, fp in tier2_scored if (-neg_sc) >= 12.0][:24]
    prom_set = set(promoted_t2)
    rem_t2_cap = 8 if len(tier1_scored) >= 40 else 48
    rem_t2 = [fp for _, _, fp in tier2_scored if fp not in prom_set][:rem_t2_cap]
    ordered_t1 = [fp for _, _, fp in tier1_scored]

    if promoted_t2:
        top_t1 = ordered_t1[:32]
        rest_t1 = ordered_t1[32:]
        return top_t1 + promoted_t2 + rest_t1 + rem_t2 + other_files
    return ordered_t1 + rem_t2 + other_files


def _whiten_symbol_vectors(raw_map: Mapping[str, Any]) -> Tuple[Dict[str, List[float]], float]:
    """
    All-but-the-Mean + 5-step Top-1 Principal Component whitening (F-02 / F-11):
    Collapses narrow-cone anisotropy (`rand_cos_p50 = 0.83..0.94 -> ~0.0`) and returns
    L2-normalized whitened vectors plus adaptive random-pair p75 floor.
    """
    keys = [k for k in raw_map.keys() if k != "__query__"]
    if not keys:
        return {}, 0.15

    # Fast numpy path when available (e.g. when loading .npz), with pure-Python fallback
    np_mod = sys.modules.get("numpy")
    if np_mod is None and len(keys) > 64:
        with contextlib.suppress(ImportError):
            import numpy as np_mod  # type: ignore

    if np_mod is not None:
        arr = np_mod.asarray([raw_map[k] for k in keys], dtype=np_mod.float32)
        if arr.ndim != 2 or arr.shape[0] < 2 or arr.shape[1] < 2:
            return {k: [float(x) for x in raw_map[k]] for k in keys}, 0.15
        mu = arr.mean(axis=0, keepdims=True)
        xc = arr - mu
        # 5 deterministic power-iteration steps for Top-1 PC u_1
        u = xc[0].copy()
        u_norm = float(np_mod.linalg.norm(u))
        if u_norm < 1e-8:
            u = np_mod.ones((arr.shape[1],), dtype=np_mod.float32)
            u_norm = float(np_mod.linalg.norm(u))
        u = u / u_norm
        xw = xc
        for pc_idx in range(min(4, xc.shape[0] - 1)):
            u = xw[min(pc_idx, xw.shape[0] - 1)].copy()
            un0 = float(np_mod.linalg.norm(u))
            if un0 < 1e-8:
                break
            u = u / un0
            for _ in range(6):
                proj = xw @ u
                u_new = xw.T @ proj
                un = float(np_mod.linalg.norm(u_new))
                if un < 1e-8:
                    break
                u = u_new / un
            if float(u[0]) < 0.0:
                u = -u
            xw = xw - np_mod.outer(xw @ u, u)
        norms = np_mod.linalg.norm(xw, axis=1, keepdims=True)
        xw = xw / np_mod.maximum(norms, 1e-8)

        n_v = xw.shape[0]
        step = max(1, n_v // 128)
        idx_a = np_mod.arange(0, n_v - 1, step)[:128]
        idx_b = (idx_a + max(1, n_v // 3)) % n_v
        sample_cos = np_mod.sum(xw[idx_a] * xw[idx_b], axis=1)
        p75 = float(np_mod.percentile(sample_cos, 75)) if sample_cos.size > 0 else 0.10
        floor_c = max(0.08, min(0.35, p75))
        return {keys[i]: xw[i].tolist() for i in range(n_v)}, floor_c

    # Pure-stdlib fallback for small in-memory dicts without numpy
    vecs = [[float(x) for x in raw_map[k]] for k in keys]
    dim = len(vecs[0])
    n_v = len(vecs)
    if n_v < 2 or dim < 2:
        return {keys[i]: vecs[i] for i in range(n_v)}, 0.15
    mu_l = [sum(v[d] for v in vecs) / n_v for d in range(dim)]
    xw_l = [[v[d] - mu_l[d] for d in range(dim)] for v in vecs]
    for pc_idx in range(min(4, n_v - 1)):
        u_l = list(xw_l[min(pc_idx, n_v - 1)])
        un = math.sqrt(sum(x * x for x in u_l)) or 1.0
        u_l = [x / un for x in u_l]
        for _ in range(6):
            proj_l = [sum(v[d] * u_l[d] for d in range(dim)) for v in xw_l]
            u_next = [sum(xw_l[i][d] * proj_l[i] for i in range(n_v)) for d in range(dim)]
            un2 = math.sqrt(sum(x * x for x in u_next))
            if un2 < 1e-8:
                break
            u_l = [x / un2 for x in u_next]
        if u_l[0] < 0.0:
            u_l = [-x for x in u_l]
        for i in range(n_v):
            dot_u = sum(xw_l[i][d] * u_l[d] for d in range(dim))
            xw_l[i] = [xw_l[i][d] - dot_u * u_l[d] for d in range(dim)]
    out_map: Dict[str, List[float]] = {}
    for i, k in enumerate(keys):
        nrm = math.sqrt(sum(x * x for x in xw_l[i])) or 1.0
        out_map[k] = [x / nrm for x in xw_l[i]]
    return out_map, 0.12


def _match_chunks_to_symbol_keys(
    chunks: Sequence[Mapping[str, Any]],
    available_keys: Sequence[str],
) -> List[Optional[str]]:
    """Map AST chunks to dotted symbol keys without smearing `<module>` vectors onto functions/classes."""
    key_set = set(available_keys)
    exact_tail_cs: Dict[str, List[str]] = {}
    exact_tail_low: Dict[str, List[str]] = {}
    mod_keys_low: Dict[str, str] = {}

    for k in available_keys:
        if k == "__query__":
            continue
        if k.endswith(".<module>") or k == "<module>":
            mod_keys_low[k[:-9].lower() if k.endswith(".<module>") else ""] = k
            continue
        parts = k.split(".")
        for n_tail in (1, 2, 3):
            if len(parts) >= n_tail:
                t_cs = ".".join(parts[-n_tail:])
                exact_tail_cs.setdefault(t_cs, []).append(k)
                exact_tail_low.setdefault(t_cs.lower(), []).append(k)

    def _pick_best_key(cands: List[str], mod_dotted_low: str) -> Optional[str]:
        if not cands:
            return None
        if len(cands) == 1:
            return cands[0]
        for c in cands:
            cl = c.lower()
            if mod_dotted_low and cl.startswith(mod_dotted_low + "."):
                return c
        core_cands = [
            c
            for c in cands
            if not any(
                seg in c.lower().split(".")
                for seg in ("docs_src", "tests", "test", "examples", "tutorials")
            )
        ]
        pool = core_cands or cands
        return pool[0] if len(pool) <= 6 else None

    matched: List[Optional[str]] = []
    for ch in chunks:
        ref_str = str(ch.get("ref", ""))
        if ref_str in key_set:
            matched.append(ref_str)
            continue
        meta = ch.get("_ast_meta") or {}
        csym = str(meta.get("canonical_symbol") or meta.get("symbol") or "").strip()
        rel_file = ref_str.split("#", 1)[0].replace("\\", "/")
        if rel_file.startswith("src/"):
            rel_file = rel_file[4:]
        mod_dotted = re.sub(r"\.(?:py|pyi)$", "", rel_file).replace("/", ".")
        if mod_dotted.endswith(".__init__"):
            mod_dotted = mod_dotted[:-9]
        mod_low = mod_dotted.lower()

        if not csym or csym == "<module>":
            matched.append(mod_keys_low.get(mod_low))
            continue

        full_cand = f"{mod_dotted}.{csym}" if mod_dotted else csym
        if full_cand in key_set:
            matched.append(full_cand)
            continue
        picked = _pick_best_key(exact_tail_cs.get(csym, []), mod_low)
        if picked is None:
            picked = _pick_best_key(exact_tail_low.get(csym.lower(), []), mod_low)
        matched.append(picked)
    return matched


def extract_code_graph_features(
    chunks: Sequence[Dict[str, Any]],
    query: str,
    *,
    graph_path: Optional[Union[str, Path]] = None,
    embeddings_path: Optional[Union[str, Path, Mapping[str, Any]]] = None,
    out_stats: Optional[Dict[str, Any]] = None,
) -> List[List[float]]:
    """Compute the normalized [M x 8] cross-regime feature matrix F in [0, 1] across candidate chunks."""
    m_len = len(chunks)
    if m_len == 0:
        return []
    if not query.strip():
        return [[0.0] * 8 for _ in range(m_len)]

    q_low = query.lower()
    q_tokens = _extract_lexical_tokens(query)
    q_unique = list(dict.fromkeys(q_tokens))
    q_anchors = _extract_code_anchors(query)
    q_ident_stems: set[str] = set()
    for anc in q_anchors:
        q_ident_stems.add(anc)
        for pt in _split_ident_parts(anc):
            if pt not in STOPWORDS:
                q_ident_stems.add(pt)
    for qt in q_unique:
        if len(qt) >= 4:
            q_ident_stems.add(qt)

    q_wants_tests = any(w in q_low for w in ("pytest", "conftest", "unit test", "test_", "_test.py"))
    # Exclude generic English "stream" so OOD prompts never trigger hallucinated async boosts
    async_kws = (
        "astream", "async", "await", "coroutine", "depends", "dependency",
        "lifespan", "middleware", "asgi",
    )
    q_wants_async = any(w in q_low for w in async_kws)
    q_exceptions = {m.group(1).lower() for m in _EXCEPTION_TOKEN_RE.finditer(query)}
    tb_refs: List[Tuple[str, Optional[int]]] = []
    for m in _TRACEBACK_LINE_RE.finditer(query):
        if m.group(1):
            tb_refs.append((m.group(1).replace("\\", "/").lower(), int(m.group(2))))
        elif m.group(3):
            tb_refs.append((m.group(3).replace("\\", "/").lower(), int(m.group(4))))
    for m_file in re.finditer(r"\b([A-Za-z0-9_./\\-]+\.(?:py|pyi|toml|yaml|yml|md))\b", query):
        cand_f = m_file.group(1).replace("\\", "/").lower()
        if not any(cand_f == x[0] for x in tb_refs):
            tb_refs.append((cand_f, None))

    # Pre-classify test & Tier-2 chunks first so max_bm normalization is strictly immune to test-echo crushing
    f_test: List[float] = []
    is_tier2_chunk: List[bool] = []
    for ch in chunks:
        fpath_low = str(ch.get("file", "")).lower()
        fname_low = str(ch.get("name", "")).lower()
        ref_rel = str(ch.get("ref", "")).split("#", 1)[0]
        is_test = (
            fname_low.startswith("test_")
            or fname_low.endswith("_test.py")
            or any(mk in fpath_low for mk in _TEST_PATH_MARKERS)
        )
        f_test.append(1.0 if (is_test and not q_wants_tests) else 0.0)
        is_tier2_chunk.append(is_test or _is_tier2_aux_relpath(ref_rel))

    # Pass 1: Sub-token counters (reused by both Feature 0 BM25 and Feature 5 pure-stdlib Corpus-IDF)
    doc_counters: List[Counter[str]] = []
    doc_lengths: List[int] = []
    df: Counter[str] = Counter()
    for ch in chunks:
        toks = _extract_lexical_tokens(ch["text"])
        cnt = Counter(toks)
        doc_counters.append(cnt)
        doc_lengths.append(max(1, len(toks)))
        for qt in q_unique:
            if qt in cnt:
                df[qt] += 1

    avgdl = sum(doc_lengths) / max(1, m_len)
    k1, b_param = 1.5, 0.75
    idfs = {qt: math.log(1.0 + (m_len - df[qt] + 0.5) / (df[qt] + 0.5)) for qt in q_unique}
    theo_max = sum(idfs[qt] * (k1 + 1.0) for qt in q_unique)

    raw_bm25: List[float] = []
    f_ident: List[float] = []
    for ch, cnt, dl in zip(chunks, doc_counters, doc_lengths):
        sc = 0.0
        for qt in q_unique:
            tf = cnt.get(qt, 0)
            if tf > 0:
                sc += idfs[qt] * ((tf * (k1 + 1.0)) / (tf + k1 * (1.0 - b_param + b_param * (dl / avgdl))))
        raw_bm25.append(sc)

        ch_low = ch["text"].lower()
        ref_low = str(ch.get("ref", "")).lower()
        anc_ratio = 0.0
        if q_anchors:
            exact_hits = sum(1 for a in q_anchors if a in ch_low or a in ref_low)
            anc_ratio = min(1.0, exact_hits / max(1, len(q_anchors)))
        stem_ratio = 0.0
        if q_ident_stems:
            stem_hits = sum(1 for st in q_ident_stems if st in cnt or st in ref_low)
            stem_ratio = min(1.0, stem_hits / max(1, len(q_ident_stems)))
        # Additive / non-exclusive fusion so 1 noisy backtick never zeroes structural stems (F-05)
        if q_anchors:
            f_ident.append(min(1.0, max(anc_ratio, 0.75 * stem_ratio)))
        else:
            f_ident.append(min(1.0, 0.85 * stem_ratio))

    non_test_bm = [raw_bm25[i] for i in range(m_len) if f_test[i] < 0.5]
    max_bm = max(non_test_bm) if non_test_bm else (max(raw_bm25) if raw_bm25 else 0.0)
    bm_denom = max(max_bm, theo_max * 0.40, 1e-6)
    f_bm25 = [min(1.0, bm / bm_denom) if theo_max > 0 else 0.0 for bm in raw_bm25]

    # Feature 2 (ast_enclosing_def) & Feature 7 (traceback_line_boost)
    f_ast: List[float] = []
    f_tb: List[float] = []

    sym_to_chunks: Dict[str, List[int]] = {}
    mod_to_chunks: Dict[str, List[int]] = {}

    for idx, ch in enumerate(chunks):
        meta = ch.get("_ast_meta") or {}
        defined = meta.get("defined_symbols") or []
        params = meta.get("param_and_ann_tokens") or []
        async_di = meta.get("async_or_di_symbols") or []
        exc_list = meta.get("raised_exceptions") or []
        kind = meta.get("node_kind", "")

        mod_stem = Path(str(ch.get("name", ""))).stem.lower()
        if mod_stem and mod_stem != "__init__":
            mod_to_chunks.setdefault(mod_stem, []).append(idx)
        for d_sym in defined:
            if len(d_sym) >= 3 and d_sym not in ("__init__", "main", "<module>"):
                sym_to_chunks.setdefault(d_sym, []).append(idx)

        ast_val = 0.0
        if defined and q_ident_stems:
            for d_sym in defined:
                d_parts = set(_split_ident_parts(d_sym)) | {d_sym}
                if d_sym in q_ident_stems:
                    ast_val = max(ast_val, 1.0)
                elif d_parts & q_ident_stems:
                    ast_val = max(ast_val, 0.72)
        if ast_val < 0.70 and params and q_ident_stems:
            p_hits = sum(1 for p in params if p in q_ident_stems)
            if p_hits > 0:
                ast_val = max(ast_val, min(0.70, 0.35 + 0.18 * p_hits))
        if q_wants_async and (kind == "async_def" or async_di):
            ast_val = min(1.0, ast_val + 0.25)
        f_ast.append(ast_val)

        fpath_low = str(ch.get("file", "")).lower()
        fname_low = str(ch.get("name", "")).lower()
        tb_val = 0.0
        s_ln = int(ch.get("start_line", 1))
        e_ln = int(ch.get("end_line", 1))
        ref_prefix_low = str(ch.get("ref", "")).split("#", 1)[0].lower()
        for ref_f, ref_ln in tb_refs:
            if fpath_low.endswith(ref_f) or ref_prefix_low.endswith(ref_f) or fname_low == ref_f:
                if ref_ln is not None and (s_ln - 5) <= ref_ln <= (e_ln + 5):
                    tb_val = max(tb_val, 1.0)
                else:
                    tb_val = max(tb_val, 0.75)
        if tb_val < 0.55 and q_exceptions and exc_list:
            if set(exc_list) & q_exceptions:
                tb_val = max(tb_val, 0.55)
        f_tb.append(tb_val)

    # Build static AST 1-hop call/import graph (call_adj) & 2-hop async/Depends graph (async_adj),
    # keeping external NetworkX node_link_data graphs STRICTLY ISOLATED in ext_call_adj (F-01 / F-11)
    call_adj: List[set[int]] = [set() for _ in range(m_len)]
    ext_call_adj: List[set[int]] = [set() for _ in range(m_len)]
    async_adj: List[set[int]] = [set() for _ in range(m_len)]
    ext_edges_matched = 0

    if graph_path is not None and str(graph_path).strip():
        gp = Path(str(graph_path))
        if gp.is_file():
            try:
                g_data = json.loads(gp.read_text(encoding="utf-8"))
                edges_list = g_data.get("edges") or g_data.get("links") or []
                if edges_list:
                    sample_e = edges_list[0]
                    if "src" in sample_e and "dst" in sample_e:
                        ref_idx = {str(ch.get("ref", "")): i for i, ch in enumerate(chunks)}
                        for edge in edges_list:
                            u = ref_idx.get(str(edge.get("src", "")))
                            v = ref_idx.get(str(edge.get("dst", "")))
                            if u is not None and v is not None and u != v:
                                ext_call_adj[u].add(v)
                                ext_call_adj[v].add(u)
                                ext_edges_matched += 1
                                if edge.get("kind") in ("async", "depends", "di"):
                                    async_adj[u].add(v)
                                    async_adj[v].add(u)
                    else:
                        # NetworkX node_link_data schema:
                        # {"source": "<dotted.sym>", "target": "<dotted.sym>", "type": "calls"}
                        node_ids = [
                            str(n.get("id") or n.get("name") or "")
                            for n in (g_data.get("nodes") or [])
                            if (n.get("id") or n.get("name"))
                        ]
                        if not node_ids:
                            node_ids = list(
                                {
                                    str(edge.get("source", ""))
                                    for edge in edges_list
                                    if edge.get("source")
                                }
                                | {
                                    str(edge.get("target", ""))
                                    for edge in edges_list
                                    if edge.get("target")
                                }
                            )
                        chunk_gkeys = _match_chunks_to_symbol_keys(chunks, node_ids)
                        gkey_to_cidxs: Dict[str, List[int]] = {}
                        for ci, gk in enumerate(chunk_gkeys):
                            if gk and not gk.endswith(".<module>") and gk != "<module>":
                                gkey_to_cidxs.setdefault(gk, []).append(ci)
                        for edge in edges_list:
                            s_id = str(edge.get("source", ""))
                            t_id = str(edge.get("target", ""))
                            if not s_id or not t_id or s_id == t_id:
                                continue
                            u_list = gkey_to_cidxs.get(s_id)
                            v_list = gkey_to_cidxs.get(t_id)
                            if u_list and v_list and len(u_list) <= 4 and len(v_list) <= 4:
                                for ui in u_list:
                                    for vi in v_list:
                                        if not _is_same_symbol_or_overlap(chunks[ui], chunks[vi]):
                                            ext_call_adj[ui].add(vi)
                                            ext_call_adj[vi].add(ui)
                                            ext_edges_matched += 1
            except Exception:  # nosec B110
                pass

    for idx, ch in enumerate(chunks):
        meta = ch.get("_ast_meta") or {}
        for cal in meta.get("called_symbols") or []:
            cal_tail = cal.split(".")[-1]
            targets = sym_to_chunks.get(cal, []) or sym_to_chunks.get(cal_tail, [])
            if 0 < len(targets) <= 24:
                for tgt in targets:
                    if tgt != idx:
                        call_adj[idx].add(tgt)
                        call_adj[tgt].add(idx)
        for imp in meta.get("imported_symbols") or []:
            m_targets = sym_to_chunks.get(imp, []) or mod_to_chunks.get(imp, [])
            if 0 < len(m_targets) <= 16:
                for tgt in m_targets:
                    if tgt != idx:
                        call_adj[idx].add(tgt)
                        call_adj[tgt].add(idx)
        for adi in meta.get("async_or_di_symbols") or []:
            adi_tail = adi.split(".")[-1]
            a_targets = sym_to_chunks.get(adi, []) or sym_to_chunks.get(adi_tail, [])
            if 0 < len(a_targets) <= 24:
                for tgt in a_targets:
                    if tgt != idx:
                        async_adj[idx].add(tgt)
                        async_adj[tgt].add(idx)
        if meta.get("node_kind") == "async_def" or meta.get("raised_exceptions"):
            for exc_sym in meta.get("raised_exceptions") or []:
                e_targets = sym_to_chunks.get(exc_sym, [])
                if 0 < len(e_targets) <= 16:
                    for tgt in e_targets:
                        if tgt != idx:
                            async_adj[idx].add(tgt)
                            async_adj[tgt].add(idx)

    seeds = [
        min(1.0, 0.42 * f_bm25[i] + 0.30 * f_ident[i] + 0.42 * f_ast[i] + 0.25 * f_tb[i])
        for i in range(m_len)
    ]

    # Feature 3: Monotonic envelope of AST call graph + isolated external NetworkX graph
    f_hop1: List[float] = []
    for i in range(m_len):
        best_ast = 0.0
        for nb in call_adj[i]:
            if _is_same_symbol_or_overlap(chunks[i], chunks[nb]):
                continue
            damp = 1.0 / (1.0 + 0.12 * math.log1p(len(call_adj[nb])))
            cand = seeds[nb] * damp
            if cand > best_ast:
                best_ast = cand

        best_ext = 0.0
        if ext_call_adj[i]:
            t2_self = 0.35 if is_tier2_chunk[i] else 1.0
            for nb in ext_call_adj[i]:
                if _is_same_symbol_or_overlap(chunks[i], chunks[nb]):
                    continue
                t2_nb = 0.35 if is_tier2_chunk[nb] else 1.0
                damp_e = 1.0 / (1.0 + 0.14 * math.log1p(len(ext_call_adj[nb])))
                cand_e = seeds[nb] * damp_e * t2_self * t2_nb
                if cand_e > best_ext:
                    best_ext = cand_e

        ext_gain = 0.85 if max(f_bm25[i], f_ident[i], f_ast[i], f_tb[i]) >= 0.04 else 0.48
        f_hop1.append(min(1.0, max(best_ast, ext_gain * best_ext)))

    # Feature 4: Smooth hub-damped 2-hop async/Depends graph (zero discontinuous degree step cliffs)
    top16_call_nbs: List[List[int]] = [
        sorted(call_adj[i], key=lambda x: (-seeds[x], x))[:16] if call_adj[i] else []
        for i in range(m_len)
    ]
    f_hop2_async: List[float] = []
    for i in range(m_len):
        best_a1 = 0.0
        for nb in async_adj[i]:
            damp1 = 1.0 / (1.0 + 0.10 * math.log1p(len(async_adj[nb])))
            cand1 = seeds[nb] * damp1
            if cand1 > best_a1:
                best_a1 = cand1
            combined_2 = list(async_adj[nb]) + [x for x in top16_call_nbs[nb][:12] if x not in async_adj[nb]]
            for nb2 in combined_2:
                if nb2 == i:
                    continue
                damp2 = 1.0 / (1.0 + 0.14 * math.log1p(len(call_adj[nb2]) + len(async_adj[nb2])))
                cand2 = 0.82 * seeds[nb2] * damp1 * damp2
                if cand2 > best_a1:
                    best_a1 = cand2
        hub_damp_i = 1.0 / (1.0 + 0.10 * math.log1p(max(0, len(call_adj[i]) - 8)))
        for nb in top16_call_nbs[i]:
            for nb2 in async_adj[nb]:
                if nb2 == i:
                    continue
                damp2 = 1.0 / (1.0 + 0.14 * math.log1p(len(async_adj[nb2])))
                cand2 = 0.80 * seeds[nb2] * damp2 * hub_damp_i
                if cand2 > best_a1:
                    best_a1 = cand2
        f_hop2_async.append(min(1.0, best_a1))

    # Feature 5 (F-02 / F-11):
    #   (a) Universal pure-stdlib Corpus-IDF Sub-Token Cosine Seed Propagation (`f_5_tfidf`)
    #   (b) Monotonic All-but-the-Mean + Top-1 PC Whitened `.npz` Sidecar Upgrade (`max(f_5_tfidf, 0.85 * f_5_npz)`)
    seed_pool = [
        i
        for i in range(m_len)
        if f_test[i] < 0.5
        and not is_tier2_chunk[i]
        and max(f_bm25[i], f_ident[i], f_tb[i]) > 0.08
        and seeds[i] > 0.10
    ]
    if not seed_pool:
        seed_pool = [
            i
            for i in range(m_len)
            if f_test[i] < 0.5
            and max(f_bm25[i], f_ident[i], f_tb[i]) > 0.08
            and seeds[i] > 0.10
        ]
    seed_pool.sort(key=lambda idx: (-seeds[idx], idx))
    top_seeds: List[int] = []
    for cand_s in seed_pool:
        if any(_is_same_symbol_or_overlap(chunks[cand_s], chunks[ps]) for ps in top_seeds):
            continue
        top_seeds.append(cand_s)
        if len(top_seeds) >= 5:
            break

    peak_seed = seeds[top_seeds[0]] if top_seeds else 0.0
    f_5_tfidf = [0.0] * m_len

    if top_seeds and m_len >= 3:
        df_corpus: Counter[str] = Counter()
        for cnt in doc_counters:
            for tok in cnt:
                if len(tok) >= 3:
                    df_corpus[tok] += 1
        max_df = max(2, int(0.25 * m_len))
        idf_c: Dict[str, float] = {
            tok: math.log(1.0 + (m_len + 1.0) / (dfc + 1.0))
            for tok, dfc in df_corpus.items()
            if 2 <= dfc <= max_df
        }
        if idf_c:
            chunk_norms = [0.0] * m_len
            for ci, cnt in enumerate(doc_counters):
                sq = 0.0
                for tok, tfv in cnt.items():
                    w_idf = idf_c.get(tok)
                    if w_idf is not None:
                        wt = (1.0 + math.log(tfv)) * w_idf
                        sq += wt * wt
                chunk_norms[ci] = math.sqrt(sq)

            seed_vocab: set[str] = set()
            for s_idx in top_seeds:
                for tok in doc_counters[s_idx]:
                    if tok in idf_c:
                        seed_vocab.add(tok)

            postings: Dict[str, List[Tuple[int, float]]] = {}
            for ci, cnt in enumerate(doc_counters):
                if chunk_norms[ci] <= 1e-9:
                    continue
                for tok in cnt:
                    if tok in seed_vocab:
                        wt = (1.0 + math.log(cnt[tok])) * idf_c[tok]
                        postings.setdefault(tok, []).append((ci, wt))

            raw_prop = [0.0] * m_len
            for rank_s, s_idx in enumerate(top_seeds):
                nrm_s = chunk_norms[s_idx]
                if nrm_s <= 1e-9:
                    continue
                decay = 1.0 / (1.0 + 0.22 * rank_s)
                dots: Dict[int, float] = {}
                s_cnt = doc_counters[s_idx]
                for tok, tf_s in s_cnt.items():
                    if tok not in postings:
                        continue
                    w_s = (1.0 + math.log(tf_s)) * idf_c[tok]
                    for j_idx, w_j in postings[tok]:
                        if j_idx != s_idx:
                            dots[j_idx] = dots.get(j_idx, 0.0) + w_s * w_j
                s_file = chunks[s_idx].get("file")
                for j_idx, dot_val in dots.items():
                    if f_test[j_idx] >= 0.5 or _is_same_symbol_or_overlap(chunks[s_idx], chunks[j_idx]):
                        continue
                    cos_ij = dot_val / (nrm_s * chunk_norms[j_idx])
                    cos_pos = max(0.0, (cos_ij - 0.05) / 0.95)
                    if cos_pos <= 0.0:
                        continue
                    file_damp = 0.80 if chunks[j_idx].get("file") == s_file else 1.0
                    cand_v = seeds[s_idx] * decay * cos_pos * file_damp
                    if cand_v > raw_prop[j_idx]:
                        raw_prop[j_idx] = cand_v

            denom_tf = max(max(raw_prop, default=0.0), 0.28 * peak_seed, 1e-6)
            for j_idx in range(m_len):
                if raw_prop[j_idx] > 0.0:
                    f_5_tfidf[j_idx] = min(peak_seed, peak_seed * (raw_prop[j_idx] / denom_tf))

    # Optional precomputed embeddings upgrade (dict / .json / Kaggle symbol-keyed .npz / legacy refs+vectors .npz)
    raw_ext_embs: Optional[Dict[str, Any]] = None
    if isinstance(embeddings_path, Mapping):
        raw_ext_embs = dict(embeddings_path)
    elif embeddings_path is not None and str(embeddings_path).strip():
        ep = Path(str(embeddings_path))
        if ep.is_file() and ep.suffix.lower() == ".json":
            with contextlib.suppress(Exception):
                raw_ext_embs = json.loads(ep.read_text(encoding="utf-8"))
        elif ep.is_file() and ep.suffix.lower() == ".npz":
            try:
                import numpy as _np  # type: ignore

                with _np.load(str(ep), allow_pickle=False) as npz:
                    npz_files = list(npz.files)
                    if "refs" in npz_files and "vectors" in npz_files:
                        refs_arr = [str(r) for r in npz["refs"].tolist()]
                        vecs_arr = npz["vectors"]
                        raw_ext_embs = {r: vecs_arr[k] for k, r in enumerate(refs_arr)}
                    else:
                        raw_ext_embs = {k: npz[k] for k in npz_files if getattr(npz[k], "ndim", 0) == 1}
            except Exception:  # nosec B110
                raw_ext_embs = None

    npz_matched_cnt = 0
    f_emb = list(f_5_tfidf)
    if raw_ext_embs:
        if "__query__" in raw_ext_embs:
            q_vec = [float(x) for x in raw_ext_embs["__query__"]]
            for i, ch in enumerate(chunks):
                rk = str(ch.get("ref", ""))
                if rk in raw_ext_embs:
                    npz_matched_cnt += 1
                    f_emb[i] = max(f_5_tfidf[i], _cosine_256d(q_vec, raw_ext_embs[rk]))
        elif top_seeds:
            whitened_map, floor_c = _whiten_symbol_vectors(raw_ext_embs)
            matched_keys = _match_chunks_to_symbol_keys(chunks, list(whitened_map.keys()))
            npz_matched_cnt = sum(1 for mk in matched_keys if mk is not None)
            raw_npz = [0.0] * m_len
            denom_floor = max(0.15, 1.0 - floor_c)
            for rank_s, s_idx in enumerate(top_seeds):
                sk = matched_keys[s_idx]
                if sk is None:
                    continue
                sv = whitened_map[sk]
                decay = 1.0 / (1.0 + 0.22 * rank_s)
                s_file = chunks[s_idx].get("file")
                for j_idx in range(m_len):
                    jk = matched_keys[j_idx]
                    if (
                        jk is None
                        or j_idx == s_idx
                        or f_test[j_idx] >= 0.5
                        or _is_same_symbol_or_overlap(chunks[s_idx], chunks[j_idx])
                    ):
                        continue
                    jv = whitened_map[jk]
                    dot_w = sum(a * b for a, b in zip(sv, jv))
                    cos_clean = max(0.0, (dot_w - floor_c) / denom_floor)
                    if cos_clean <= 0.0:
                        continue
                    t2_damp = 0.45 if is_tier2_chunk[j_idx] else 1.0
                    file_damp = 0.80 if chunks[j_idx].get("file") == s_file else 1.0
                    cand_n = seeds[s_idx] * decay * cos_clean * file_damp * t2_damp
                    if cand_n > raw_npz[j_idx]:
                        raw_npz[j_idx] = cand_n
            denom_npz = max(max(raw_npz, default=0.0), 0.45 * peak_seed, 1e-6)
            for j_idx in range(m_len):
                if matched_keys[j_idx] is not None and raw_npz[j_idx] > 0.0:
                    f_5_npz_j = min(peak_seed, peak_seed * (raw_npz[j_idx] / denom_npz))
                    npz_gain = 0.85 if max(f_bm25[j_idx], f_ident[j_idx], f_ast[j_idx], f_tb[j_idx]) >= 0.04 else 0.48
                    f_emb[j_idx] = max(f_5_tfidf[j_idx], npz_gain * f_5_npz_j)

    if out_stats is not None:
        out_stats["external_graph_edges_matched"] = ext_edges_matched
        out_stats["npz_symbols_matched"] = npz_matched_cnt
        out_stats["top_seed_count"] = len(top_seeds)

    matrix: List[List[float]] = []
    for i in range(m_len):
        matrix.append(
            [
                round(f_bm25[i], 6),
                round(f_ident[i], 6),
                round(f_ast[i], 6),
                round(f_hop1[i], 6),
                round(f_hop2_async[i], 6),
                round(f_emb[i], 6),
                round(f_test[i], 6),
                round(f_tb[i], 6),
            ]
        )
    return matrix


def _platt_prob(raw_score: float, platt_t: float, platt_b: float) -> float:
    temp = max(1e-4, float(platt_t))
    z = max(-40.0, min(40.0, (float(raw_score) + float(platt_b)) / temp))
    return 1.0 / (1.0 + math.exp(-z))


def compute_channel_availability(
    chunks: Sequence[Mapping[str, Any]],
    feat_matrix: Sequence[Sequence[float]],
) -> List[float]:
    """
    Compute smooth realized channel availability M_avail in [0, 1]^8 (F-12):
    Prevents missing-sidecar / missing-traceback / symptom-only score starvation
    identically across CUDA evolution, Platt/conformal calibration, CLI, and Container A.
    """
    m_len = len(chunks)
    if m_len == 0 or not feat_matrix:
        return [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

    nt = [i for i in range(m_len) if feat_matrix[i][6] < 0.5]
    if not nt:
        nt = list(range(m_len))

    max_f1 = max((float(feat_matrix[i][1]) for i in nt), default=0.0)
    max_f2 = max((float(feat_matrix[i][2]) for i in nt), default=0.0)
    max_f3 = max((float(feat_matrix[i][3]) for i in nt), default=0.0)
    max_f4 = max((float(feat_matrix[i][4]) for i in nt), default=0.0)
    max_f5 = max((float(feat_matrix[i][5]) for i in nt), default=0.0)
    max_f7 = max((float(feat_matrix[i][7]) for i in nt), default=0.0)
    has_ast = any(bool(ch.get("_ast_meta")) for ch in chunks)

    return [
        1.0,
        round(0.25 + 0.75 * min(1.0, max_f1), 6),
        0.0 if not has_ast else round(0.25 + 0.75 * min(1.0, max_f2), 6),
        1.0 if max_f3 > 1e-6 else (0.15 if has_ast else 0.0),
        0.0 if not has_ast else (1.0 if max_f4 > 0.20 else (0.25 if max_f4 > 1e-6 else 0.0)),
        1.0 if (m_len >= 2 and max_f5 > 1e-6) else 0.0,
        1.0,
        1.0 if max_f7 >= 0.70 else (0.50 if max_f7 >= 0.50 else 0.0),
    ]


def apply_active_simplex_weights(
    weights: Sequence[float],
    m_avail: Sequence[float],
    gamma_max: float = 1.45,
) -> List[float]:
    """Renormalize positive simplex weights across realized channels with gain cap gamma_max."""
    w = project_sieve_weights_simplex(weights)
    pos_idxs = (0, 1, 2, 3, 4, 5, 7)
    w_pos_total = sum(max(0.0, w[d]) for d in pos_idxs)
    active_mass = sum(max(0.0, w[d]) * float(m_avail[d]) for d in pos_idxs)
    scale = min(float(gamma_max), w_pos_total / max(active_mass, 1e-8)) if active_mass > 1e-8 else 1.0
    return [
        w[6] if d == 6 else (max(0.0, w[d]) * float(m_avail[d]) * scale)
        for d in range(8)
    ]


def _chunk_total_est_tokens(ch: Mapping[str, Any]) -> int:
    meta = ch.get("_ast_meta") or {}
    skel = str(meta.get("skeleton_header") or "")
    txt = str(ch.get("text") or "")
    combined = f"{skel}\n{txt}" if (skel and skel not in txt) else txt
    return max(1, int(round(_estimate_tokens(combined))))


def _truncate_text_to_token_budget(text: str, budget_tokens: int) -> str:
    if budget_tokens <= 0:
        return ""
    if int(round(_estimate_tokens(text))) <= budget_tokens:
        return text
    kept: List[str] = []
    acc = 0.0
    for ln in text.splitlines():
        ln_t = _estimate_tokens(ln) + 0.3
        if kept and (acc + ln_t) > float(budget_tokens):
            break
        if not kept and ln_t > float(budget_tokens):
            char_cap = max(16, int(budget_tokens * 3.0))
            kept.append(ln[:char_cap])
            break
        kept.append(ln)
        acc += ln_t
    return "\n".join(kept)


def _auto_discover_sidecar_path(
    sidecar_arg: Optional[Union[str, Path, Mapping[str, Any]]],
    scan_root: Optional[Path],
    suffix: str,
) -> Optional[Union[str, Path, Mapping[str, Any]]]:
    if sidecar_arg is None or isinstance(sidecar_arg, Mapping):
        return sidecar_arg
    s_str = str(sidecar_arg).strip()
    if not s_str:
        return None
    sp = Path(s_str)
    if sp.is_file():
        return sp
    if sp.is_dir():
        cands = sorted(sp.glob(f"*{suffix}"))
        if len(cands) == 1:
            return cands[0]
        if scan_root is not None and cands:
            head_sha = ""
            git_head = scan_root / ".git" / "HEAD"
            if git_head.is_file():
                with contextlib.suppress(Exception):
                    htxt = git_head.read_text(encoding="utf-8", errors="ignore").strip()
                    if len(htxt) >= 12 and not htxt.startswith("ref:"):
                        head_sha = htxt[:16].lower()
            rname = scan_root.name.lower()
            for c in cands:
                stem_l = c.stem.lower()
                if (
                    (head_sha and head_sha in stem_l)
                    or stem_l == rname
                    or rname.endswith(stem_l)
                    or stem_l.startswith(rname.split("_")[0] + "_")
                ):
                    return c
    return sidecar_arg


def _select_sieve_slots(
    chunks: Sequence[Dict[str, Any]],
    feat_matrix: Sequence[Sequence[float]],
    genome_cfg: Mapping[str, Any],
    *,
    agent_tier: str,
    top_k: Optional[int] = None,
    max_tokens: Optional[int] = None,
    m_avail: Optional[Sequence[float]] = None,
) -> Tuple[List[int], List[float], List[float], int]:
    """Select ranked chunk indices under Conditional Residual Selection (UL-04), Span-IoU <= 0.30, and token wall."""
    m_len = len(chunks)
    if m_len == 0:
        return [], [], [], 0

    eff_m_avail = list(m_avail) if m_avail is not None else compute_channel_availability(chunks, feat_matrix)
    gamma_max = float(genome_cfg.get("gamma_max", 1.45))
    w_static = project_sieve_weights_simplex(genome_cfg["w_core"])
    w_core = apply_active_simplex_weights(genome_cfg["w_core"], eff_m_avail, gamma_max=gamma_max)
    raw_halo = genome_cfg.get("w_halo") or genome_cfg.get("w_residual") or genome_cfg["w_core"]
    w_halo = apply_active_simplex_weights(raw_halo, eff_m_avail, gamma_max=gamma_max)

    lam_div = max(
        0.0,
        float(genome_cfg.get("lambda_file_div", genome_cfg.get("diversity_lambda", 0.18))),
    )
    platt_t = max(1e-4, float(genome_cfg.get("platt_T", 0.11)))
    platt_b = float(genome_cfg.get("platt_b", -0.24))
    eff_top_k = int(top_k if top_k is not None and top_k > 0 else genome_cfg.get("top_k", 3))
    eff_budget = int(
        max_tokens if max_tokens is not None and max_tokens > 0 else genome_cfg.get("token_budget", 800)
    )

    core_scores = [
        sum(feat_matrix[i][d] * w_core[d] for d in range(8)) for i in range(m_len)
    ]
    static_scores = [
        sum(feat_matrix[i][d] * w_static[d] for d in range(8)) for i in range(m_len)
    ]
    halo_scores = [
        sum(feat_matrix[i][d] * w_halo[d] for d in range(8)) for i in range(m_len)
    ]
    est_tokens = [_chunk_total_est_tokens(chunks[i]) for i in range(m_len)]

    selected: List[int] = []
    file_counts: Counter[str] = Counter()
    used_tokens = 0
    per_file_cap = 1 if eff_top_k <= 3 else 2
    has_residual = agent_tier != "e4b-sniper" and (
        "w_halo" in genome_cfg or "w_residual" in genome_cfg
    )
    anchor_slots = min(eff_top_k, int(genome_cfg.get("anchor_slots", 3))) if has_residual else eff_top_k
    order_core = sorted(range(m_len), key=lambda idx: (-core_scores[idx], idx))

    for ii in order_core:
        if len(selected) >= anchor_slots:
            break
        f_key = str(chunks[ii].get("file", ""))
        if file_counts[f_key] >= per_file_cap:
            continue
        if any(_span_iou(chunks[ii], chunks[prev_i]) > 0.30 for prev_i in selected):
            continue
        tk = est_tokens[ii]
        if not selected and tk > eff_budget:
            tk = eff_budget
        elif (used_tokens + tk) > eff_budget:
            continue
        selected.append(ii)
        file_counts[f_key] += 1
        used_tokens += tk

    if has_residual and len(selected) < eff_top_k:
        anchor_file_set = set(file_counts.keys())
        sel_set = set(selected)
        while len(selected) < eff_top_k:
            best_i = -1
            best_adj = -1e9
            for i in range(m_len):
                if i in sel_set:
                    continue
                f_key = str(chunks[i].get("file", ""))
                cnt = file_counts[f_key]
                if cnt >= per_file_cap:
                    continue
                tk = est_tokens[i]
                if (used_tokens + tk) > eff_budget:
                    continue
                if any(_span_iou(chunks[i], chunks[prev_i]) > 0.30 for prev_i in selected):
                    continue
                adj = halo_scores[i] - lam_div * float(cnt)
                if f_key not in anchor_file_set and cnt == 0:
                    adj += 0.045
                if adj > best_adj:
                    best_adj = adj
                    best_i = i
            if best_i < 0:
                break
            selected.append(best_i)
            sel_set.add(best_i)
            bf_key = str(chunks[best_i].get("file", ""))
            file_counts[bf_key] += 1
            used_tokens += est_tokens[best_i]

    probs = [
        _platt_prob(0.35 * core_scores[i] + 0.65 * static_scores[i], platt_t, platt_b)
        for i in range(m_len)
    ]
    return selected, core_scores, probs, used_tokens


def sieve_code_graph(
    paths: Sequence[Union[str, Path]],
    query: str,
    *,
    agent_tier: str = "e4b-sniper",
    sieve_weights: Optional[Union[str, Path, Mapping[str, Any]]] = None,
    genome_key: Optional[str] = None,
    graph_path: Optional[Union[str, Path]] = None,
    embeddings_path: Optional[Union[str, Path, Mapping[str, Any]]] = None,
    top_k: Optional[int] = None,
    max_tokens: Optional[int] = None,
    max_chars: int = 1600,
    max_chunks: int = 4096,
    pattern: str = CODE_PATTERN,
) -> Dict[str, Any]:
    """Run zero-torch Stage 0+ AST & cross-regime matrix sieve with Slot-1 calibrated conformal abstention."""
    t0 = time.perf_counter()
    norm_tier = (agent_tier or "e4b-sniper").strip().lower()
    if norm_tier == "auto":
        norm_tier = "e4b-sniper"
    if norm_tier not in ("e4b-sniper", "31b-deep"):
        raise ValueError(f"Unsupported agent_tier {agent_tier!r}; expected 'e4b-sniper' or '31b-deep'.")

    genomes_bundle, genome_source = load_sieve_genomes(sieve_weights)
    if "w_core" in genomes_bundle:
        active_key = "custom_inline"
        genome_cfg = dict(genomes_bundle)
    else:
        if genome_key:
            active_key = genome_key
        else:
            active_key = "31b_deep" if norm_tier == "31b-deep" else "e4b_sniper_distilled"
        if active_key not in genomes_bundle:
            raise ValueError(f"Genome key {active_key!r} not found in {list(genomes_bundle.keys())}.")
        genome_cfg = dict(genomes_bundle[active_key])
        if "gamma_max" not in genome_cfg and "gamma_max" in genomes_bundle:
            genome_cfg["gamma_max"] = genomes_bundle["gamma_max"]

    str_paths = [str(p) for p in paths]
    files, scan_root = collect_target_files(str_paths, pattern=pattern)
    files = _prerank_repo_files(files, scan_root, query)

    eff_graph_path = _auto_discover_sidecar_path(graph_path, scan_root, ".json")
    eff_emb_path = _auto_discover_sidecar_path(embeddings_path, scan_root, ".npz")

    all_chunks: List[Dict[str, Any]] = []
    large_repo = len(files) > 60
    warm_cache = bool(files) and ((str(files[0]), max_chars, 0) in _AST_CHUNK_CACHE)
    max_file_scan = (
        (128 if len(files) > 150 else len(files))
        if warm_cache
        else (20 if len(files) > 55 else len(files))
    )
    for f_rank, fpath in enumerate(files[:max_file_scan]):
        rel_pfx = _rel_ref_prefix(fpath, scan_root)
        rem = max(0, max_chunks - len(all_chunks))
        if rem <= 0:
            break
        per_f_lim = (
            rem
            if not large_repo
            else min(rem, (48 if f_rank < 12 else 28) if warm_cache else 24)
        )
        f_chs = chunk_file(fpath, max_chars=max_chars, rel_prefix=rel_pfx, limit_hint=0)
        all_chunks.extend(_select_file_top_chunks(f_chs, query, per_f_lim))
        if len(all_chunks) >= max_chunks:
            all_chunks = all_chunks[:max_chunks]
            break

    ext_stats: Dict[str, Any] = {}
    feat_matrix = extract_code_graph_features(
        all_chunks,
        query,
        graph_path=eff_graph_path if not isinstance(eff_graph_path, Mapping) else None,
        embeddings_path=eff_emb_path,
        out_stats=ext_stats,
    )
    m_avail = compute_channel_availability(all_chunks, feat_matrix)
    eff_budget = int(
        max_tokens if max_tokens is not None and max_tokens > 0 else genome_cfg.get("token_budget", 800)
    )
    sel_idxs, core_scores, probs, _raw_used = _select_sieve_slots(
        all_chunks,
        feat_matrix,
        genome_cfg,
        agent_tier=norm_tier,
        top_k=top_k,
        max_tokens=eff_budget,
        m_avail=m_avail,
    )

    q_hat = float(genome_cfg.get("conformal_q_hat", 0.45))
    top1_prob = probs[sel_idxs[0]] if sel_idxs else 0.0
    max_prob = max((probs[i] for i in sel_idxs), default=0.0)
    abstain = bool(top1_prob < (1.0 - q_hat))
    route = "review" if abstain else "auto"

    out_items: List[Dict[str, Any]] = []
    running_tok = 0
    for slot_pos, idx in enumerate(sel_idxs, start=1):
        ch = all_chunks[idx]
        meta = ch.get("_ast_meta") or {}
        skel = str(meta.get("skeleton_header") or "")
        raw_txt = str(ch.get("text") or "")
        rendered = f"{skel}\n{raw_txt}" if (skel and skel not in raw_txt) else raw_txt
        rem_budget = max(1, eff_budget - running_tok)
        rendered_clamped = _truncate_text_to_token_budget(rendered, rem_budget)
        slot_tok = min(rem_budget, max(1, int(round(_estimate_tokens(rendered_clamped)))))
        running_tok += slot_tok
        out_items.append(
            {
                "slot": slot_pos,
                "role": "sniper_core" if (norm_tier == "e4b-sniper" or slot_pos <= 3) else "residual_halo",
                "ref": ch["ref"],
                "file": ch["file"],
                "name": ch["name"],
                "heading": ch["heading"],
                "symbol": meta.get("symbol", ""),
                "canonical_symbol": meta.get("canonical_symbol", meta.get("symbol", "")),
                "node_kind": meta.get("node_kind", ""),
                "skeleton_header": skel,
                "start_line": ch["start_line"],
                "end_line": ch["end_line"],
                "sieve_score": round(core_scores[idx], 4),
                "probability": round(probs[idx], 4),
                "est_tokens": slot_tok,
                "features": {
                    SIEVE_FEATURE_NAMES[d]: round(feat_matrix[idx][d], 4) for d in range(8)
                },
            }
        )

    return {
        "ok": True,
        "meta": {
            "version": __version__,
            "engine": "xlaya-code-graph-sieve",
            "agent_tier": norm_tier,
            "genome_key": active_key,
            "genome_source": genome_source,
            "files_scanned": len(files),
            "chunks_evaluated": len(all_chunks),
            "selected_count": len(out_items),
            "selected_tokens": running_tok,
            "token_budget": eff_budget,
            "top1_probability": round(top1_prob, 4),
            "max_probability": round(max_prob, 4),
            "conformal_q_hat": round(q_hat, 4),
            "abstain": abstain,
            "route": route,
            "m_avail": [round(x, 4) for x in m_avail],
            "external_graph_edges_matched": int(ext_stats.get("external_graph_edges_matched", 0)),
            "npz_symbols_matched": int(ext_stats.get("npz_symbols_matched", 0)),
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
        },
        "feature_names": list(SIEVE_FEATURE_NAMES),
        "results": out_items,
    }


_TOOL_STOPWORDS = frozenset(
    set(STOPWORDS)
    | {
        "you", "your", "please", "could", "would", "help", "need", "want", "looking",
        "some", "tell", "use", "using", "optional", "required", "default", "parameter", "parameters",
    }
)
_TOOL_GENERIC_VERBS = frozenset(
    {
        "find", "get", "fetch", "retrieve", "show", "give", "list", "search",
        "check", "query", "obtain", "return", "calculate", "compute", "generate",
        "create", "make", "perform", "run", "execute",
    }
)
_TOOL_FRAMING_NOISE = frozenset(
    {
        "interested", "interest", "detail", "information", "info", "provide", "specify",
        "assist", "assistance", "proceed", "latest", "current", "currently", "available",
        "availability", "possible", "possibility", "check", "know", "like", "look",
        "need", "want", "able", "can", "could", "would", "should", "please", "help",
        "tell", "give", "show", "fetch", "retrieve", "get", "find", "search", "list",
        "obtain", "calculate", "compute", "generate", "create", "make", "perform", "run",
        "execute", "use", "base", "based", "data", "value", "result", "report", "status",
        "summary", "overview", "specific", "certain", "particular", "any", "some", "more",
        "about", "api", "tool", "function", "service", "system", "endpoint", "method",
    }
)
_TOOL_NUMBER_WORDS = frozenset(
    {"zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "dozen", "hundred"}
)
_TOOL_CAMEL_RE = re.compile(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+")
_TOOL_NUM_RE = re.compile(r"(?<![A-Za-z])-?\d+(?:\.\d+)?(?![A-Za-z])")
_TOOL_QUOTED_RE = re.compile(r"""['"]([^'"]{1,80})['"]""")
_TOOL_LIST_LIT_RE = re.compile(r"\[[^\]\n]{1,160}\]")
_TOOL_URL_DOMAIN_RE = re.compile(
    r"\b(?:https?://\S+|\S+@\S+\.[A-Za-z]{2,}|[A-Za-z0-9-]+\.(?:com|org|net|io|gov|edu|co|uk|de|jp|ai|app))\b",
    re.IGNORECASE,
)
_TOOL_ID_HEX_RE = re.compile(r"\b(?:[A-Za-z]+\d+[A-Za-z0-9_-]*|\d+[A-Za-z]+[A-Za-z0-9_-]*|[0-9a-f]{8,})\b")


def _tool_stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 5 and word.endswith("ing") and not word.endswith(("thing", "string", "ring", "king")):
        base = word[:-3]
        return base[:-1] if len(base) >= 4 and base[-1] == base[-2] else base
    if len(word) > 5 and word.endswith(("ches", "shes", "xes", "zes", "sses")):
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def _tool_split_tokens(text: str, *, strip_generic_verbs: bool = False) -> List[str]:
    out: List[str] = []
    raw_all: List[str] = []
    for raw in re.findall(r"[A-Za-z0-9_]+", text):
        low = raw.lower()
        for sub in raw.split("_"):
            if not sub:
                continue
            for p in _TOOL_CAMEL_RE.findall(sub):
                pl = p.lower()
                if len(pl) >= 2 and pl not in _TOOL_STOPWORDS:
                    st = _tool_stem(pl)
                    raw_all.append(st)
                    if not (strip_generic_verbs and pl in _TOOL_GENERIC_VERBS):
                        out.append(st)
        if len(low) >= 3 and "_" not in low and low not in _TOOL_STOPWORDS:
            st_low = _tool_stem(low)
            if st_low not in raw_all:
                raw_all.append(st_low)
            if not (strip_generic_verbs and low in _TOOL_GENERIC_VERBS) and st_low not in out:
                out.append(st_low)
    return out if out else raw_all


def extract_tool_call_features(
    query: str,
    tools: Sequence[Union[str, Mapping[str, Any]]],
) -> Tuple[List[float], str]:
    """
    Extract 18D Sibling- & Schema-Invariant Causal 2-Stage Tool Conformal features (F-06 / Decision 4A):
      - Stage 1 (Dims 0..6): Intrinsic per-tool intent relevance (`P(rel)`, invariant to sibling tool count)
      - Stage 2 (Dims 7..17): Schema-invariant OpenAI/BFCL `parameters.required` + ToolBench `optional` slots
    Returns `(features_18d, matched_tool_name)`.
    """
    parsed_tools: List[Mapping[str, Any]] = []
    for item in tools or ():
        obj: Any = item
        if isinstance(item, str):
            with contextlib.suppress(Exception):
                obj = json.loads(item)
        if isinstance(obj, Mapping):
            fn = obj.get("function", obj)
            if isinstance(fn, Mapping):
                parsed_tools.append(fn)

    if not parsed_tools or not query.strip():
        return [0.0] * 18, ""

    q_toks = _tool_split_tokens(query, strip_generic_verbs=True)
    q_set = set(q_toks)
    q_low = query.lower()
    q_quotes = _TOOL_QUOTED_RE.findall(query)
    q_lists = _TOOL_LIST_LIT_RE.findall(query)
    q_urls = _TOOL_URL_DOMAIN_RE.findall(query)
    query_unquoted = _TOOL_QUOTED_RE.sub(" ", _TOOL_LIST_LIT_RE.sub(" ", _TOOL_URL_DOMAIN_RE.sub(" ", query)))
    q_unq_low = query_unquoted.lower()
    q_nums = _TOOL_NUM_RE.findall(query_unquoted) + [
        w for w in re.findall(r"\b[a-z]+\b", q_unq_low) if w in _TOOL_NUMBER_WORDS
    ]
    q_ids = _TOOL_ID_HEX_RE.findall(query_unquoted)
    words_unq = re.findall(r"\b[A-Za-z][A-Za-z0-9.-]*\b", query_unquoted)
    _scream_stop = (
        _TOOL_STOPWORDS
        | _TOOL_GENERIC_VERBS
        | {
            "now", "today", "here", "my", "me", "i", "api", "sdk", "url", "uri", "id",
            "json", "xml", "html", "csv", "fasta", "genbank", "utc", "gmt", "http", "https",
        }
    )
    # Group contiguous capitalized words into single proper-noun phrases
    # (skipping sentence-initial word unless multi-word)
    raw_proper_phrases: List[str] = []
    for m_pr in re.finditer(r"\b[A-Z][A-Za-z0-9.-]*(?:\s+[A-Z][A-Za-z0-9.-]*)*\b", query_unquoted):
        phrase = m_pr.group(0).strip()
        p_words = phrase.split()
        if m_pr.start() == 0 and len(p_words) == 1 and not (2 <= len(p_words[0]) <= 5 and p_words[0].isupper()):
            continue
        kept_w = [w for w in p_words if w.lower() not in _scream_stop]
        if kept_w:
            raw_proper_phrases.append(" ".join(kept_w))

    q_tickers = [
        w
        for idx, w in enumerate(words_unq)
        if w.lower() not in _scream_stop and 2 <= len(w) <= 5 and w.isupper() and (idx > 0 or len(w) >= 3)
    ] + re.findall(r"\$([A-Za-z]{1,6})\b", query)

    best_rank_sc = -1.0
    best_feats: List[float] = [0.0] * 18
    best_name = ""

    for fn in parsed_tools:
        nm = str(fn.get("name", ""))
        leaf_flat = re.sub(r"[^a-z0-9]", "", nm.lower())
        desc = str(fn.get("description", ""))
        raw_params = fn.get("parameters") or fn.get("input_schema") or fn.get("arguments")
        params = raw_params if isinstance(raw_params, Mapping) else {}
        props = params.get("properties") if isinstance(params.get("properties"), Mapping) else {}

        nm_toks = _tool_split_tokens(nm.replace(".", "_"), strip_generic_verbs=True)
        desc_toks = _tool_split_tokens(f"{nm.replace('.', ' ')} {desc}", strip_generic_verbs=True)
        prop_name_toks: List[str] = []
        prop_toks: List[str] = []
        for pk, pv in props.items():
            pk_split = _tool_split_tokens(str(pk), strip_generic_verbs=True)
            prop_name_toks.extend(pk_split)
            prop_toks.extend(pk_split)
            if isinstance(pv, Mapping):
                prop_toks.extend(_tool_split_tokens(str(pv.get("description", "")), strip_generic_verbs=True))
                for ev in (pv.get("enum") or ())[:12]:
                    prop_toks.extend(_tool_split_tokens(str(ev)))

        nm_set = set(nm_toks)
        desc_set = set(desc_toks)
        prop_name_set = set(prop_name_toks)
        prop_set = set(prop_toks)
        intent_set = nm_set | desc_set
        full_set = intent_set | prop_set

        compound_hits = {qt for qt in q_set if len(qt) >= 4 and leaf_flat and qt in leaf_flat}
        nm_matched = (q_set & nm_set) | compound_hits
        nm_denom = max(1, len(nm_set)) if nm_set else 1
        nm_rec = min(1.0, len(nm_matched) / nm_denom) if (nm_set or compound_hits) else 0.0

        q_denom = max(1, len(q_set))
        q_cov_desc = min(1.0, len((q_set & intent_set) | compound_hits) / q_denom) if q_set else 0.0
        q_cov_full = min(1.0, len((q_set & full_set) | compound_hits) / q_denom) if q_set else 0.0
        sig_union = nm_set | prop_name_set
        sig_cov = (
            min(1.0, len((q_set & sig_union) | compound_hits) / max(1, len(sig_union)))
            if sig_union
            else q_cov_desc
        )
        prop_name_rec = (
            min(1.0, len(q_set & prop_name_set) / max(1, len(prop_name_set)))
            if prop_name_set
            else nm_rec
        )
        harmonic_f1_intent = (2.0 * nm_rec * q_cov_full) / max(1e-6, nm_rec + q_cov_full)
        rel_sc = (
            0.30 * nm_rec
            + 0.22 * q_cov_desc
            + 0.18 * q_cov_full
            + 0.15 * sig_cov
            + 0.15 * harmonic_f1_intent
        )

        raw_req = params.get("required") if isinstance(params, Mapping) else None
        if not isinstance(raw_req, list):
            raw_req = fn.get("required")
        req_list = raw_req if isinstance(raw_req, list) else None
        has_toolbench_opt_tags = any(
            isinstance(v, Mapping) and "optional" in str(v.get("type", "")).lower()
            for v in props.values()
        )
        req_props: List[Tuple[str, str, str, Mapping[str, Any]]] = []
        opt_props: List[Tuple[str, str, str, Mapping[str, Any]]] = []
        for pk, pv in props.items():
            pv_map = pv if isinstance(pv, Mapping) else {}
            ptype = str(pv_map.get("type", "str")).lower()
            pdesc_raw = str(pv_map.get("description", ""))
            pdesc = pdesc_raw.lower()
            if req_list is not None:
                is_req = (pk in req_list) and ("optional" not in ptype)
            elif has_toolbench_opt_tags:
                is_req = ("optional" not in ptype) and ("optional" not in pdesc)
            else:
                is_req = False
            if is_req:
                req_props.append((str(pk), ptype, pdesc_raw, pv_map))
            else:
                opt_props.append((str(pk), ptype, pdesc_raw, pv_map))

        opt_toks_all: set[str] = set()
        opt_enums_low: set[str] = set()
        opt_bound_nums = 0
        opt_bound_quotes: set[str] = set()
        for opk, _, opdesc_raw, opv in opt_props:
            op_toks = _tool_split_tokens(opk)
            opt_toks_all.update(op_toks)
            for ev in (opv.get("enum") or ())[:16]:
                opt_enums_low.add(str(ev).lower())
            for dq in _TOOL_QUOTED_RE.findall(opdesc_raw):
                if 1 <= len(dq.strip()) <= 32:
                    opt_enums_low.add(dq.strip().lower())
            for ost in set(op_toks) | {opk.lower()}:
                if len(ost) >= 3:
                    if re.search(rf"\b{re.escape(ost)}\b(?:\s+(?:of|is|to|=|:))?\s*-?\d+", q_unq_low) or re.search(
                        rf"-?\d+(?:\.\d+)?%?\s+(?:\w+\s+)?{re.escape(ost)}\b", q_unq_low
                    ):
                        opt_bound_nums += 1
                    for qt in q_quotes:
                        qt_l = qt.lower()
                        q_pat = (
                            rf"(?:['\"]{re.escape(qt_l)}['\"]\s+(?:\w+\s+)?{re.escape(ost)}\b|"
                            rf"\b{re.escape(ost)}\s+(?:is\s+|of\s+|=\s*)?['\"]{re.escape(qt_l)}['\"])"
                        )
                        if re.search(q_pat, q_low):
                            opt_bound_quotes.add(qt_l)

        eff_num_count = max(0, len(q_nums) - opt_bound_nums)
        non_opt_quotes = [
            qt
            for qt in q_quotes
            if qt.lower() not in opt_enums_low
            and qt.lower() not in opt_bound_quotes
            and not (set(_tool_split_tokens(qt)) <= opt_toks_all and opt_toks_all)
        ]

        # Exclude proper-noun phrases that merely repeat the tool/API/format schema names
        schema_stems = nm_set | desc_set | prop_name_set | opt_toks_all | {_tool_stem(e) for e in opt_enums_low}
        q_proper = [
            ph
            for ph in raw_proper_phrases
            if not (set(_tool_split_tokens(ph)) <= schema_stems and bool(_tool_split_tokens(ph)))
        ]

        all_req_name_toks: set[str] = set()
        for rpk, _, _, _ in req_props:
            all_req_name_toks.update(_tool_split_tokens(rpk, strip_generic_verbs=True))

        arg_value_toks = [
            t
            for t in q_toks
            if t not in (nm_set | compound_hits)
            and t not in _TOOL_FRAMING_NOISE
            and t not in opt_toks_all
            and t not in all_req_name_toks
        ]
        n_concrete_entities = (
            eff_num_count + len(non_opt_quotes) + len(q_lists) + len(q_urls) + len(q_proper) + len(q_ids)
        )

        req_total = len(req_props)
        req_filled = 0
        missing_num_slot = 0
        missing_id_url_slot = 0
        param_concept_cov_sum = 0.0
        n_num_req = 0

        avail_nums = eff_num_count
        avail_quotes = len(non_opt_quotes)
        avail_proper = len(q_proper)
        avail_coord_places = 2 * len(q_proper) + 2 * len(non_opt_quotes)
        avail_ids = len(q_ids)
        avail_urls = len(q_urls)
        avail_lists = len(q_lists)
        avail_tickers = len(q_tickers)
        avail_arg_toks = len(arg_value_toks)

        # Score concept overlap first and process concept-anchored slots before unanchored slots
        scored_req_props: List[Tuple[float, int, str, str, str, Mapping[str, Any], float]] = []
        for idx_rp, (pk, ptype, pdesc_raw, pv_map) in enumerate(req_props):
            pk_toks = set(_tool_split_tokens(pk, strip_generic_verbs=True))
            pd_toks = set(_tool_split_tokens(pdesc_raw.lower(), strip_generic_verbs=True))
            p_all = pk_toks | pd_toks
            c_cov = min(1.0, (len(q_set & p_all) / max(1, min(3, len(p_all))))) if p_all else 0.5
            param_concept_cov_sum += c_cov
            scored_req_props.append((-c_cov, idx_rp, pk, ptype, pdesc_raw, pv_map, c_cov))
        scored_req_props.sort()

        for _, _, pk, ptype, pdesc_raw, pv_map, c_cov in scored_req_props:
            pk_low = pk.lower()
            pdesc = pdesc_raw.lower()

            wants_list = ("array" in ptype) or ("list" in ptype)
            wants_num = (
                any(k in ptype for k in ("int", "float", "number"))
                and "str" not in ptype
                and not wants_list
            ) or pk_low in ("year", "age", "count", "limit", "page", "offset", "quantity")
            is_url_email = (not wants_num) and any(
                k in pk_low for k in ("url", "uri", "email", "domain", "website", "host", "endpoint")
            )
            is_coord = (not wants_num) and (
                pk_low in ("coord", "coords", "coordinates", "lat", "lon", "lng", "latitude", "longitude")
                or pk_low.endswith(("_lat", "_lon", "_lng"))
            )
            is_ticker = (not wants_num) and pk_low in ("ticker", "symbol", "stock_symbol", "ticker_symbol")
            is_id_code = (
                not wants_num
                and not is_ticker
                and (
                    pk_low in ("id", "uuid", "mmsi", "isbn", "vin", "zipcode", "zip_code", "postal_code", "pincode")
                    or pk_low.endswith(("_id", "_uuid"))
                )
            )

            enum_vals = [str(ev).lower() for ev in (pv_map.get("enum") or ()) if str(ev).strip()]
            if (
                not enum_vals
                and any(h in pdesc for h in ("one of:", "options are", "valid values are", "allowed values are"))
                and not any(ex in pdesc for ex in ("e.g.", "for example", "such as", "format"))
            ):
                desc_qs = [q.strip().lower() for q in _TOOL_QUOTED_RE.findall(pdesc_raw) if 1 <= len(q.strip()) <= 24]
                if 2 <= len(desc_qs) <= 10:
                    enum_vals = desc_qs

            slot_ok = False
            if is_coord:
                if avail_nums > 0:
                    avail_nums -= 1
                    slot_ok = True
                elif avail_coord_places > 0:
                    avail_coord_places -= 1
                    slot_ok = True
                else:
                    missing_num_slot += 1
            elif wants_num:
                n_num_req += 1
                if avail_nums > 0:
                    avail_nums -= 1
                    slot_ok = True
                else:
                    missing_num_slot += 1
            elif is_url_email:
                if avail_urls > 0:
                    avail_urls -= 1
                    slot_ok = True
                elif avail_quotes > 0:
                    avail_quotes -= 1
                    slot_ok = True
                elif avail_proper > 0:
                    avail_proper -= 1
                    slot_ok = True
                else:
                    missing_id_url_slot += 1
            elif is_ticker:
                if avail_tickers > 0:
                    avail_tickers -= 1
                    slot_ok = True
                elif avail_quotes > 0:
                    avail_quotes -= 1
                    slot_ok = True
                elif avail_ids > 0:
                    avail_ids -= 1
                    slot_ok = True
                else:
                    missing_id_url_slot += 1
            elif is_id_code:
                if avail_ids > 0:
                    avail_ids -= 1
                    slot_ok = True
                elif avail_nums > 0:
                    avail_nums -= 1
                    slot_ok = True
                elif avail_quotes > 0:
                    avail_quotes -= 1
                    slot_ok = True
                elif avail_tickers > 0:
                    avail_tickers -= 1
                    slot_ok = True
                else:
                    missing_id_url_slot += 1
            elif enum_vals:
                if any(
                    ev in q_low or (bool(_tool_split_tokens(ev)) and set(_tool_split_tokens(ev)) <= q_set)
                    for ev in enum_vals
                ):
                    slot_ok = True
                elif avail_quotes > 0:
                    avail_quotes -= 1
                    slot_ok = True
                else:
                    missing_id_url_slot += 1
            elif wants_list:
                if avail_lists > 0:
                    avail_lists -= 1
                    slot_ok = True
                elif (
                    avail_quotes >= 1
                    or avail_proper >= 2
                    or avail_nums >= 2
                    or "," in query_unquoted
                    or " and " in q_unq_low
                ):
                    if avail_quotes > 0:
                        avail_quotes -= 1
                    slot_ok = True
                else:
                    missing_num_slot += 1
            else:
                if avail_quotes > 0:
                    avail_quotes -= 1
                    slot_ok = True
                elif avail_proper > 0:
                    avail_proper -= 1
                    slot_ok = True
                elif avail_urls > 0:
                    avail_urls -= 1
                    slot_ok = True
                elif avail_ids > 0:
                    avail_ids -= 1
                    slot_ok = True
                elif avail_lists > 0:
                    avail_lists -= 1
                    slot_ok = True
                elif avail_nums > 0:
                    avail_nums -= 1
                    slot_ok = True
                elif c_cov >= 0.34 and avail_arg_toks >= 2 and n_concrete_entities >= max(0, req_total - 1):
                    avail_arg_toks -= 2
                    slot_ok = True
            if slot_ok:
                req_filled += 1

        req_cov = (req_filled / req_total) if req_total > 0 else 1.0
        unfilled_ratio = ((req_total - req_filled) / req_total) if req_total > 0 else 0.0
        unfilled_count_norm = min(1.0, max(0, req_total - req_filled) / 3.0)
        mean_param_cov = (param_concept_cov_sum / req_total) if req_total > 0 else 1.0
        num_deficit = max(0, n_num_req - eff_num_count)
        entity_per_req = min(1.0, n_concrete_entities / max(1, req_total)) if req_total > 0 else 1.0
        concrete_val_cov = (
            min(1.0, (n_concrete_entities + 0.35 * len(arg_value_toks)) / max(1, req_total))
            if req_total > 0
            else 1.0
        )
        entity_deficit_flag = (
            1.0
            if (req_total > 0 and (n_concrete_entities < req_total or req_cov < 1.0))
            else 0.0
        )

        joint_rel_slot_harmony = harmonic_f1_intent * (0.40 + 0.60 * mean_param_cov)
        cand_feats = [
            round(nm_rec, 6),  # 0 (+1)
            round(q_cov_desc, 6),  # 1 (+1)
            round(q_cov_full, 6),  # 2 (+1)
            round(sig_cov, 6),  # 3 (+1)
            round(prop_name_rec, 6),  # 4 (+1)
            round(harmonic_f1_intent, 6),  # 5 (+1)
            round(joint_rel_slot_harmony, 6),  # 6 (+1)
            1.0 if req_total == 0 else 0.0,  # 7 (+1): zero_req_invariant
            round(req_cov, 6),  # 8 (+1)
            round(unfilled_ratio, 6),  # 9 (-1)
            round(unfilled_count_norm, 6),  # 10 (-1)
            1.0 if missing_num_slot > 0 else 0.0,  # 11 (-1)
            1.0 if missing_id_url_slot > 0 else 0.0,  # 12 (-1)
            round(entity_per_req, 6),  # 13 (+1)
            round(mean_param_cov, 6),  # 14 (+1)
            round(concrete_val_cov, 6),  # 15 (+1)
            round(min(1.0, num_deficit / 2.0), 6),  # 16 (-1)
            entity_deficit_flag,  # 17 (-1)
        ]
        rank_sc = rel_sc + 0.22 * req_cov * min(1.0, rel_sc / 0.25)
        if rank_sc > best_rank_sc:
            best_rank_sc = rank_sc
            best_feats = cand_feats
            best_name = nm

    return best_feats, best_name


def triage_tool_call(
    query: str,
    tools: Sequence[Union[str, Mapping[str, Any]]],
    *,
    sieve_weights: Optional[Union[str, Path, Mapping[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Execute the zero-torch Factorized 2-Stage Tool-Schema Conformal Gate (`When2Call` / MCP tool routing):
      - Stage 1: `p_rel = P(relevant_tool_exists | f[0..6])`
      - Stage 2: `p_slots = P(required_slots_satisfied | f[7..17], rel)` (causal floor when `req_total == 0`)
      - Exact Bayes Chain Rule: `P(tool_call) = p_rel * p_slots`,
        `P(cannot_answer) = 1 - p_rel`, `P(rfi) = p_rel * (1 - p_slots)`
    """
    t0 = time.perf_counter()
    feats, matched_tool = extract_tool_call_features(query, tools)
    if not matched_tool or not query.strip():
        return {
            "ok": True,
            "decision": "cannot_answer",
            "abstain": True,
            "route": "review",
            "matched_tool": "",
            "tool_probability": 0.0,
            "class_probabilities": {"tool_call": 0.0, "cannot_answer": 1.0, "request_for_info": 0.0},
            "conformal_q_hat": 0.50,
            "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        }

    bundle, source = load_sieve_genomes(sieve_weights)
    gate_cfg = bundle.get("tool_gate") if isinstance(bundle.get("tool_gate"), Mapping) else {}
    tau_tool = float(gate_cfg.get("tau_tool_call", 0.50))

    if gate_cfg.get("schema") == "factorized_2stage_v23" and "rel_w1" in gate_cfg and "slot_w1" in gate_cfg:
        f_rel = feats[:7]
        rw1, rb1 = gate_cfg["rel_w1"], gate_cfg["rel_b1"]
        rw2, rb2 = gate_cfg["rel_w2"], float(gate_cfg["rel_b2"])
        t_rel = max(0.05, float(gate_cfg.get("temp_rel", 1.0)))
        h_rel = [
            math.tanh(sum(float(rw1[h][d]) * f_rel[d] for d in range(len(f_rel))) + float(rb1[h]))
            for h in range(len(rb1))
        ]
        z_rel = (sum(float(rw2[h]) * h_rel[h] for h in range(len(h_rel))) + rb2) / t_rel
        p_rel = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z_rel))))

        f_slot = feats[7:]
        sw1, sb1 = gate_cfg["slot_w1"], gate_cfg["slot_b1"]
        sw2, sb2 = gate_cfg["slot_w2"], float(gate_cfg["slot_b2"])
        t_slot = max(0.05, float(gate_cfg.get("temp_slot", 1.0)))
        h_slot = [
            math.tanh(sum(float(sw1[h][d]) * f_slot[d] for d in range(len(f_slot))) + float(sb1[h]))
            for h in range(len(sb1))
        ]
        z_slot = (sum(float(sw2[h]) * h_slot[h] for h in range(len(h_slot))) + sb2) / t_slot
        p_slots = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, z_slot))))

        p_tool = p_rel * p_slots
        p_cannot = 1.0 - p_rel
        p_rfi = p_rel * (1.0 - p_slots)
    else:
        rel_z = 2.3 * feats[0] + 2.2 * feats[1] + 1.5 * feats[2] + 1.3 * feats[4] + 1.4 * feats[5] - 1.45
        p_rel = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, rel_z))))
        if feats[7] >= 0.5:
            p_slots = 0.94
        else:
            slot_z = (
                2.5 * feats[8]
                - 1.8 * feats[9]
                - 2.0 * feats[11]
                - 1.8 * feats[12]
                + 1.2 * feats[13]
                + 1.0 * feats[14]
                - 1.5 * feats[16]
                - 1.3 * feats[17]
                - 0.85
            )
            p_slots = 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, slot_z))))
        p_tool = p_rel * p_slots
        p_cannot = 1.0 - p_rel
        p_rfi = p_rel * (1.0 - p_slots)
    abstain = bool(p_tool < tau_tool)
    if not abstain:
        decision = "tool_call"
    else:
        decision = "cannot_answer" if p_cannot >= p_rfi else "request_for_info"

    return {
        "ok": True,
        "decision": decision,
        "abstain": abstain,
        "route": "review" if abstain else "auto",
        "matched_tool": matched_tool,
        "tool_probability": round(p_tool, 4),
        "class_probabilities": {
            "tool_call": round(p_tool, 4),
            "cannot_answer": round(p_cannot, 4),
            "request_for_info": round(p_rfi, 4),
        },
        "conformal_q_hat": round(1.0 - tau_tool, 4),
        "genome_source": source,
        "features": feats,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
    }


# ---------------------------------------------------------------------------
# Pure-Python Deterministic Fallback (Zero External ML Dependencies)
# ---------------------------------------------------------------------------


def _significant_numbers(text: str) -> set[str]:
    stripped_lines = [LINE_INDEX_PREFIX_RE.sub("", ln) for ln in text.splitlines()]
    return set(NUMBER_TOKEN_RE.findall("\n".join(stripped_lines)))


def fallback_evaluate(
    chunks: List[Dict[str, Any]],
    mode: str,
    query: str,
    ssot: str,
    labels: Dict[str, str],
    threshold: float = 0.55,
) -> List[Dict[str, Any]]:
    """Deterministic lexical + Thai 3-gram + subset-safe contradiction fallback."""
    lex_scores = compute_lexical_scores(chunks, query or ssot)
    ssot_nums = _significant_numbers(ssot) if ssot else set()
    negation_markers = {"not", "never", "false", "deprecated", "legacy", "unsupported", "removed"}
    ssot_negations = set(LATIN_TOKEN_RE.findall(ssot.lower())) & negation_markers

    results: List[Dict[str, Any]] = []
    for ch, lex in zip(chunks, lex_scores):
        txt = ch["text"]
        word_count = max(1, len(txt.split()))
        has_code = "```" in txt or "`" in txt
        has_table = "|" in txt
        item = dict(ch)
        item["engine"] = "pure-python-fallback"
        item["lexical_score"] = lex

        if mode == "shortlist":
            exp_score = round(min(4.0, lex * 4.0), 4)
            hyb = round(0.82 * (exp_score / 4.0) + 0.18 * lex, 4)
            item.update(
                {
                    "score": exp_score,
                    "expected_score": exp_score,
                    "hybrid_score": hyb,
                    "noul": 0.0,
                    "confidence": 0.5,
                }
            )
        elif mode == "contradiction":
            chunk_nums = _significant_numbers(txt)
            chunk_words = set(LATIN_TOKEN_RE.findall(txt.lower()))
            # Subset/superset safe: require both an unfulfilled SSOT number and a conflicting chunk number
            has_conflicting_nums = bool(
                ssot_nums
                and chunk_nums
                and bool(ssot_nums - chunk_nums)
                and bool(chunk_nums - ssot_nums)
            )
            has_extra_negation = bool((chunk_words & negation_markers) - ssot_negations)
            rel = round(min(1.0, lex * 1.15), 4)
            if rel >= 0.25 and (has_conflicting_nums or has_extra_negation):
                raw_p = round(min(0.95, 0.72 + 0.25 * rel), 4)
            else:
                raw_p = round(0.08 * rel, 4)
            eff_p = round(rel * raw_p, 4)
            item.update(
                {
                    "score": 0.0,
                    "noul": eff_p,
                    "noul_raw": raw_p,
                    "relevance": rel,
                    "flagged": bool(eff_p >= threshold),
                    "confidence": 0.5,
                }
            )
        elif mode == "classify":
            best_label = next(iter(labels.keys()), "unknown")
            best_score = -1.0
            for lbl, desc in labels.items():
                lbl_lex = compute_lexical_scores([ch], f"{lbl} {desc}")[0]
                if lbl_lex > best_score:
                    best_score = lbl_lex
                    best_label = lbl
            item.update({"choice": best_label, "confidence": round(0.4 + 0.4 * max(0.0, best_score), 4)})
        else:
            base = min(2.5, word_count / 55.0)
            bonus = (0.75 if has_code else 0.0) + (0.75 if has_table else 0.0)
            exp_score = round(min(4.0, base + bonus), 4)
            item.update(
                {
                    "score": exp_score,
                    "expected_score": exp_score,
                    "noul": 0.0,
                    "confidence": 0.5,
                }
            )
        results.append(item)
    return results


# ---------------------------------------------------------------------------
# Stage 1 & Stage 2: Neural Triage + Conformal VegaML Escalation
# ---------------------------------------------------------------------------


def parse_label_spec(spec: str) -> Dict[str, str]:
    """Parse 'label1:desc1|label2:desc2' or comma-separated labels into a criteria dict."""
    effective = spec.strip() or DEFAULT_LABELS_SPEC
    sep = "|" if "|" in effective else ","
    out: Dict[str, str] = {}
    for item in effective.split(sep):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            k, v = item.split(":", 1)
            out[k.strip()] = v.strip()
        else:
            out[item] = item
    return out


def parse_noul_labels(spec: str) -> Optional[Dict[str, str]]:
    """Parse optional '--noul-labels' (e.g. 'B,A' -> {'false': 'B', 'true': 'A'})."""
    cleaned = spec.strip()
    if not cleaned:
        return None
    if ":" in cleaned:
        sep = "|" if "|" in cleaned else ","
        mapped: Dict[str, str] = {}
        for part in cleaned.split(sep):
            if ":" in part:
                k, v = part.split(":", 1)
                mapped[k.strip().lower()] = v.strip()
        if set(mapped.keys()) != {"false", "true"} or mapped["false"] == mapped["true"]:
            raise ValueError("noul_labels mapping must provide distinct 'false' and 'true' labels.")
        return mapped
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    if len(parts) != 2 or parts[0] == parts[1]:
        raise ValueError("noul_labels must contain two distinct comma-separated labels, e.g. 'B,A'.")
    return {"false": parts[0], "true": parts[1]}


def _shares_specific_identifier(chunk_text: str, ssot_text: str) -> bool:
    ident_re = re.compile(r"\b[A-Za-z][A-Za-z0-9]*(?:[-_][A-Za-z0-9]+)+\b|\b[A-Za-z]+[0-9]+[A-Za-z0-9.-]*\b")
    ssot_idents = {m.lower() for m in ident_re.findall(ssot_text) if len(m) >= 4}
    if not ssot_idents:
        return False
    chunk_low = chunk_text.lower()
    return any(ident in chunk_low for ident in ssot_idents)


def _build_mode_questions(
    mode: str,
    query: str,
    ssot: str,
    true_desc: str,
    false_desc: str,
    labels: Dict[str, str],
    noul_label_map: Optional[Dict[str, str]],
    thorough: bool = False,
    rubric_preset: str = "default",
) -> Dict[str, Dict[str, Any]]:
    def with_noul_labels(q: Dict[str, Any]) -> Dict[str, Any]:
        if noul_label_map is not None:
            q = dict(q)
            q["labels"] = noul_label_map
        return q

    def joint_contradiction_questions(canon: str) -> Dict[str, Dict[str, Any]]:
        rel_q: Dict[str, Any] = {
            "type": "noul",
            "instructions": f"Does this passage mention the specific model or subject of: {canon}?",
        }
        cons_q: Dict[str, Any] = {
            "type": "noul",
            "instructions": (
                f"Are the facts and numbers stated in this passage consistent and compatible with: {canon}?"
            ),
        }
        contra_q: Dict[str, Any] = {
            "type": "noul",
            "instructions": (
                f"Assuming `{canon}` is strictly true, does this text state any conflicting "
                "number, incompatible limit, wrong version, or opposite behavior?"
            ),
        }
        if false_desc or true_desc:
            contra_q["criteria"] = {
                "false": false_desc or "consistent or compatible",
                "true": true_desc or "states conflicting numbers or opposite claims",
            }
        return {
            "is_relevant": with_noul_labels(rel_q),
            "is_consistent": with_noul_labels(cons_q),
            "contradicts_ssot": with_noul_labels(contra_q),
        }

    if mode == "shortlist":
        return {
            "rel": {
                "type": "score",
                "instructions": f"Rate how directly this section answers or specifies: {query}",
                "criteria": DEFAULT_RELEVANCE_CRITERIA,
            }
        }
    if mode == "contradiction":
        return joint_contradiction_questions(ssot)
    if mode == "classify":
        return {
            "cat": {
                "type": "choice",
                "instructions": query or "Classify this text into the most accurate category.",
                "criteria": labels,
            }
        }

    qs: Dict[str, Dict[str, Any]] = {}
    if thorough:
        preset_key = rubric_preset if rubric_preset in RUBRIC_PRESETS else "default"
        preset_spec = RUBRIC_PRESETS[preset_key]
        query_suffix = f" (Focus: {query})" if query.strip() else ""
        for facet_name in FACET_WEIGHTS:
            facet_def = preset_spec[facet_name]
            qs[f"facet_{facet_name}"] = {
                "type": "score",
                "instructions": f"{facet_def['instructions']}{query_suffix}",
                "criteria": list(facet_def["criteria"]),
            }
    else:
        qs["rubric"] = {
            "type": "score",
            "instructions": query or "Rate the technical completeness and specificity of this documentation.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        }
    if ssot:
        qs.update(joint_contradiction_questions(ssot))
    return qs


def _extract_facet_breakdown(ans: Dict[str, Any]) -> Dict[str, Any]:
    """Compute 4-facet decomposed rubric metrics from prediction answers."""
    facet_scores: Dict[str, float] = {}
    facet_confs: List[float] = []
    facet_disagreements: List[float] = []
    for facet_name in FACET_WEIGHTS:
        q_key = f"facet_{facet_name}"
        f_ans = ans.get(q_key, {})
        val = float(f_ans.get("expected_score", f_ans.get("score", 0.0)))
        facet_scores[facet_name] = round(val, 4)
        if "confidence" in f_ans:
            facet_confs.append(float(f_ans["confidence"]))
        if "disagreement" in f_ans:
            facet_disagreements.append(float(f_ans["disagreement"]))

    composite = sum(facet_scores[f] * w for f, w in FACET_WEIGHTS.items())
    vals = list(facet_scores.values())
    f_min = min(vals) if vals else 0.0
    f_max = max(vals) if vals else 0.0
    f_spread = round(f_max - f_min, 4)
    weakest = min(facet_scores.items(), key=lambda kv: (kv[1], kv[0]))[0] if facet_scores else "specificity"
    mean_conf = sum(facet_confs) / len(facet_confs) if facet_confs else 0.5
    out: Dict[str, Any] = {
        "facet_scores": facet_scores,
        "facet_min": round(f_min, 4),
        "facet_spread": f_spread,
        "weakest_facet": weakest,
        "composite_score": round(composite, 4),
        "confidence": round(mean_conf, 4),
    }
    if facet_disagreements:
        max_dis = max(facet_disagreements)
        out["disagreement"] = round(max_dis, 4)
        out["model_agreement"] = round(1.0 - max_dis, 4)
    return out


def _compute_file_summaries(enriched: Sequence[Dict[str, Any]], mode: str) -> List[Dict[str, Any]]:
    """Aggregate per-file summary statistics across all evaluated chunks."""
    by_file: Dict[str, List[Dict[str, Any]]] = {}
    for item in enriched:
        fname = str(item.get("file", item.get("name", "unknown")))
        by_file.setdefault(fname, []).append(item)

    summaries: List[Dict[str, Any]] = []
    for fname, items in by_file.items():
        if mode == "contradiction":
            scores = [float(r.get("noul", 0.0)) for r in items]
        elif mode == "shortlist":
            scores = [float(r.get("hybrid_score", r.get("expected_score", 0.0))) for r in items]
        elif mode == "classify":
            scores = [float(r.get("confidence", 0.0)) for r in items]
        else:
            scores = [float(r.get("composite_score", r.get("expected_score", r.get("score", 0.0)))) for r in items]

        best_idx = max(range(len(items)), key=lambda i: scores[i])
        worst_idx = min(range(len(items)), key=lambda i: scores[i])
        disagreements = [float(r.get("disagreement", 0.0)) for r in items]
        summary: Dict[str, Any] = {
            "file": fname,
            "chunks": len(items),
            "mean_score": round(sum(scores) / max(1, len(scores)), 4),
            "max_score": round(max(scores), 4),
            "min_score": round(min(scores), 4),
            "strongest_ref": items[best_idx].get("ref", fname),
            "weakest_ref": items[worst_idx].get("ref", fname),
            "max_disagreement": round(max(disagreements, default=0.0), 4),
        }
        if any("facet_scores" in r for r in items):
            facet_means: Dict[str, float] = {}
            for facet_name in FACET_WEIGHTS:
                f_vals = [
                    float(r["facet_scores"].get(facet_name, 0.0))
                    for r in items
                    if "facet_scores" in r
                ]
                if f_vals:
                    facet_means[facet_name] = round(sum(f_vals) / len(f_vals), 4)
            if facet_means:
                summary["facet_means"] = facet_means
                summary["weakest_facet"] = min(facet_means.items(), key=lambda kv: (kv[1], kv[0]))[0]
        summaries.append(summary)
    return summaries


def _select_vega_finalists(
    results: List[Dict[str, Any]],
    mode: str,
    threshold: float,
    vega_top_k: int,
    whole_file: bool,
) -> List[int]:
    if vega_top_k <= 0 or not results:
        return []
    if whole_file and len(results) <= vega_top_k:
        return list(range(len(results)))

    # Prioritize inter-encoder disagreement >= 0.15 first when ensemble jury is active
    high_disagreement = [
        i for i, r in enumerate(results) if float(r.get("disagreement", 0.0)) >= 0.15
    ]
    high_disagreement.sort(key=lambda i: float(results[i].get("disagreement", 0.0)), reverse=True)

    chosen: List[int] = []
    seen = set()
    for idx in high_disagreement:
        if idx not in seen:
            chosen.append(idx)
            seen.add(idx)
            if len(chosen) >= vega_top_k:
                return chosen

    if mode == "contradiction":
        borderline = [
            i for i, r in enumerate(results) if 0.25 <= float(r.get("noul", 0.0)) <= 0.85
        ]
        borderline.sort(key=lambda i: abs(float(results[i].get("noul", 0.0)) - threshold))
        for idx in borderline:
            if idx not in seen:
                chosen.append(idx)
                seen.add(idx)
                if len(chosen) >= vega_top_k:
                    return chosen
        by_noul = sorted(
            range(len(results)),
            key=lambda i: float(results[i].get("noul", 0.0)),
            reverse=True,
        )
        for idx in by_noul:
            if idx not in seen:
                chosen.append(idx)
                seen.add(idx)
                if len(chosen) >= vega_top_k:
                    break
        return chosen

    if mode == "classify":
        low_conf = [
            i for i, r in enumerate(results) if float(r.get("confidence", 1.0)) < 0.55
        ]
        low_conf.sort(key=lambda i: float(results[i].get("confidence", 1.0)))
        for idx in low_conf:
            if idx not in seen:
                chosen.append(idx)
                seen.add(idx)
                if len(chosen) >= vega_top_k:
                    break
        return chosen

    for idx in range(len(results)):
        if idx not in seen:
            chosen.append(idx)
            seen.add(idx)
            if len(chosen) >= vega_top_k:
                break
    return chosen


def _attach_vega_escalation(
    results: List[Dict[str, Any]],
    finalist_indices: List[int],
    questions: Dict[str, Dict[str, Any]],
    mode: str,
    vega_model: str,
    resolved_device: str,
    batch_size: int,
    resident_cache: bool,
    threshold: float = 0.55,
    whole_file: bool = False,
    views: int = 1,
    policy_path: Optional[str] = None,
) -> int:
    if not finalist_indices:
        return 0
    vega_ok, _ = _pkg_version("vegaml", "vegaml")
    if not vega_ok:
        print("[XLaya] Warning: --vega requested, but vegaml is not installed.", file=sys.stderr)
        return 0

    eff_vega_model = _resolve_vega_model(vega_model, resolved_device)
    eff_views = max(1, min(3, int(views)))
    v_key = f"vega:{eff_vega_model}"
    with _CACHE_LOCK:
        was_cached = v_key in _MODEL_CACHE

    v_agent = _load_vega_checkpoint(
        eff_vega_model,
        resolved_device,
        cache=resident_cache,
        policy_path=policy_path,
    )
    v_questions = _strip_noul_labels_for_vega(questions)
    texts = [results[i].get("_full_text") or results[i]["text"] for i in finalist_indices]

    if len(texts) == 1:
        v_preds = [v_agent.predict(texts[0], v_questions, views=eff_views)]
    else:
        v_preds = v_agent.predict_batch(
            texts,
            v_questions,
            batch_size=min(batch_size, 16),
            views=eff_views,
        )

    for idx, raw_pred in zip(finalist_indices, v_preds):
        ans = _sanitize_prediction(raw_pred).get("answers", {})
        if mode == "contradiction":
            v_rel = ans.get("is_relevant", {})
            v_cons = ans.get("is_consistent", {})
            v_con = ans.get("contradicts_ssot", {})
            p_rel = float(v_rel.get("noul", 0.0))
            p_cons = float(v_cons.get("noul", 0.0))
            p_raw = float(v_con.get("noul", 0.0))
            v_abstain = bool(v_con.get("abstain", False))
            v_pset = list(v_con.get("prediction_set", []))
            v_route = v_con.get("route")
            v_noul = round(p_rel * p_raw * (1.0 - p_cons), 4)
            if (
                whole_file
                and not v_abstain
                and v_route == "auto"
                and v_pset == ["true"]
                and p_cons < 0.40
            ):
                v_noul = max(v_noul, round(p_raw * (1.0 - p_cons), 4))
            vega_info: Dict[str, Any] = {
                "model": eff_vega_model,
                "views": eff_views,
                "route": v_route,
                "route_reason": v_con.get("route_reason"),
                "abstain": v_abstain,
                "prediction_set": v_pset,
                "noul": v_noul,
                "noul_raw": round(p_raw, 4),
                "relevance": round(p_rel, 4),
                "consistency": round(p_cons, 4),
            }
            if "view_agreement" in v_con:
                vega_info["view_agreement"] = round(float(v_con["view_agreement"]), 4)
            if "outbound" in v_con:
                vega_info["outbound"] = bool(v_con["outbound"])
                vega_info["ood_score"] = round(float(v_con.get("ood_score", 0.0)), 4)
            results[idx]["vega"] = vega_info
            if not v_abstain and v_noul >= threshold:
                results[idx]["noul"] = max(float(results[idx].get("noul", 0.0)), v_noul)
                results[idx]["flagged"] = True
        elif mode == "shortlist":
            v_rel = ans.get("rel", {})
            vega_info = {
                "model": eff_vega_model,
                "views": eff_views,
                "route": v_rel.get("route"),
                "route_reason": v_rel.get("route_reason"),
                "abstain": bool(v_rel.get("abstain", False)),
                "prediction_set": list(v_rel.get("prediction_set", [])),
                "expected_score": round(float(v_rel.get("expected_score", v_rel.get("score", 0.0))), 4),
            }
            if "view_agreement" in v_rel:
                vega_info["view_agreement"] = round(float(v_rel["view_agreement"]), 4)
            if "outbound" in v_rel:
                vega_info["outbound"] = bool(v_rel["outbound"])
                vega_info["ood_score"] = round(float(v_rel.get("ood_score", 0.0)), 4)
            results[idx]["vega"] = vega_info
        elif mode == "classify":
            v_cat = ans.get("cat", {})
            vega_info = {
                "model": eff_vega_model,
                "views": eff_views,
                "route": v_cat.get("route"),
                "route_reason": v_cat.get("route_reason"),
                "abstain": bool(v_cat.get("abstain", False)),
                "prediction_set": list(v_cat.get("prediction_set", [])),
                "choice": v_cat.get("choice"),
            }
            if "view_agreement" in v_cat:
                vega_info["view_agreement"] = round(float(v_cat["view_agreement"]), 4)
            if "outbound" in v_cat:
                vega_info["outbound"] = bool(v_cat["outbound"])
                vega_info["ood_score"] = round(float(v_cat.get("ood_score", 0.0)), 4)
            results[idx]["vega"] = vega_info
        else:
            if any(f"facet_{f}" in ans for f in FACET_WEIGHTS):
                v_fb = _extract_facet_breakdown(ans)
                first_f = ans.get("facet_specificity", {})
                vega_info = {
                    "model": eff_vega_model,
                    "views": eff_views,
                    "route": first_f.get("route"),
                    "route_reason": first_f.get("route_reason"),
                    "abstain": any(bool(ans.get(f"facet_{f}", {}).get("abstain", False)) for f in FACET_WEIGHTS),
                    "prediction_set": list(first_f.get("prediction_set", [])),
                    "expected_score": v_fb["composite_score"],
                    "facet_scores": v_fb["facet_scores"],
                    "weakest_facet": v_fb["weakest_facet"],
                }
                v_agrees = [
                    float(ans[f"facet_{f}"]["view_agreement"])
                    for f in FACET_WEIGHTS
                    if f"facet_{f}" in ans and "view_agreement" in ans[f"facet_{f}"]
                ]
                if v_agrees:
                    vega_info["view_agreement"] = round(sum(v_agrees) / len(v_agrees), 4)
                if "outbound" in first_f:
                    vega_info["outbound"] = bool(first_f["outbound"])
                    vega_info["ood_score"] = round(float(first_f.get("ood_score", 0.0)), 4)
            else:
                v_rub = ans.get("rubric", {})
                vega_info = {
                    "model": eff_vega_model,
                    "views": eff_views,
                    "route": v_rub.get("route"),
                    "route_reason": v_rub.get("route_reason"),
                    "abstain": bool(v_rub.get("abstain", False)),
                    "prediction_set": list(v_rub.get("prediction_set", [])),
                    "expected_score": round(float(v_rub.get("expected_score", v_rub.get("score", 0.0))), 4),
                }
                if "view_agreement" in v_rub:
                    vega_info["view_agreement"] = round(float(v_rub["view_agreement"]), 4)
                if "outbound" in v_rub:
                    vega_info["outbound"] = bool(v_rub["outbound"])
                    vega_info["ood_score"] = round(float(v_rub.get("ood_score", 0.0)), 4)
            if "contradicts_ssot" in ans and "is_relevant" in ans:
                p_rel = float(ans["is_relevant"].get("noul", 0.0))
                p_cons = float(ans.get("is_consistent", {}).get("noul", 0.0))
                p_raw = float(ans["contradicts_ssot"].get("noul", 0.0))
                vega_info["noul"] = round(p_rel * p_raw * (1.0 - p_cons), 4)
            results[idx]["vega"] = vega_info

    if not resident_cache and not was_cached:
        del v_agent
        gc.collect()

    return len(finalist_indices)


def run_triage(
    paths: Sequence[str],
    mode: str = "rubric",
    query: str = "",
    ssot: str = "",
    true_desc: str = "",
    false_desc: str = "",
    labels_spec: str = "",
    noul_labels: str = "",
    lang: str = "auto",
    device: str = "auto",
    profile: str = "auto",
    agent_tier: str = "auto",
    sieve_weights: Optional[Union[str, Path, Mapping[str, Any]]] = None,
    max_chars: int = 1600,
    whole_file: bool = False,
    max_chunks: int = 2048,
    top_k: Optional[int] = None,
    threshold: float = 0.55,
    batch_size: int = 32,
    pattern: str = DEFAULT_PATTERN,
    lexical_prefilter: int = 0,
    vega: bool = False,
    vega_model: str = "auto",
    vega_top_k: int = 10,
    views: int = 1,
    thorough: bool = False,
    rubric_preset: str = "default",
    policy_path: Optional[str] = None,
    resident_cache: bool = True,
) -> Dict[str, Any]:
    """Execute the full 3-stage Stage 0 → Stage 1 → Stage 2 semantic triage cascade."""
    t0 = time.perf_counter()

    if mode not in VALID_MODES:
        raise ValueError(f"Unsupported mode {mode!r}; expected one of {sorted(VALID_MODES)}.")
    if mode == "shortlist" and not query.strip():
        raise ValueError("Mode 'shortlist' requires a non-empty query (--query).")
    if mode == "contradiction" and not ssot.strip():
        raise ValueError("Mode 'contradiction' requires a non-empty canonical SSOT statement (--ssot).")
    if lang not in ("auto", "en", "multi", "typed", "ensemble"):
        raise ValueError(
            f"Unsupported lang {lang!r}; expected 'auto', 'en', 'multi', 'typed', or 'ensemble'."
        )
    if rubric_preset not in RUBRIC_PRESETS:
        raise ValueError(
            f"Unsupported rubric_preset {rubric_preset!r}; expected one of {sorted(RUBRIC_PRESETS)}."
        )

    hw = _resolve_hardware_profile(profile=profile, agent_tier=agent_tier, device=device)
    eff_views = max(1, min(3, int(views)))
    if hw["profile"] == "max" and vega and int(views) == 1:
        eff_views = 3
        vega_top_k = max(vega_top_k, 20)
        if batch_size == 32:
            batch_size = 64
    elif hw["profile"] == "edge":
        vega = False
        batch_size = min(batch_size, hw["batch_size_cap"])
        if lang == "ensemble":
            lang = "typed"
    elif hw["profile"] == "nano":
        vega = False

    if thorough:
        max_chunks = max(max_chunks, 4096)
        lexical_prefilter = 0

    noul_label_map = parse_noul_labels(noul_labels)
    labels_dict = parse_label_spec(labels_spec)

    has_sieve_arg = sieve_weights is not None and (
        isinstance(sieve_weights, Mapping) or bool(str(sieve_weights).strip())
    )
    eff_pattern = pattern
    if pattern == DEFAULT_PATTERN and (
        hw["agent_tier_explicit"]
        or hw["profile"] == "nano"
        or mode == "shortlist"
        or rubric_preset == "code_audit"
        or has_sieve_arg
    ):
        eff_pattern = CODE_PATTERN

    files, scan_root = collect_target_files(paths, pattern=eff_pattern)
    if not files and pattern == DEFAULT_PATTERN and eff_pattern != CODE_PATTERN:
        eff_pattern = CODE_PATTERN
        files, scan_root = collect_target_files(paths, pattern=eff_pattern)
    if mode == "shortlist" and query.strip() and files:
        files = _prerank_repo_files(files, scan_root, query)

    if not files:
        return {
            "ok": True,
            "meta": {
                "version": __version__,
                "profile": hw["profile"],
                "agent_tier": hw["agent_tier"],
                "mode": mode,
                "thorough": thorough,
                "rubric_preset": rubric_preset if mode == "rubric" else None,
                "files_scanned": 0,
                "chunks_evaluated": 0,
                "truncated_chunks": 0,
                "vega_escalated": 0,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            },
            "results": [],
        }

    all_chunks: List[Dict[str, Any]] = []
    truncated_chunks = 0
    hard_cap = max(max_chunks + 1, max_chunks * 4)

    for fpath in files:
        rel_pfx = _rel_ref_prefix(fpath, scan_root)
        remaining_hint = max(0, hard_cap - len(all_chunks))
        extracted = chunk_file(
            fpath,
            max_chars=max_chars,
            whole_file=whole_file,
            rel_prefix=rel_pfx,
            limit_hint=remaining_hint,
        )
        all_chunks.extend(extracted)
        if len(all_chunks) >= hard_cap:
            break

    if len(all_chunks) > max_chunks:
        truncated_chunks = len(all_chunks) - max_chunks
        all_chunks = all_chunks[:max_chunks]
        print(
            f"[XLaya] Warning: chunk count exceeded max_chunks={max_chunks}; "
            f"truncated {truncated_chunks}+ trailing chunks.",
            file=sys.stderr,
        )

    if not all_chunks:
        return {
            "ok": True,
            "meta": {
                "version": __version__,
                "profile": hw["profile"],
                "agent_tier": hw["agent_tier"],
                "mode": mode,
                "thorough": thorough,
                "rubric_preset": rubric_preset if mode == "rubric" else None,
                "files_scanned": len(files),
                "chunks_evaluated": 0,
                "truncated_chunks": truncated_chunks,
                "vega_escalated": 0,
                "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            },
            "results": [],
        }

    lex_target = query if mode in ("shortlist", "classify", "rubric") and query else (ssot or query)
    lex_scores = compute_lexical_scores(all_chunks, lex_target)
    for ch, lx in zip(all_chunks, lex_scores):
        ch["lexical_score"] = lx

    prefiltered_from: Optional[int] = None
    if lexical_prefilter > 0 and len(all_chunks) > lexical_prefilter and lex_target.strip():
        prefiltered_from = len(all_chunks)
        ranked_indices = sorted(
            range(len(all_chunks)),
            key=lambda i: (all_chunks[i]["lexical_score"], -i),
            reverse=True,
        )[:lexical_prefilter]
        ranked_indices.sort()
        all_chunks = [all_chunks[i] for i in ranked_indices]

    if hw["stage0_only"]:
        laya_ok, laya_ver = False, None
        resolved_device = "cpu"
    else:
        laya_ok, laya_ver = _pkg_version("laya", "laya")
        resolved_device = (
            hw["device"]
            if (hw["profile_explicit"] and (device or "auto").strip().lower() in ("", "auto"))
            else (_resolve_device(device) if laya_ok else "cpu")
        )

    questions = _build_mode_questions(
        mode=mode,
        query=query,
        ssot=ssot,
        true_desc=true_desc,
        false_desc=false_desc,
        labels=labels_dict,
        noul_label_map=noul_label_map,
        thorough=thorough,
        rubric_preset=rubric_preset,
    )

    if not laya_ok:
        sieve_meta_extra: Dict[str, Any] = {}
        if mode == "shortlist":
            genomes_bundle, g_src = load_sieve_genomes(sieve_weights)
            g_key = "31b_deep" if hw["agent_tier"] == "31b-deep" else "e4b_sniper_distilled"
            g_cfg = dict(genomes_bundle if "w_core" in genomes_bundle else genomes_bundle[g_key])
            if "gamma_max" not in g_cfg and isinstance(genomes_bundle, Mapping) and "gamma_max" in genomes_bundle:
                g_cfg["gamma_max"] = genomes_bundle["gamma_max"]
            feat_mat = extract_code_graph_features(all_chunks, query)
            m_avail = compute_channel_availability(all_chunks, feat_mat)
            sel_top = top_k if (top_k is not None and top_k > 0) else (
                hw["default_top_k"] if (hw["agent_tier_explicit"] or hw["profile"] == "nano") else 10
            )
            sel_bud = hw["token_budget"] if (hw["agent_tier_explicit"] or hw["profile"] == "nano") else 100000
            sel_idxs, core_sc, probs, used_tok = _select_sieve_slots(
                all_chunks,
                feat_mat,
                g_cfg,
                agent_tier=hw["agent_tier"],
                top_k=sel_top,
                max_tokens=sel_bud,
                m_avail=m_avail,
            )
            q_hat = float(g_cfg.get("conformal_q_hat", 0.45))
            top1_prob = probs[sel_idxs[0]] if sel_idxs else 0.0
            max_prob = max((probs[i] for i in sel_idxs), default=0.0)
            abstain = bool(top1_prob < (1.0 - q_hat))
            sieve_meta_extra = {
                "top1_probability": round(top1_prob, 4),
                "max_probability": round(max_prob, 4),
                "conformal_q_hat": round(q_hat, 4),
                "abstain": abstain,
                "route": "review" if abstain else "auto",
                "m_avail": [round(x, 4) for x in m_avail],
            }
            sel_rank = {idx: pos for pos, idx in enumerate(sel_idxs)}
            enriched = []
            ordered_all = list(sel_idxs) + [i for i in range(len(all_chunks)) if i not in sel_rank]
            for i in ordered_all:
                ch = all_chunks[i]
                pr_val = round(probs[i], 4)
                exp_sc = round(4.0 * pr_val, 4)
                item = dict(ch)
                item.update(
                    {
                        "engine": "xlaya-nano-sieve" if hw["profile"] == "nano" else "pure-python-fallback",
                        "score": exp_sc,
                        "expected_score": exp_sc,
                        "sieve_score": round(core_sc[i], 4),
                        "hybrid_score": round(
                            (1.0 + 0.01 * (len(sel_idxs) - sel_rank[i])) * pr_val
                            if i in sel_rank
                            else 0.5 * pr_val,
                            4,
                        ),
                        "noul": 0.0,
                        "confidence": pr_val,
                        "selected_slot": (sel_rank[i] + 1) if i in sel_rank else None,
                    }
                )
                enriched.append(item)
            if hw["agent_tier_explicit"] or hw["profile"] == "nano":
                top_k = len(sel_idxs)
        else:
            enriched = fallback_evaluate(all_chunks, mode, query, ssot, labels_dict, threshold=threshold)
            if hw["profile"] == "nano":
                for item in enriched:
                    item["engine"] = "xlaya-nano-sieve"
            g_src = "stage0_fallback"
            used_tok = sum(max(1, int(round(_estimate_tokens(c["text"])))) for c in all_chunks[:10])
        if thorough and mode == "rubric":
            for item in enriched:
                base_sc = float(item.get("expected_score", item.get("score", 2.0)))
                item["facet_scores"] = {f: round(base_sc, 4) for f in FACET_WEIGHTS}
                item["facet_min"] = round(base_sc, 4)
                item["facet_spread"] = 0.0
                item["weakest_facet"] = "specificity"
                item["composite_score"] = round(base_sc, 4)
        meta: Dict[str, Any] = {
            "version": __version__,
            "profile": hw["profile"],
            "agent_tier": hw["agent_tier"],
            "genome_source": g_src,
            "selected_tokens": used_tok,
            "laya_available": False,
            "laya_version": None,
            "model": "xlaya-nano-sieve" if hw["profile"] == "nano" else "pure-python-fallback",
            "language_route": "nano" if hw["profile"] == "nano" else "fallback",
            "language_routing": {
                "english": 0,
                "multilingual": 0,
                "typed_decisions": 0,
                "ensemble": 0,
                "head_guard_multilingual": False,
            },
            "device": "cpu",
            "mode": mode,
            "thorough": thorough,
            "rubric_preset": rubric_preset if mode == "rubric" else None,
            "files_scanned": len(files),
            "chunks_evaluated": len(enriched),
            "truncated_chunks": truncated_chunks,
            "vega_escalated": 0,
        }
        meta.update(sieve_meta_extra)
        if prefiltered_from is not None:
            meta["lexical_prefiltered_from"] = prefiltered_from
    else:
        head_txt = _questions_head_text(questions)
        head_is_en = _is_english_text(head_txt)

        en_idxs: List[int] = []
        ml_idxs: List[int] = []
        typed_idxs: List[int] = []
        ens_en_idxs: List[int] = []
        ens_ml_idxs: List[int] = []

        if lang == "en":
            en_idxs = list(range(len(all_chunks)))
        elif lang == "multi":
            ml_idxs = list(range(len(all_chunks)))
        elif lang == "typed":
            typed_idxs = list(range(len(all_chunks)))
        elif lang == "ensemble":
            if not head_is_en:
                ens_ml_idxs = list(range(len(all_chunks)))
            else:
                for idx, ch in enumerate(all_chunks):
                    is_py = str(ch.get("name", "")).lower().endswith((".py", ".pyi"))
                    is_en_ch = (not NON_ENGLISH_SCRIPT_RE.search(ch["text"])) if is_py else _is_english_text(ch["text"])
                    if is_en_ch:
                        ens_en_idxs.append(idx)
                    else:
                        ens_ml_idxs.append(idx)
        elif not head_is_en:
            ml_idxs = list(range(len(all_chunks)))
        else:
            for idx, ch in enumerate(all_chunks):
                is_py = str(ch.get("name", "")).lower().endswith((".py", ".pyi"))
                is_en_ch = (not NON_ENGLISH_SCRIPT_RE.search(ch["text"])) if is_py else _is_english_text(ch["text"])
                if is_en_ch:
                    en_idxs.append(idx)
                else:
                    ml_idxs.append(idx)

        preds_by_idx: List[Optional[Tuple[Dict[str, Any], str]]] = [None] * len(all_chunks)
        needs_tournament = mode == "classify" and len(labels_dict) > 20

        # Standard single-checkpoint buckets (english, multilingual, typed-decisions)
        for bucket_name, b_idxs, model_tag in (
            ("english", en_idxs, "convaiinnovations/laya"),
            ("multilingual", ml_idxs, "convaiinnovations/laya (multilingual)"),
            ("typed-decisions", typed_idxs, "convaiinnovations/laya (typed-decisions)"),
        ):
            if not b_idxs:
                continue
            with _CACHE_LOCK:
                already_cached = bucket_name in _MODEL_CACHE
            agent = _load_laya_checkpoint(bucket_name, resolved_device, cache=resident_cache)
            b_texts = [all_chunks[i]["text"] for i in b_idxs]
            b_preds = _run_laya_agent_on_states(
                agent,
                b_texts,
                questions,
                needs_tournament=needs_tournament,
                batch_size=batch_size,
            )
            for orig_i, pr in zip(b_idxs, b_preds):
                preds_by_idx[orig_i] = (pr, model_tag)

            if not resident_cache and not already_cached:
                with _CACHE_LOCK:
                    _MODEL_CACHE.pop(bucket_name, None)
                del agent
                gc.collect()

        # Ensemble Jury buckets (english + typed-decisions OR multilingual + typed-decisions)
        if ens_en_idxs or ens_ml_idxs:
            with _CACHE_LOCK:
                td_was_cached = "typed-decisions" in _MODEL_CACHE
            agent_td = _load_laya_checkpoint("typed-decisions", resolved_device, cache=resident_cache)

            for primary_bucket, e_idxs, w_pri, w_td, ens_tag in (
                (
                    "english",
                    ens_en_idxs,
                    0.45,
                    0.55,
                    "convaiinnovations/laya (ensemble:en+typed-decisions)",
                ),
                (
                    "multilingual",
                    ens_ml_idxs,
                    0.75,
                    0.25,
                    "convaiinnovations/laya (ensemble:multilingual+typed-decisions)",
                ),
            ):
                if not e_idxs:
                    continue
                with _CACHE_LOCK:
                    pri_was_cached = primary_bucket in _MODEL_CACHE
                agent_pri = _load_laya_checkpoint(primary_bucket, resolved_device, cache=resident_cache)
                e_texts = [all_chunks[i]["text"] for i in e_idxs]
                preds_pri = _run_laya_agent_on_states(
                    agent_pri,
                    e_texts,
                    questions,
                    needs_tournament=needs_tournament,
                    batch_size=batch_size,
                )
                preds_td = _run_laya_agent_on_states(
                    agent_td,
                    e_texts,
                    questions,
                    needs_tournament=needs_tournament,
                    batch_size=batch_size,
                )
                for orig_i, p1, p2 in zip(e_idxs, preds_pri, preds_td):
                    blended = _blend_two_predictions(
                        _sanitize_prediction(p1),
                        _sanitize_prediction(p2),
                        questions,
                        w_a=w_pri,
                        w_b=w_td,
                    )
                    preds_by_idx[orig_i] = (blended, ens_tag)

                if not resident_cache and not pri_was_cached:
                    with _CACHE_LOCK:
                        _MODEL_CACHE.pop(primary_bucket, None)
                    del agent_pri
                    gc.collect()

            if not resident_cache and not td_was_cached:
                with _CACHE_LOCK:
                    _MODEL_CACHE.pop("typed-decisions", None)
                del agent_td
                gc.collect()

        enriched = []
        for ch, entry in zip(all_chunks, preds_by_idx):
            assert entry is not None
            pred, model_tag = entry
            ans = pred["answers"]
            item = dict(ch)
            item["engine"] = model_tag
            lex_val = float(ch.get("lexical_score", 0.0))

            if mode == "shortlist":
                rel_ans = ans["rel"]
                exp_s = float(rel_ans.get("expected_score", rel_ans["score"]))
                exp_round = round(exp_s, 4)
                hyb = round(0.82 * (exp_s / 4.0) + 0.18 * lex_val, 4)
                item["score"] = exp_round
                item["expected_score"] = exp_round
                item["lexical_score"] = round(lex_val, 4)
                item["hybrid_score"] = hyb
                item["confidence"] = round(float(rel_ans["confidence"]), 4)
                if "disagreement" in rel_ans:
                    item["disagreement"] = round(float(rel_ans["disagreement"]), 4)
                    item["model_agreement"] = round(float(rel_ans["model_agreement"]), 4)
            elif mode == "contradiction":
                p_rel = float(ans["is_relevant"]["noul"])
                p_cons = float(ans.get("is_consistent", {}).get("noul", 0.0))
                p_raw = float(ans["contradicts_ssot"]["noul"])
                eff_rel = (
                    max(p_rel, 0.85)
                    if (
                        p_rel < 0.35
                        and p_cons < 0.15
                        and p_raw >= 0.75
                        and _shares_specific_identifier(ch["text"], ssot)
                    )
                    else p_rel
                )
                p_eff = round(eff_rel * p_raw * (1.0 - p_cons), 4)
                item["noul"] = p_eff
                item["noul_raw"] = round(p_raw, 4)
                item["relevance"] = round(eff_rel, 4)
                item["consistency"] = round(p_cons, 4)
                item["flagged"] = bool(p_eff >= threshold)
                item["confidence"] = round(float(ans["contradicts_ssot"]["confidence"]), 4)
                if "disagreement" in ans["contradicts_ssot"]:
                    max_dis = max(
                        float(ans["is_relevant"].get("disagreement", 0.0)),
                        float(ans.get("is_consistent", {}).get("disagreement", 0.0)),
                        float(ans["contradicts_ssot"].get("disagreement", 0.0)),
                    )
                    item["disagreement"] = round(max_dis, 4)
                    item["model_agreement"] = round(1.0 - max_dis, 4)
            elif mode == "classify":
                cat_ans = ans["cat"]
                item["choice"] = cat_ans["choice"]
                item["confidence"] = round(float(cat_ans["confidence"]), 4)
                if "disagreement" in cat_ans:
                    item["disagreement"] = round(float(cat_ans["disagreement"]), 4)
                    item["model_agreement"] = round(float(cat_ans["model_agreement"]), 4)
            else:
                if thorough and any(f"facet_{f}" in ans for f in FACET_WEIGHTS):
                    fb = _extract_facet_breakdown(ans)
                    item["score"] = fb["composite_score"]
                    item["expected_score"] = fb["composite_score"]
                    item["composite_score"] = fb["composite_score"]
                    item["facet_scores"] = fb["facet_scores"]
                    item["facet_min"] = fb["facet_min"]
                    item["facet_spread"] = fb["facet_spread"]
                    item["weakest_facet"] = fb["weakest_facet"]
                    item["confidence"] = fb["confidence"]
                    if "disagreement" in fb:
                        item["disagreement"] = fb["disagreement"]
                        item["model_agreement"] = fb["model_agreement"]
                else:
                    rub_ans = ans["rubric"]
                    exp_s = float(rub_ans.get("expected_score", rub_ans["score"]))
                    exp_round = round(exp_s, 4)
                    item["score"] = exp_round
                    item["expected_score"] = exp_round
                    item["confidence"] = round(float(rub_ans["confidence"]), 4)
                    if "disagreement" in rub_ans:
                        item["disagreement"] = round(float(rub_ans["disagreement"]), 4)
                        item["model_agreement"] = round(float(rub_ans["model_agreement"]), 4)
                if "contradicts_ssot" in ans and "is_relevant" in ans:
                    p_rel = float(ans["is_relevant"]["noul"])
                    p_cons = float(ans.get("is_consistent", {}).get("noul", 0.0))
                    p_raw = float(ans["contradicts_ssot"]["noul"])
                    p_eff = round(p_rel * p_raw * (1.0 - p_cons), 4)
                    item["noul"] = p_eff
                    item["noul_raw"] = round(p_raw, 4)
                    item["relevance"] = round(p_rel, 4)
                    item["consistency"] = round(p_cons, 4)
                else:
                    item["noul"] = 0.0
            enriched.append(item)

        if lang == "typed":
            lang_route = "typed-decisions"
            model_summary = "convaiinnovations/laya (typed-decisions)"
        elif lang == "ensemble":
            lang_route = (
                "ensemble(en+typed)"
                if not ens_ml_idxs
                else ("ensemble(multi+typed)" if not ens_en_idxs else "ensemble(bilingual+typed)")
            )
            model_summary = (
                "convaiinnovations/laya (ensemble:en+typed-decisions)"
                if not ens_ml_idxs
                else (
                    "convaiinnovations/laya (ensemble:multilingual+typed-decisions)"
                    if not ens_en_idxs
                    else "convaiinnovations/laya (ensemble:en+multi+typed-decisions)"
                )
            )
        else:
            lang_route = (
                "english"
                if not ml_idxs
                else ("multilingual" if not en_idxs else "bilingual(per-chunk)")
            )
            model_summary = (
                "convaiinnovations/laya"
                if not ml_idxs
                else (
                    "convaiinnovations/laya (multilingual)"
                    if not en_idxs
                    else "convaiinnovations/laya (en+multilingual)"
                )
            )
        meta = {
            "version": __version__,
            "profile": hw["profile"],
            "agent_tier": hw["agent_tier"],
            "laya_available": True,
            "laya_version": laya_ver,
            "model": model_summary,
            "language_route": lang_route,
            "language_routing": {
                "english": len(en_idxs) + len(ens_en_idxs),
                "multilingual": len(ml_idxs) + len(ens_ml_idxs),
                "typed_decisions": len(typed_idxs) + len(ens_en_idxs) + len(ens_ml_idxs),
                "ensemble": len(ens_en_idxs) + len(ens_ml_idxs),
                "head_guard_multilingual": (not head_is_en and lang in ("auto", "ensemble")),
            },
            "device": resolved_device,
            "mode": mode,
            "thorough": thorough,
            "rubric_preset": rubric_preset if mode == "rubric" else None,
            "files_scanned": len(files),
            "chunks_evaluated": len(enriched),
            "truncated_chunks": truncated_chunks,
            "vega_escalated": 0,
        }
        if prefiltered_from is not None:
            meta["lexical_prefiltered_from"] = prefiltered_from

        if mode == "shortlist" and (hw["agent_tier_explicit"] or has_sieve_arg):
            genomes_bundle, g_src = load_sieve_genomes(sieve_weights)
            g_key = "31b_deep" if hw["agent_tier"] == "31b-deep" else "e4b_sniper_distilled"
            g_cfg = genomes_bundle if "w_core" in genomes_bundle else genomes_bundle[g_key]
            feat_mat = extract_code_graph_features(all_chunks, query)
            sel_top = top_k if (top_k is not None and top_k > 0) else hw["default_top_k"]
            sel_idxs, core_sc, probs, used_tok = _select_sieve_slots(
                all_chunks,
                feat_mat,
                g_cfg,
                agent_tier=hw["agent_tier"],
                top_k=sel_top,
                max_tokens=hw["token_budget"],
            )
            q_hat = float(g_cfg.get("conformal_q_hat", 0.15))
            max_prob = max((probs[i] for i in sel_idxs), default=0.0)
            abstain = bool(max_prob < (1.0 - q_hat))
            sel_rank = {idx: pos for pos, idx in enumerate(sel_idxs)}
            for idx_e, item in enumerate(enriched):
                pr_v = probs[idx_e]
                exp_v = float(item.get("expected_score", 0.0))
                item["sieve_score"] = round(core_sc[idx_e], 4)
                item["sieve_probability"] = round(pr_v, 4)
                base_hyb = 0.55 * (exp_v / 4.0) + 0.45 * pr_v
                if idx_e in sel_rank:
                    item["selected_slot"] = sel_rank[idx_e] + 1
                    item["hybrid_score"] = round(base_hyb + 0.25 - 0.005 * sel_rank[idx_e], 4)
                else:
                    item["selected_slot"] = None
                    item["hybrid_score"] = round(0.5 * base_hyb, 4)
            meta["genome_source"] = g_src
            meta["selected_tokens"] = used_tok
            meta["max_probability"] = round(max_prob, 4)
            meta["conformal_q_hat"] = round(q_hat, 4)
            meta["abstain"] = abstain
            meta["route"] = "review" if abstain else "auto"
            if top_k is None or hw["agent_tier_explicit"]:
                top_k = len(sel_idxs)

    # Mode-specific sorting (preserve selected_slot order strictly above non-selected items)
    if mode == "shortlist":
        enriched.sort(
            key=lambda r: (
                1 if r.get("selected_slot") is not None else 0,
                -(int(r["selected_slot"]) if r.get("selected_slot") is not None else 999999),
                r.get("hybrid_score", 0.0),
                r.get("expected_score", 0.0),
            ),
            reverse=True,
        )
    elif mode == "contradiction":
        enriched.sort(
            key=lambda r: (r.get("noul", 0.0), r.get("confidence", 0.0)),
            reverse=True,
        )
    elif mode == "rubric":
        enriched.sort(
            key=lambda r: (
                r.get("composite_score", r.get("expected_score", r.get("score", 0.0))),
                -r.get("noul", 0.0),
            ),
            reverse=True,
        )

    # Stage 2: Opt-in VegaML Conformal Escalation
    if vega and laya_ok and hw["vega_allowed"]:
        finalist_idxs = _select_vega_finalists(
            results=enriched,
            mode=mode,
            threshold=threshold,
            vega_top_k=vega_top_k,
            whole_file=whole_file,
        )
        meta["vega_escalated"] = _attach_vega_escalation(
            results=enriched,
            finalist_indices=finalist_idxs,
            questions=questions,
            mode=mode,
            vega_model=vega_model,
            resolved_device=resolved_device,
            batch_size=batch_size,
            resident_cache=resident_cache,
            threshold=threshold,
            whole_file=whole_file,
            views=eff_views,
            policy_path=policy_path,
        )
        meta["vega_model_resolved"] = _resolve_vega_model(vega_model, resolved_device)
        meta["vega_views"] = eff_views
        if mode == "contradiction":
            enriched.sort(
                key=lambda r: (r.get("noul", 0.0), r.get("confidence", 0.0)),
                reverse=True,
            )

    if thorough:
        meta["file_summaries"] = _compute_file_summaries(enriched, mode=mode)

    if top_k is None:
        eff_top_k = 0 if (mode == "classify" or thorough) else 10
    else:
        eff_top_k = int(top_k)

    # Mode-specific result slicing (BUG-A5)
    if mode == "contradiction":
        flagged_items = [r for r in enriched if r.get("flagged")]
        meta["flagged_count"] = len(flagged_items)
        if flagged_items:
            selected = flagged_items
        else:
            selected = enriched[:eff_top_k] if eff_top_k > 0 else (enriched if thorough else [])
    elif mode == "classify":
        selected = enriched[:eff_top_k] if eff_top_k > 0 else enriched
    else:
        selected = enriched[:eff_top_k] if eff_top_k > 0 else enriched

    clean_results = [
        {k: v for k, v in item.items() if k not in ("text", "_full_text", "_ast_meta")}
        for item in selected
    ]
    meta["results_returned"] = len(clean_results)
    meta["elapsed_ms"] = round((time.perf_counter() - t0) * 1000.0, 2)

    return {
        "ok": True,
        "meta": meta,
        "results": clean_results,
    }


# ---------------------------------------------------------------------------
# Built-in Self-Test Suite (--self-test)
# ---------------------------------------------------------------------------


def run_self_test() -> Dict[str, Any]:
    """Run deterministic + neural counter-anchor self-verification suite."""
    t0 = time.perf_counter()
    checks: Dict[str, Any] = {}

    # 1. Runtime status & thread checks
    st = get_status()
    assert st["ok"] is True and st["version"] == __version__
    assert st["cpu_threads"] >= 1
    checks["status"] = {
        "device": st["device"],
        "gpu_name": st["gpu_name"],
        "cpu_threads": st["cpu_threads"],
        "laya_version": st["laya_version"],
        "vegaml_version": st["vegaml_version"],
        "recommended_vega_model": st["recommended_vega_model"],
    }

    with tempfile.TemporaryDirectory(prefix="xlaya_selftest_") as tmp_str:
        tmp_dir = Path(tmp_str)

        # 2. 4-backtick fence safety + #{1,6} breadcrumb stack + non-duplicated heading
        md_sample = (
            "# Root Spec\n\n"
            "Intro overview paragraph with sufficient detail so it stays intact.\n\n"
            "## Chunker Engine\n\n"
            "````markdown\n"
            "```python\n"
            "# Fake Heading Inside Nested Fence\n"
            "x = 1\n"
            "```\n"
            "````\n\n"
            "#### Deep Sublevel\n\n"
            "Body under level-4 heading verifying 6-level breadcrumb tracking.\n"
        )
        f_md = tmp_dir / "subA" / "fence_test.md"
        f_md.parent.mkdir(parents=True, exist_ok=True)
        f_md.write_text(md_sample, encoding="utf-8")

        md_chunks = chunk_file(f_md, max_chars=1600)
        headings = [c["heading"] for c in md_chunks]
        assert not any("Fake Heading Inside Nested Fence" in h for h in headings), headings
        deep_chunks = [c for c in md_chunks if "Deep Sublevel" in c["heading"]]
        assert len(deep_chunks) == 1, headings
        assert deep_chunks[0]["heading"] == "Root Spec > Chunker Engine > Deep Sublevel"
        assert deep_chunks[0]["text"].startswith("[Root Spec > Chunker Engine]\n#### Deep Sublevel")

        # 3. Structured formats (.jsonl, .json, .csv, .html) + disambiguated refs
        f_jsonl = tmp_dir / "subB" / "events.jsonl"
        f_jsonl.parent.mkdir(parents=True, exist_ok=True)
        f_jsonl.write_text(
            '{"id": "ev1", "msg": "alpha"}\n\n{"id": "ev2", "msg": "beta"}\n',
            encoding="utf-8",
        )
        jl_chunks = chunk_file(f_jsonl, max_chars=1600)
        assert [c["ref"] for c in jl_chunks] == ["events.jsonl#L1-L1", "events.jsonl#L3-L3"]

        f_json = tmp_dir / "subB" / "items.json"
        f_json.write_text(json.dumps([{"id": "k1", "v": 10}, {"id": "k2", "v": 20}]), encoding="utf-8")
        js_chunks = chunk_file(f_json, max_chars=1600)
        assert [c["ref"] for c in js_chunks] == ["items.json#item-0", "items.json#item-1"]

        f_csv = tmp_dir / "subB" / "rows.csv"
        f_csv.write_text("col,val\nr1,100\nr2,200\n", encoding="utf-8")
        csv_chunks = chunk_file(f_csv, max_chars=1600)
        assert [c["ref"] for c in csv_chunks] == ["rows.csv#L2-L2", "rows.csv#L3-L3"]

        f_html = tmp_dir / "subB" / "page.html"
        f_html.write_text(
            "<h1>Main &amp; Title</h1><p>First.</p><h2>Second</h2><p>Body &lt;ok&gt;.</p>",
            encoding="utf-8",
        )
        html_chunks = chunk_file(f_html, max_chars=1600)
        assert len(html_chunks) == 2 and "<ok>" in html_chunks[1]["text"]

        files_multi, root_multi = collect_target_files([str(tmp_dir)])
        refs_multi = [_rel_ref_prefix(p, root_multi) for p in files_multi]
        assert "subA/fence_test.md" in refs_multi and "subB/events.jsonl" in refs_multi
        files_single, root_single = collect_target_files([str(f_md)])
        assert len(files_single) == 1 and root_single is None
        checks["stage0_chunker"] = "passed"

        # 4. Fail-fast validation (BUG-A6)
        for bad_kwargs in (
            {"mode": "shortlist", "query": ""},
            {"mode": "contradiction", "ssot": ""},
        ):
            raised = False
            try:
                run_triage([str(f_md)], **bad_kwargs)
            except ValueError:
                raised = True
            assert raised, f"Expected ValueError for {bad_kwargs}"
        checks["fail_fast_validation"] = "passed"

        # 5. Stage 0 Lexical Thai 3-gram + Code-Span + Subset-Safe Fallback
        thai_chunks = [
            {"text": "ระบบตรวจสอบความขัดแย้งทางความหมายสำหรับเอกสารภาษาไทยอย่างแม่นยำ"},
            {"text": "สูตรการทำอาหารต้มยำกุ้งและส่วนผสมสมุนไพรสดในครัวเรือน"},
        ]
        thai_lex = compute_lexical_scores(thai_chunks, "ตรวจสอบความขัดแย้งเอกสาร")
        assert thai_lex[0] > 0.4 and thai_lex[1] == 0.0, thai_lex

        fb_chunks = [
            {
                "file": "a.md", "name": "a.md", "heading": "Partial Consistent",
                "start_line": 1, "end_line": 2, "ref": "a.md#L1-L2",
                "text": "ModernBERT-large uses a 512-token context window for local triage.",
            },
            {
                "file": "a.md", "name": "a.md", "heading": "Conflicting Numbers",
                "start_line": 3, "end_line": 4, "ref": "a.md#L3-L4",
                "text": "ModernBERT-large uses a 128-token context window and outputs 500 LLM tokens.",
            },
        ]
        fb_res = fallback_evaluate(
            fb_chunks,
            mode="contradiction",
            query="",
            ssot="ModernBERT-large uses a 512-token context window and outputs 0 LLM tokens.",
            labels={},
            threshold=0.55,
        )
        assert fb_res[0]["flagged"] is False and fb_res[1]["flagged"] is True, fb_res
        checks["lexical_and_fallback"] = {"thai_lex": thai_lex, "subset_safe": True}

        # 6. Neural checks (when laya is installed)
        if st["laya_available"]:
            bilingual_md = (
                "# English Architecture\n\n"
                "ModernBERT executes fast local semantic classification on GPU hardware.\n\n"
                "# สถาปัตยกรรมภาษาไทย\n\n"
                "ระบบประมวลผลภาษาไทยอัตโนมัติสำหรับการคัดกรองเอกสารและตรวจสอบความถูกต้อง\n"
            )
            f_bi = tmp_dir / "bilingual.md"
            f_bi.write_text(bilingual_md, encoding="utf-8")

            bi_en_head = run_triage(
                [str(f_bi)],
                mode="shortlist",
                query="semantic classification architecture",
                lang="auto",
            )
            rt_en = bi_en_head["meta"]["language_routing"]
            assert rt_en["english"] == 1 and rt_en["multilingual"] == 1, rt_en

            bi_th_head = run_triage(
                [str(f_bi)],
                mode="shortlist",
                query="ค้นหาสถาปัตยกรรมภาษาไทย",
                lang="auto",
            )
            rt_th = bi_th_head["meta"]["language_routing"]
            assert rt_th["english"] == 0 and rt_th["multilingual"] == 2 and rt_th["head_guard_multilingual"], rt_th
            checks["bilingual_routing"] = {"en_head": rt_en, "th_head_guard": rt_th}

            # 6b. Stage 1 Ensemble Jury + Disagreement Telemetry + Thorough 4-Facet Rubric
            ens_res = predict_direct(
                state="ModernBERT-large uses a 512-token context window and outputs 0 LLM tokens.",
                questions={
                    "q": {
                        "type": "noul",
                        "instructions": "Does this text mention a 512-token context window?",
                    }
                },
                model="ensemble",
            )
            ens_q = ens_res["result"]["answers"]["q"]
            assert "disagreement" in ens_q and "model_agreement" in ens_q, ens_q
            assert abs(ens_q["disagreement"] + ens_q["model_agreement"] - 1.0) <= 1e-3, ens_q
            checks["stage1_ensemble_jury"] = {
                "noul": ens_q["noul"],
                "disagreement": ens_q["disagreement"],
                "model_agreement": ens_q["model_agreement"],
            }

            th_res = run_triage(
                [str(f_bi)],
                mode="rubric",
                thorough=True,
                rubric_preset="architecture",
                lang="en",
            )
            assert th_res["meta"]["thorough"] is True
            assert len(th_res["meta"].get("file_summaries", [])) == 1
            first_th = th_res["results"][0]
            assert set(first_th["facet_scores"].keys()) == set(FACET_WEIGHTS.keys())
            checks["thorough_4facet_rubric"] = {
                "composite_score": first_th["composite_score"],
                "weakest_facet": first_th["weakest_facet"],
                "file_mean": th_res["meta"]["file_summaries"][0]["mean_score"],
            }

            # 7. Hybrid shortlist verification
            sh_item = bi_en_head["results"][0]
            expected_hyb = round(
                0.82 * (sh_item["expected_score"] / 4.0) + 0.18 * sh_item["lexical_score"],
                4,
            )
            assert sh_item["hybrid_score"] == expected_hyb, sh_item
            checks["hybrid_shortlist"] = sh_item["hybrid_score"]

            # 8. Counter-Anchor Contradiction Test: A_pos ∧ A_neg
            f_pos = tmp_dir / "pos_skill.md"
            f_pos.write_text(
                "# XLaya Semantic Decision & Conformal Triage Sidecar (`/xlaya` v2.1)\n\n"
                "Unlike System 2 LLMs that iterate across multi-step tool loops, `laya` executes a "
                "deterministic encoder forward pass (`output_tokens: 0`) using ModernBERT-large's "
                "512-token context window (not 128 tokens) with 0 LLM output tokens.\n",
                encoding="utf-8",
            )
            pos_target = f_pos

            ssot_claim = "ModernBERT-large has a 128-token context window and outputs 500 LLM tokens."
            res_pos = run_triage([str(pos_target)], mode="contradiction", ssot=ssot_claim, threshold=0.55)
            pos_flagged = [r for r in res_pos["results"] if r.get("flagged")]
            assert len(pos_flagged) >= 1 and pos_flagged[0]["noul"] >= 0.55, res_pos

            f_neg = tmp_dir / "unrelated_ops.md"
            f_neg.write_text(
                "# Cloud Dataproc & Airflow\n\n"
                "Provision PySpark clusters on Dataproc Serverless with autoscaling workers and "
                "schedule daily Apache Airflow DAGs in Cloud Composer.\n\n"
                "# Windows UIA Ghost Mouse\n\n"
                "Dispatch background Win32 mouse click events via UI Automation tree handles "
                "without moving the physical desktop cursor.\n",
                encoding="utf-8",
            )
            res_neg = run_triage([str(f_neg)], mode="contradiction", ssot=ssot_claim, threshold=0.55, top_k=5)
            neg_max = max((r["noul"] for r in res_neg["results"]), default=0.0)
            assert res_neg["meta"]["flagged_count"] == 0 and neg_max < 0.25, res_neg

            consistent_ssot = (
                "ModernBERT-large uses a 512-token context window and outputs 0 LLM tokens, "
                "while vega-U supports up to 73,728 tokens."
            )
            res_con = run_triage(
                [str(pos_target)], mode="contradiction", ssot=consistent_ssot, threshold=0.55, top_k=5
            )
            assert res_con["meta"]["flagged_count"] == 0, res_con
            checks["contradiction_anchors"] = {
                "a_pos_max_noul": pos_flagged[0]["noul"],
                "a_pos_flagged": len(pos_flagged),
                "a_con_flagged": res_con["meta"]["flagged_count"],
                "a_neg_max_noul": neg_max,
                "a_neg_flagged": res_neg["meta"]["flagged_count"],
            }

            # 9. >20 labels tournament routing (24 labels via predict_tournament)
            many_labels = {f"topic_{i:02d}": f"Category {i} unrelated domain" for i in range(23)}
            many_labels["gpu_cuda_inference"] = "GPU CUDA neural model inference and PyTorch batching"
            tourn_res = predict_direct(
                state="PyTorch executes batched neural model inference on an NVIDIA CUDA GPU.",
                questions={
                    "cat": {
                        "type": "choice",
                        "instructions": "Select the matching technical category.",
                        "criteria": many_labels,
                    }
                },
                model="en",
            )
            assert tourn_res["ok"] is True
            assert "tournament" in tourn_res["result"]
            assert tourn_res["result"]["answers"]["cat"]["choice"] in many_labels
            checks["tournament_24_labels"] = {
                "winner": tourn_res["result"]["answers"]["cat"]["choice"],
                "rounds": tourn_res["result"]["tournament"]["cat"]["rounds"],
            }

            # 10. Vega conformal + multi-view debiasing smoke check (when vegaml is installed)
            if st["vegaml_available"]:
                vega_res = predict_direct(
                    state="ModernBERT-large uses a 512-token context window.",
                    questions={
                        "chk": {
                            "type": "noul",
                            "instructions": "Does this text mention a 512-token context window?",
                        }
                    },
                    vega=True,
                    vega_model="0.8b",
                    views=2,
                )
                v_ans = vega_res["result"]["answers"]["chk"]
                assert "unbound" not in v_ans
                for req_key in ("prediction_set", "abstain", "route", "route_reason", "view_agreement"):
                    assert req_key in v_ans, v_ans
                checks["vega_conformal"] = {
                    "route": v_ans["route"],
                    "abstain": v_ans["abstain"],
                    "prediction_set": v_ans["prediction_set"],
                    "view_agreement": v_ans["view_agreement"],
                }

        # 11. v2.2.0 Pure-Python AST Code-Graph Sieve & Profile/Tier Gate (always runs, 0 torch needed)
        code_dir = tmp_dir / "mini_repo"
        (code_dir / "security").mkdir(parents=True, exist_ok=True)
        (code_dir / "routers").mkdir(parents=True, exist_ok=True)
        (code_dir / "tests").mkdir(parents=True, exist_ok=True)
        (code_dir / "security" / "oauth.py").write_text(
            "def decode_jwt_token(raw_token: str) -> dict:\n"
            "    if not raw_token or '.' not in raw_token:\n"
            "        raise ValueError('MalformedBearerTokenError: missing JWT segments')\n"
            "    return {'sub': raw_token.split('.')[0]}\n\n"
            "async def verify_current_user(token: str) -> dict:\n"
            "    return decode_jwt_token(token)\n",
            encoding="utf-8",
        )
        (code_dir / "routers" / "users.py").write_text(
            "from security.oauth import verify_current_user\n\n"
            "def Depends(dep):\n"
            "    return dep\n\n"
            "async def get_profile_endpoint(user: dict = Depends(verify_current_user)) -> dict:\n"
            "    return {'profile': user}\n",
            encoding="utf-8",
        )
        (code_dir / "tests" / "test_oauth.py").write_text(
            "from security.oauth import decode_jwt_token\n\n"
            "def test_decode_jwt_token_malformed():\n"
            "    # Mentions MalformedBearerTokenError and get_profile_endpoint in test fixture\n"
            "    assert decode_jwt_token('alice.sig')['sub'] == 'alice'\n",
            encoding="utf-8",
        )
        (code_dir / "unrelated_billing.py").write_text(
            "def compute_invoice_vat(subtotal: float) -> float:\n"
            "    return round(subtotal * 0.07, 2)\n",
            encoding="utf-8",
        )

        sieve_q = (
            "Traceback in get_profile_endpoint: MalformedBearerTokenError raised during "
            "Depends(verify_current_user) token validation"
        )
        nano_triage = run_triage(
            [str(code_dir)],
            mode="shortlist",
            query=sieve_q,
            profile="nano",
            agent_tier="e4b-sniper",
            top_k=4,
        )
        assert nano_triage["meta"]["profile"] == "nano", nano_triage["meta"]
        assert nano_triage["meta"]["agent_tier"] == "e4b-sniper", nano_triage["meta"]
        assert nano_triage["meta"]["files_scanned"] == 4, nano_triage["meta"]
        assert "abstain" in nano_triage["meta"] and nano_triage["meta"]["route"] in ("auto", "review")
        top_files = [r["file"] for r in nano_triage["results"][:2]]
        assert any("oauth.py" in f for f in top_files) and any("users.py" in f for f in top_files), top_files

        mm_blocked = False
        try:
            predict_direct(questions={"q": {"type": "noul", "instructions": "x"}}, image="dummy.png", profile="nano")
        except ValueError:
            mm_blocked = True
        assert mm_blocked, "predict_direct(..., profile='nano', image=...) must reject multimodal without torch"

        nano_pred = predict_direct(
            state="Raised MalformedBearerTokenError in decode_jwt_token when bearer header was empty.",
            questions={
                "kind": {
                    "type": "choice",
                    "instructions": "Classify the software defect category.",
                    "criteria": {
                        "auth_bug": "JWT bearer token authentication validation failure",
                        "billing": "Invoice VAT tax rounding calculation",
                    },
                },
                "sev": {
                    "type": "score",
                    "instructions": "Score relevance to authentication token validation.",
                },
                "has_err": {
                    "type": "noul",
                    "instructions": "Does this report mention MalformedBearerTokenError?",
                },
            },
            profile="nano",
        )
        assert nano_pred["ok"] is True and nano_pred["profile"] == "nano", nano_pred
        assert nano_pred["result"]["answers"]["kind"]["choice"] == "auth_bug", nano_pred
        assert nano_pred["result"]["answers"]["has_err"]["noul"] > 0.5, nano_pred

        proj_w = project_sieve_weights_simplex([0.4, 0.3, 0.2, 0.2, 0.1, 0.1, 0.5, 0.2])
        assert proj_w[6] <= 0.0 and abs(sum(abs(x) for x in proj_w) - 1.0) <= 1e-4, proj_w
        checks["v22_profiles_and_code_sieve"] = {
            "nano_top2_files": top_files,
            "nano_choice": nano_pred["result"]["answers"]["kind"]["choice"],
            "nano_multimodal_guarded": mm_blocked,
            "simplex_l1": round(sum(abs(x) for x in proj_w), 6),
        }

        # 12. v2.3.0 Cross-Regime Sieve, Skeleton Header, Token Wall & 2-Stage Tool Gate
        sieve_r2 = sieve_code_graph([str(code_dir)], sieve_q, agent_tier="e4b-sniper")
        assert sieve_r2["ok"] is True and sieve_r2["meta"]["selected_tokens"] <= 800, sieve_r2["meta"]
        assert len(sieve_r2["meta"]["m_avail"]) == 8, sieve_r2["meta"]
        tc_hit = triage_tool_call(
            "Convert RGB color code 255, 0, 0 to CMYK.",
            [
                {
                    "name": "rgb_to_cmyk",
                    "description": "Converts an RGB color code to CMYK.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "r": {"type": "int", "description": "Red component (0-255)"},
                            "g": {"type": "int", "description": "Green component (0-255)"},
                            "b": {"type": "int", "description": "Blue component (0-255)"},
                        },
                        "required": ["r", "g", "b"],
                    },
                }
            ],
        )
        tc_miss = triage_tool_call(
            "What is the capital of France?",
            [
                {
                    "name": "rgb_to_cmyk",
                    "description": "Converts an RGB color code to CMYK.",
                    "parameters": {
                        "type": "object",
                        "properties": {"r": {"type": "int"}},
                        "required": ["r"],
                    },
                }
            ],
        )
        assert tc_hit["abstain"] is False and tc_hit["decision"] == "tool_call", tc_hit
        assert tc_miss["abstain"] is True and tc_miss["decision"] in ("cannot_answer", "request_for_info"), tc_miss
        checks["v23_cross_regime_and_tool_gate"] = {
            "sieve_selected_tokens": sieve_r2["meta"]["selected_tokens"],
            "tool_hit_prob": tc_hit["tool_probability"],
            "tool_miss_decision": tc_miss["decision"],
        }

    return {
        "ok": True,
        "version": __version__,
        "checks": checks,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 2),
    }


# ---------------------------------------------------------------------------
# CLI Interface
# ---------------------------------------------------------------------------


def _print_human_report(payload: Dict[str, Any], args: argparse.Namespace) -> None:
    meta = payload["meta"]
    shown = payload["results"]
    vega_part = f" | vega_escalated={meta.get('vega_escalated', 0)}" if args.vega else ""
    thorough_part = f" | thorough({meta.get('rubric_preset')})" if meta.get("thorough") else ""
    profile_part = f" | profile={meta.get('profile')}" if meta.get("profile") else ""
    tier_part = f" | tier={meta.get('agent_tier')}" if meta.get("agent_tier") else ""
    print(
        f"[XLaya v{__version__}] model={meta.get('model')} | device={meta.get('device')}"
        f"{profile_part}{tier_part} "
        f"| route={meta.get('language_route')} | mode={args.mode}{thorough_part} "
        f"| files={meta.get('files_scanned')} | chunks={meta.get('chunks_evaluated')}{vega_part} "
        f"| {meta.get('elapsed_ms')} ms"
    )
    print("-" * 98)

    if meta.get("file_summaries"):
        print("File-Level Rollup Summary:")
        for fs in meta["file_summaries"]:
            wf = f" | weakest_facet={fs['weakest_facet']}" if "weakest_facet" in fs else ""
            print(
                f"  • {fs['file']:32s} | chunks={fs['chunks']:3d} | mean={fs['mean_score']:.2f} "
                f"(min={fs['min_score']:.2f}, max={fs['max_score']:.2f}) "
                f"| weakest={fs['weakest_ref']}{wf}"
            )
        print("-" * 98)

    if not shown:
        print("  (No matching chunks returned.)")
        return

    if args.mode == "contradiction":
        flagged_n = meta.get("flagged_count", 0)
        hdr = (
            f"Contradiction Sweep (threshold P ≥ {args.threshold:.2f}) → "
            f"{flagged_n} flagged of {meta.get('chunks_evaluated', 0)} chunks:"
        )
        print(hdr)
        for r in shown:
            flag_str = "FLAG" if r.get("flagged") else "DIAG"
            v_tag = ""
            if "vega" in r:
                v_tag = f" | vega={r['vega']['noul']:.3f}({r['vega']['route']})"
            dis_tag = f" | dis={r['disagreement']:.2f}" if "disagreement" in r else ""
            print(
                f"  [{flag_str}] P(eff)={r.get('noul', 0.0):.3f} "
                f"(rel={r.get('relevance', 0.0):.2f} × raw={r.get('noul_raw', 0.0):.2f}){dis_tag}{v_tag} "
                f"| {r['ref']:36s} | {r['heading'][:34]}"
            )
    elif args.mode == "shortlist":
        print(f"Top-{len(shown)} Hybrid Shortlisted Sections for query: {args.query!r}")
        for idx, r in enumerate(shown, start=1):
            v_tag = f" | vega={r['vega']['expected_score']:.2f}" if "vega" in r else ""
            dis_tag = f" | dis={r['disagreement']:.2f}" if "disagreement" in r else ""
            print(
                f"  {idx:2d}. hyb={r.get('hybrid_score', 0.0):.3f} "
                f"(neural={r.get('expected_score', 0.0):.2f}/4.00, lex={r.get('lexical_score', 0.0):.2f})"
                f"{dis_tag}{v_tag} | {r['ref']:36s} | {r['heading'][:32]}"
            )
    elif args.mode == "classify":
        print(f"Classification Results ({len(shown)} chunks):")
        for r in shown:
            v_tag = f" | vega={r['vega']['choice']}({r['vega']['route']})" if "vega" in r else ""
            dis_tag = f" | dis={r['disagreement']:.2f}" if "disagreement" in r else ""
            print(
                f"  choice={str(r.get('choice', '')):18s} | conf={r.get('confidence', 0.0):.3f}"
                f"{dis_tag}{v_tag} | {r['ref']:36s} | {r['heading'][:34]}"
            )
    else:
        print(f"Rubric Completeness Sweep (top {len(shown)} of {meta.get('chunks_evaluated', 0)} chunks):")
        for r in shown:
            contra_part = f" | P(contra)={r.get('noul', 0.0):.3f}" if args.ssot else ""
            v_tag = f" | vega={r['vega']['expected_score']:.2f}" if "vega" in r else ""
            facet_part = ""
            if "facet_scores" in r:
                facet_part = f" [weakest={r.get('weakest_facet')}:{r.get('facet_min', 0.0):.2f}]"
            print(
                f"  score={r.get('expected_score', r.get('score', 0.0)):.2f}/4.00{facet_part} "
                f"| conf={r.get('confidence', 0.0):.3f}{contra_part}{v_tag} "
                f"| {r['ref']:36s} | {r['heading'][:34]}"
            )


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "XBoost /xlaya v2.3.0 — 5-Tier Hardware-Adaptive System 1 → System 1.5 "
            "Triage & Cross-Regime Code-Graph Sieve Engine"
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Target files or directories to chunk and evaluate",
    )
    parser.add_argument(
        "--mode",
        choices=["rubric", "contradiction", "shortlist", "classify"],
        default="rubric",
        help="Evaluation mode (default: rubric)",
    )
    parser.add_argument("--query", default="", help="Target query/instructions for shortlist, rubric, or classify")
    parser.add_argument("--ssot", default="", help="Canonical SSOT statement to test for contradictions (noul)")
    parser.add_argument("--true-desc", default="", help="Custom description for noul 'true' (contradiction)")
    parser.add_argument("--false-desc", default="", help="Custom description for noul 'false' (consistent)")
    parser.add_argument(
        "--labels",
        default=DEFAULT_LABELS_SPEC,
        help="Label specification 'key1:desc1|key2:desc2' for classify mode",
    )
    parser.add_argument(
        "--noul-labels",
        default="",
        help="Optional custom noul label pair, e.g. 'B,A' mapping false→B and true→A",
    )
    parser.add_argument(
        "--lang",
        choices=["auto", "en", "multi", "typed", "ensemble"],
        default="auto",
        help="Stage 1 routing: auto, en, multi, typed (typed-decisions), or ensemble (multi-encoder jury)",
    )
    parser.add_argument(
        "--device",
        choices=["auto", "cuda", "mps", "cpu"],
        default="auto",
        help="Execution device: auto, cuda, mps, or cpu (default: auto)",
    )
    parser.add_argument(
        "--profile",
        choices=list(XLAYA_PROFILES),
        default="auto",
        help=(
            "Hardware execution profile: auto, nano (0-torch <25 MB), edge (CPU single encoder), "
            "workstation (16 GB), max (40 GB+ / L4x4)"
        ),
    )
    parser.add_argument(
        "--agent-tier",
        choices=list(XLAYA_AGENT_TIERS),
        default="auto",
        help=(
            "Downstream SWE agent tier: auto, e4b-sniper (K=3, <=800 tok precision sieve), "
            "or 31b-deep (K=8, <=4096 tok conditional residual graph sieve)"
        ),
    )
    parser.add_argument(
        "--sieve-weights",
        default="",
        help="Optional path to evolved JSON sieve_genomes.json policy file",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1600,
        help="Maximum characters per chunk (default: 1600, paired with script-aware token budget)",
    )
    parser.add_argument(
        "--whole-file",
        action="store_true",
        help="Evaluate each file as a single unit (up to max-chars in Stage 1; up to ~73k tokens with --vega)",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=2048,
        help="Maximum number of chunks to evaluate in one pass (default: 2048; auto-raised to 4096 in --thorough)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Top results to return (default: 10 for shortlist/rubric/contradiction, 0 [all] for classify/thorough)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.55,
        help="Effective contradiction threshold P(rel × contra) (default: 0.55)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32,
        help="Batch size for length-sorted agent.predict_batch (default: 32)",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help=(
            f"Comma-separated glob patterns for directory scans (default: {DEFAULT_PATTERN}; "
            "auto-expands to code files for code_audit/shortlist)"
        ),
    )
    parser.add_argument(
        "--lexical-prefilter",
        type=int,
        default=0,
        help="Optional Stage 0 BM25 + code-span + Thai 3-gram prefilter top-K before neural pass (0 = off)",
    )
    parser.add_argument(
        "--vega",
        action="store_true",
        help="Enable Stage 2 VegaML conformal escalation on top/borderline/high-disagreement finalists",
    )
    parser.add_argument(
        "--vega-model",
        choices=["auto", "0.8b", "4b", "gemma-1b", "27b", "none"],
        default="auto",
        help="VegaML reader model size for Stage 2 escalation (default: auto hardware-aware)",
    )
    parser.add_argument(
        "--vega-top-k",
        type=int,
        default=10,
        help="Maximum Stage 1 finalists escalated to VegaML (default: 10)",
    )
    parser.add_argument(
        "--views",
        "--vega-views",
        dest="views",
        type=int,
        choices=[1, 2, 3],
        default=1,
        help="Stage 2 VegaML multi-view debiasing passes (1=single, 2=reversed options, 3=+prose paraphrase)",
    )
    parser.add_argument(
        "--thorough",
        action="store_true",
        help="Enable full-document scan (no prefilter, all chunks) + 4-facet decomposed rubric + file_summaries",
    )
    parser.add_argument(
        "--rubric-preset",
        choices=["default", "architecture", "code_audit", "doc_sync", "research"],
        default="default",
        help="Domain rubric preset for --thorough 4-facet scoring (default: default)",
    )
    parser.add_argument(
        "--policy-path",
        default="",
        help="Directory path to load/save a trained TTTHead + split-conformal calibration policy bundle",
    )
    parser.add_argument(
        "--fit-rows",
        default="",
        help=(
            "Path to CSV/JSON/JSONL labeled rows to fit and save a persistent "
            "TTTHead + conformal policy at --policy-path"
        ),
    )
    parser.add_argument(
        "--fit-questions",
        "--questions-file",
        dest="fit_questions",
        default="",
        help="Optional path to JSON questions schema for --fit-rows or multimodal prediction",
    )
    parser.add_argument(
        "--target-precision",
        type=float,
        default=0.95,
        help="Target precision for split-conformal calibration during --fit-rows (default: 0.95)",
    )
    parser.add_argument(
        "--image",
        default="",
        help="Local image file path for Stage 2 VegaVision multimodal prediction",
    )
    parser.add_argument(
        "--audio",
        default="",
        help="Local audio file path for Stage 2 VegaAudio multimodal prediction",
    )
    parser.add_argument(
        "--video",
        default="",
        help="Local video file path for Stage 2 VegaVideo multimodal prediction",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run built-in deterministic + neural + conformal + code-sieve self-test suite and exit",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if args.self_test:
        report = run_self_test()
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0 if report.get("ok") else 1

    if args.fit_rows:
        if not args.policy_path:
            print("[XLaya Error] --fit-rows requires --policy-path to persist the policy bundle.", file=sys.stderr)
            return 2
        rows_path = Path(args.fit_rows)
        if not rows_path.is_file():
            print(f"[XLaya Error] --fit-rows file not found: {rows_path}", file=sys.stderr)
            return 2
        if rows_path.suffix.lower() == ".csv":
            rows_data: Any = str(rows_path)
        elif rows_path.suffix.lower() == ".jsonl":
            raw_text = rows_path.read_text(encoding="utf-8").strip()
            rows_data = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
        else:
            raw_text = rows_path.read_text(encoding="utf-8").strip()
            rows_data = json.loads(raw_text)
        if args.fit_questions:
            q_data = json.loads(Path(args.fit_questions).read_text(encoding="utf-8"))
        else:
            q_data = _build_mode_questions(
                mode=args.mode,
                query=args.query,
                ssot=args.ssot,
                true_desc=args.true_desc,
                false_desc=args.false_desc,
                labels=parse_label_spec(args.labels),
                noul_label_map=parse_noul_labels(args.noul_labels),
                thorough=args.thorough,
                rubric_preset=args.rubric_preset,
            )
        fit_res = fit_policy(
            rows=rows_data,
            questions=q_data,
            policy_path=args.policy_path,
            vega_model=args.vega_model,
            device=args.device,
            target_precision=args.target_precision,
            resident_cache=False,
        )
        print(json.dumps(fit_res, indent=2, ensure_ascii=False))
        return 0 if fit_res.get("ok") else 1

    if args.image or args.audio or args.video:
        if args.fit_questions:
            q_data = json.loads(Path(args.fit_questions).read_text(encoding="utf-8"))
        else:
            q_data = _build_mode_questions(
                mode=args.mode,
                query=args.query or "Evaluate the visual or audio content accurately.",
                ssot=args.ssot,
                true_desc=args.true_desc,
                false_desc=args.false_desc,
                labels=parse_label_spec(args.labels),
                noul_label_map=parse_noul_labels(args.noul_labels),
                thorough=args.thorough,
                rubric_preset=args.rubric_preset,
            )
        mm_res = predict_direct(
            questions=q_data,
            vega=True,
            vega_model=args.vega_model,
            views=args.views,
            policy_path=args.policy_path,
            image=args.image or None,
            audio=args.audio or None,
            video=args.video or None,
            device=args.device,
            profile=args.profile,
        )
        print(json.dumps(mm_res, indent=2, ensure_ascii=False))
        return 0 if mm_res.get("ok") else 1

    if not args.paths:
        print("[XLaya Error] At least one target file or directory path is required.", file=sys.stderr)
        return 2

    effective_top_k = (
        args.top_k
        if args.top_k is not None
        else (0 if (args.mode == "classify" or args.thorough) else 10)
    )

    try:
        payload = run_triage(
            paths=args.paths,
            mode=args.mode,
            query=args.query,
            ssot=args.ssot,
            true_desc=args.true_desc,
            false_desc=args.false_desc,
            labels_spec=args.labels,
            noul_labels=args.noul_labels,
            lang=args.lang,
            device=args.device,
            max_chars=args.max_chars,
            whole_file=args.whole_file,
            max_chunks=args.max_chunks,
            top_k=effective_top_k,
            threshold=args.threshold,
            batch_size=args.batch_size,
            pattern=args.pattern,
            lexical_prefilter=args.lexical_prefilter,
            vega=args.vega,
            vega_model=args.vega_model,
            vega_top_k=args.vega_top_k,
            views=args.views,
            thorough=args.thorough,
            rubric_preset=args.rubric_preset,
            policy_path=args.policy_path or None,
            profile=args.profile,
            agent_tier=args.agent_tier,
            sieve_weights=args.sieve_weights or None,
            resident_cache=False,
        )
    except ValueError as exc:
        print(f"[XLaya Error] {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    if payload["meta"].get("files_scanned", 0) == 0:
        print("[XLaya] No matching files found for the given paths.", file=sys.stderr)
        return 0
    if payload["meta"].get("chunks_evaluated", 0) == 0:
        print("[XLaya] No non-empty text chunks extracted.", file=sys.stderr)
        return 0

    _print_human_report(payload, args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
