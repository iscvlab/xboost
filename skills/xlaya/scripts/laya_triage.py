#!/usr/bin/env python3
"""
laya_triage.py — 3-Stage System 1 → System 1.5 Semantic Triage, Multi-Facet Rubric & Conformal Cascade Engine
Part of the XBoost Agent Skill Framework (/xlaya v2.1.0).

Architecture:
- Stage 0 (Deterministic Chunker + Lexical Engine):
  • 4-backtick/tilde fence-safe Markdown parser with 6-level #{1,6} breadcrumb stack
  • Script-aware token budget estimator (English ≤ 380 est. tokens, Multilingual ≤ 780 est. tokens)
  • Multi-format structured chunking (.md, .txt, .html/.htm, .jsonl, .json, .csv) with disambiguated refs
  • Stdlib BM25 + code-span / CLI-flag / identifier bonus + overlapping Thai character 3-grams
- Stage 1 (ModernBERT Multi-Encoder Jury — english + typed-decisions + mmBERT):
  • Thread-safe resident model cache (_MODEL_CACHE) + offline-first local HF snapshot resolution
  • Support for 'en', 'multi', 'typed' (subfolder='typed-decisions'), and 'ensemble' (0.45*en + 0.55*typed)
  • Per-item inter-model disagreement & model_agreement telemetry for automatic Stage 2 escalation
  • 4-facet decomposed rubric scoring (specificity, completeness, consistency, actionability) + file summaries
- Stage 2 (VegaML Conformal System 1.5 Escalation & Persistent TTT Calibration):
  • Hardware-aware vega_model selector ('auto' -> '4b' or '0.8b', plus 'gemma-1b', '27b')
  • Multi-view test-time surface debiasing (views=1|2|3 reversing option order & prose templates -> view_agreement)
  • Persistent TTTHead + split-conformal policy training (fit_policy / load_calibration / outbound OOD guard)
  • Local multimodal inference (image, audio, video) through VegaAgent
"""

from __future__ import annotations

import argparse
import contextlib
import csv
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
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

__version__ = "2.1.0"

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
    }
)

DEFAULT_PATTERN = "*.md,*.html,*.txt,*.json,*.jsonl,*.csv"
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
VALID_VEGA_MODELS = frozenset({"auto", "0.8b", "08b", "4b", "gemma-1b", "27b"})

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


def _resolve_device(device: str = "auto") -> str:
    req = (device or "auto").strip().lower()
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

    # Hardware-aware auto-selector: prefer 4b on >=10 GB CUDA VRAM when cached locally, else 0.8b
    if resolved_device.startswith("cuda") and _is_hf_repo_cached("Qwen/Qwen3.5-4B"):
        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                free_b, total_b = torch.cuda.mem_get_info()
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


def get_status() -> Dict[str, Any]:
    """Return current runtime, GPU/CPU, Laya/VegaML availability, and resident cache status."""
    laya_ok, laya_ver = _pkg_version("laya", "laya")
    vega_ok, vega_ver = _pkg_version("vegaml", "vegaml")

    torch_ver: Optional[str] = None
    cuda_ok = False
    mps_ok = False
    gpu_name: Optional[str] = None
    vram_total_gb: Optional[float] = None
    vram_free_gb: Optional[float] = None
    cpu_threads = _recommended_cpu_threads()
    default_dev = "cpu"

    try:
        import torch  # type: ignore

        torch_ver = str(torch.__version__)
        cuda_ok = bool(torch.cuda.is_available())
        mps_ok = bool(hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
        cpu_threads = _configure_cpu_threads(torch)
        if cuda_ok:
            default_dev = "cuda"
            gpu_name = str(torch.cuda.get_device_name(0))
            try:
                free_b, total_b = torch.cuda.mem_get_info()
                vram_free_gb = round(free_b / (1024 ** 3), 2)
                vram_total_gb = round(total_b / (1024 ** 3), 2)
            except Exception:  # nosec B110
                pass
        elif mps_ok:
            default_dev = "mps"
        else:
            default_dev = "cpu"
    except ImportError:
        pass

    with _CACHE_LOCK:
        loaded = list(_MODEL_CACHE.keys())

    return {
        "ok": True,
        "version": __version__,
        "python": sys.version.split()[0],
        "laya_available": laya_ok,
        "laya_version": laya_ver,
        "vegaml_available": vega_ok,
        "vegaml_version": vega_ver,
        "torch_version": torch_ver,
        "cuda_available": cuda_ok,
        "mps_available": mps_ok,
        "device": default_dev,
        "gpu_name": gpu_name,
        "vram_total_gb": vram_total_gb,
        "vram_free_gb": vram_free_gb,
        "recommended_vega_model": _resolve_vega_model("auto", default_dev),
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

    eff_views = max(1, min(3, int(views or 1)))
    has_multimodal = any(x is not None and str(x).strip() != "" for x in (image, audio, video))
    is_batch = states is not None
    if not is_batch and state is None and not has_multimodal:
        raise ValueError(
            "predict_direct requires 'state', 'states', or a multimodal input ('image', 'audio', 'video')."
        )

    t0 = time.perf_counter()
    resolved_device = _resolve_device(device)

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


def _estimate_tokens(text: str) -> float:
    ascii_count = sum(1 for ch in text if ord(ch) < 128)
    non_ascii = len(text) - ascii_count
    punct = sum(1 for ch in text if ch in "|`{}[]()<>:;=/\\_-*#~")
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
) -> List[Dict[str, Any]]:
    raw_body = "\n".join(s_lines).strip()
    if not raw_body:
        return []

    first_prefix = f"[{parent_breadcrumb}]\n" if parent_breadcrumb else ""
    cont_prefix = f"[{full_breadcrumb}]\n" if full_breadcrumb else ""

    first_candidate = first_prefix + raw_body
    if _fits_budget(first_candidate, max_chars):
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
    acc_start = start_ln
    acc_end = start_ln
    is_first_emit = True

    def emit_accumulated() -> None:
        nonlocal acc_lines, is_first_emit
        if not acc_lines:
            return
        body = "\n".join(acc_lines).strip()
        acc_lines = []
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
        pfx = first_prefix if (is_first_emit and not acc_lines) else cont_prefix
        combined = ("\n\n".join(["\n".join(acc_lines), b_text]) if acc_lines else b_text).strip()

        if _fits_budget(pfx + combined, max_chars):
            if not acc_lines:
                acc_start = b_start
            acc_lines = (acc_lines + [""] + b_lines) if acc_lines else list(b_lines)
            acc_end = b_end
            continue

        emit_accumulated()
        pfx = first_prefix if is_first_emit else cont_prefix
        if _fits_budget(pfx + b_text.strip(), max_chars):
            acc_start = b_start
            acc_end = b_end
            acc_lines = list(b_lines)
            continue

        # Oversized single block (e.g., large code fence or GFM table): split on line boundaries
        line_buf: List[str] = []
        lb_start = b_start
        for l_off, single_line in enumerate(b_lines):
            cur_ln = b_start + l_off
            pfx = first_prefix if is_first_emit else cont_prefix
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

            trial = "\n".join(line_buf + [single_line]).strip()
            if line_buf and not _fits_budget(pfx + trial, max_chars):
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
                lb_start = cur_ln
            else:
                if not line_buf:
                    lb_start = cur_ln
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


def chunk_file(
    file_path: Path,
    max_chars: int = 1600,
    whole_file: bool = False,
    rel_prefix: Optional[str] = None,
    limit_hint: int = 0,
) -> List[Dict[str, Any]]:
    """Split a supported file into fence-safe or structured chunks with line/item refs."""
    try:
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        print(f"[XLaya] Warning: could not read {file_path}: {exc}", file=sys.stderr)
        return []

    if not raw_text.strip():
        return []

    ref_base = rel_prefix if rel_prefix is not None else file_path.name
    lines = raw_text.splitlines()

    if whole_file:
        ext = file_path.suffix.lower()
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

    ext = file_path.suffix.lower()
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
                        child = (root_path / fname).resolve()
                        if child not in seen and child.is_file():
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


def _extract_lexical_tokens(text: str) -> List[str]:
    lower = text.lower()
    tokens = [w for w in LATIN_TOKEN_RE.findall(lower) if len(w) >= 2 and w not in STOPWORDS]

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

    eff_views = max(1, min(3, int(views)))
    if thorough:
        max_chunks = max(max_chunks, 4096)
        lexical_prefilter = 0

    noul_label_map = parse_noul_labels(noul_labels)
    labels_dict = parse_label_spec(labels_spec)

    files, scan_root = collect_target_files(paths, pattern=pattern)
    if not files:
        return {
            "ok": True,
            "meta": {
                "version": __version__,
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

    laya_ok, laya_ver = _pkg_version("laya", "laya")
    resolved_device = _resolve_device(device) if laya_ok else "cpu"

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
        enriched = fallback_evaluate(all_chunks, mode, query, ssot, labels_dict, threshold=threshold)
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
            "laya_available": False,
            "laya_version": None,
            "model": "pure-python-fallback",
            "language_route": "fallback",
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
                    if _is_english_text(ch["text"]):
                        ens_en_idxs.append(idx)
                    else:
                        ens_ml_idxs.append(idx)
        elif not head_is_en:
            ml_idxs = list(range(len(all_chunks)))
        else:
            for idx, ch in enumerate(all_chunks):
                if _is_english_text(ch["text"]):
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

    # Mode-specific sorting
    if mode == "shortlist":
        enriched.sort(
            key=lambda r: (r.get("hybrid_score", 0.0), r.get("expected_score", 0.0)),
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
    if vega and laya_ok:
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
        {k: v for k, v in item.items() if k not in ("text", "_full_text")}
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
    print(
        f"[XLaya v{__version__}] model={meta.get('model')} | device={meta.get('device')} "
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
        description="XBoost /xlaya v2.1.0 — 3-Stage System 1 → System 1.5 Pure-Local High-Accuracy Triage Engine"
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
        help=f"Comma-separated glob patterns for directory scans (default: {DEFAULT_PATTERN})",
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
        choices=["auto", "0.8b", "4b", "gemma-1b", "27b"],
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
        help="Path to JSON/JSONL labeled rows to fit and save a persistent TTTHead + conformal policy at --policy-path",
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
        help="Run built-in deterministic + neural + conformal self-test suite and exit",
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
        raw_text = rows_path.read_text(encoding="utf-8").strip()
        if rows_path.suffix.lower() == ".jsonl":
            rows_data = [json.loads(line) for line in raw_text.splitlines() if line.strip()]
        else:
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
