#!/usr/bin/env python3
"""
laya_triage.py — System 1 Semantic Decision, Heading Chunker & Contradiction Triage CLI Engine
Part of the XBoost Agent Skill Framework (/xlaya).

Features:
1. Fence-Safe Heading-Aware Chunking (<= 1,200 chars / ~300 tokens) with exact #L<start>-L<end> line tracking,
   preventing silent truncation inside ModernBERT-large's 512-token window (512 - 192 head = 320 state tokens)
   and ignoring `#` comments inside fenced code blocks.
2. Automatic English vs Multilingual model routing via laya.is_english() (zero-overhead script detection).
3. Four operational modes:
   - rubric        : 5-level (0..4) ordinal technical completeness scoring + optional noul check
   - contradiction : Calibrated noul contradiction hunting against a canonical SSOT statement
   - shortlist     : Top-K section shortlisting (#L<start>-L<end>) for /xbrief and /xplan
   - classify      : Categorical classification via choice (auto-shortlists via embeddings if >20 labels)
4. Graceful pure-Python fallback if `laya` is not installed in the active Python environment.
"""

import argparse
import json
import re
import sys
import warnings
from pathlib import Path
from typing import Any, Dict, List, Tuple

sys.dont_write_bytecode = True
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

warnings.filterwarnings("ignore", category=RuntimeWarning, module="laya")

HEADING_RE = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
THAI_OR_NON_ASCII_RE = re.compile(r"[\u0E00-\u0E7F\u3000-\u9FFF\u0600-\u06FF\u0400-\u04FF]")

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


def chunk_markdown_file(
    file_path: Path,
    max_chars: int = 1200,
    min_merge_chars: int = 220,
    whole_file: bool = False,
) -> List[Dict[str, Any]]:
    """Split a file into fence-safe, heading-aware chunks (<= max_chars) with 1-based line ranges."""
    try:
        raw_text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return [
            {
                "file": str(file_path.as_posix()),
                "name": file_path.name,
                "heading": "<read_error>",
                "start_line": 1,
                "end_line": 1,
                "ref": f"{file_path.name}#L1-L1",
                "text": f"Error reading file: {exc}",
            }
        ]

    lines = raw_text.splitlines()
    if not lines:
        return []

    if whole_file:
        clipped = raw_text[:max_chars]
        return [
            {
                "file": str(file_path.as_posix()),
                "name": file_path.name,
                "heading": file_path.name,
                "start_line": 1,
                "end_line": len(lines),
                "ref": f"{file_path.name}#L1-L{len(lines)}",
                "text": clipped,
            }
        ]

    raw_sections: List[Tuple[str, int, int, List[str]]] = []
    current_heading = file_path.name
    sec_start = 1
    sec_lines: List[str] = []
    in_fence = False

    for idx, line in enumerate(lines, start=1):
        if FENCE_RE.match(line):
            in_fence = not in_fence

        match = None if in_fence else HEADING_RE.match(line)
        if match and sec_lines:
            raw_sections.append((current_heading, sec_start, idx - 1, sec_lines))
            current_heading = match.group(2).strip()
            sec_start = idx
            sec_lines = [line]
        else:
            if match and not sec_lines:
                current_heading = match.group(2).strip()
                sec_start = idx
            sec_lines.append(line)

    if sec_lines:
        raw_sections.append((current_heading, sec_start, len(lines), sec_lines))

    # Merge tiny intro/header stubs (< min_merge_chars) into the following section when total <= max_chars
    sections: List[Tuple[str, int, int, List[str]]] = []
    i = 0
    while i < len(raw_sections):
        h, s_ln, e_ln, s_lns = raw_sections[i]
        text_len = sum(len(x) + 1 for x in s_lns)
        if text_len < min_merge_chars and (i + 1) < len(raw_sections):
            nh, _, ne_ln, ns_lns = raw_sections[i + 1]
            combined_len = text_len + sum(len(x) + 1 for x in ns_lns)
            if combined_len <= max_chars:
                merged_heading = f"{h} > {nh}" if h != file_path.name else nh
                raw_sections[i + 1] = (merged_heading, s_ln, ne_ln, s_lns + ns_lns)
                i += 1
                continue
        sections.append((h, s_ln, e_ln, s_lns))
        i += 1

    chunks: List[Dict[str, Any]] = []
    for heading, start_ln, end_ln, s_lines in sections:
        block_text = "\n".join(s_lines).strip()
        if not block_text:
            continue
        if len(block_text) <= max_chars:
            chunks.append(
                {
                    "file": str(file_path.as_posix()),
                    "name": file_path.name,
                    "heading": heading,
                    "start_line": start_ln,
                    "end_line": end_ln,
                    "ref": f"{file_path.name}#L{start_ln}-L{end_ln}",
                    "text": block_text,
                }
            )
            continue

        # Subdivide oversized section on paragraph boundaries while keeping line accuracy
        prefix = f"[{heading}]\n"
        budget = max(256, max_chars - len(prefix))
        buf_lines: List[str] = []
        buf_chars = 0
        chunk_start = start_ln

        for offset, s_line in enumerate(s_lines):
            cur_ln = start_ln + offset
            line_len = len(s_line) + 1
            if len(s_line) > budget:
                if buf_lines:
                    body = "\n".join(buf_lines).strip()
                    if body:
                        chunks.append(
                            {
                                "file": str(file_path.as_posix()),
                                "name": file_path.name,
                                "heading": heading,
                                "start_line": chunk_start,
                                "end_line": cur_ln - 1,
                                "ref": f"{file_path.name}#L{chunk_start}-L{cur_ln - 1}",
                                "text": (prefix + body)[:max_chars],
                            }
                        )
                    buf_lines = []
                    buf_chars = 0

                s_strip = s_line.lstrip()
                if s_strip.startswith("|") and len(s_strip.split("|")) > 1:
                    row_head = ("|" + s_strip.split("|")[1] + " | ")[:60]
                else:
                    row_head = ""

                slice_budget = max(128, max_chars - len(prefix) - len(row_head))
                for pos in range(0, len(s_line), slice_budget):
                    segment = s_line[pos: pos + slice_budget]
                    seg_text = (prefix + segment) if pos == 0 else (prefix + row_head + segment)
                    chunks.append(
                        {
                            "file": str(file_path.as_posix()),
                            "name": file_path.name,
                            "heading": heading,
                            "start_line": cur_ln,
                            "end_line": cur_ln,
                            "ref": f"{file_path.name}#L{cur_ln}-L{cur_ln}",
                            "text": seg_text[:max_chars],
                        }
                    )
                chunk_start = cur_ln + 1
                continue

            should_split = bool(buf_lines) and (buf_chars + line_len > budget)
            if should_split:
                body = "\n".join(buf_lines).strip()
                if body:
                    chunks.append(
                        {
                            "file": str(file_path.as_posix()),
                            "name": file_path.name,
                            "heading": heading,
                            "start_line": chunk_start,
                            "end_line": cur_ln - 1,
                            "ref": f"{file_path.name}#L{chunk_start}-L{cur_ln - 1}",
                            "text": (prefix + body)[:max_chars],
                        }
                    )
                buf_lines = [s_line]
                buf_chars = line_len
                chunk_start = cur_ln
            else:
                buf_lines.append(s_line)
                buf_chars += line_len

        if buf_lines:
            body = "\n".join(buf_lines).strip()
            if body:
                chunks.append(
                    {
                        "file": str(file_path.as_posix()),
                        "name": file_path.name,
                        "heading": heading,
                        "start_line": chunk_start,
                        "end_line": end_ln,
                        "ref": f"{file_path.name}#L{chunk_start}-L{end_ln}",
                        "text": (prefix + body)[:max_chars],
                    }
                )

    return chunks


def collect_target_files(paths: List[str], pattern: str = "*.md") -> List[Path]:
    """Resolve file or directory paths into a sorted list of target files."""
    resolved: List[Path] = []
    seen = set()
    for raw in paths:
        p = Path(raw).resolve()
        if p.is_file():
            if p not in seen:
                seen.add(p)
                resolved.append(p)
        elif p.is_dir():
            excluded_parts = {
                ".git",
                "node_modules",
                ".venv",
                "venv",
                "env",
                "dist",
                "build",
                "__pycache__",
                ".obsidian",
                ".pytest_cache",
            }
            for child in sorted(p.rglob(pattern)):
                if child.is_file() and not any(part in excluded_parts for part in child.parts):
                    if child not in seen:
                        seen.add(child)
                        resolved.append(child)
    return resolved


def parse_label_spec(spec: str) -> Dict[str, str]:
    """Parse 'label1:desc1|label2:desc2' or comma-separated labels into a criteria dict."""
    sep = "|" if "|" in spec else ","
    out: Dict[str, str] = {}
    for item in spec.split(sep):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            k, v = item.split(":", 1)
            out[k.strip()] = v.strip()
        else:
            out[item] = item
    return out


def fallback_evaluate(
    chunks: List[Dict[str, Any]],
    mode: str,
    query: str,
    ssot: str,
    labels: Dict[str, str],
) -> List[Dict[str, Any]]:
    """Deterministic pure-Python fallback when `laya` is not installed."""
    ssot_or_query = ssot or query
    query_terms = [t.lower() for t in re.findall(r"\w+", query or ssot) if len(t) > 2]
    ssot_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", ssot_or_query))
    negation_markers = {"not", "never", "false", "deprecated", "legacy", "old", "fail"}
    ssot_negations = set(re.findall(r"\b[a-z]+\b", ssot_or_query.lower())) & negation_markers
    results: List[Dict[str, Any]] = []

    for ch in chunks:
        text_lower = ch["text"].lower()
        word_count = len(ch["text"].split())
        has_code = "```" in ch["text"] or "`" in ch["text"]
        has_table = "|" in ch["text"]

        if mode == "shortlist":
            hits = sum(1 for t in query_terms if t in text_lower)
            denom = max(1, len(query_terms))
            score_val = min(4.0, round((hits / denom) * 4.0, 3))
            results.append({**ch, "score": score_val, "noul": 0.0, "confidence": 0.5, "engine": "fallback"})
        elif mode == "contradiction":
            hits = sum(1 for t in query_terms if t in text_lower)
            overlap_ratio = hits / max(1, len(query_terms))
            chunk_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", text_lower))
            chunk_words = set(re.findall(r"\b[a-z]+\b", text_lower))
            has_conflicting_nums = bool(ssot_nums and chunk_nums and not ssot_nums.issubset(chunk_nums))
            has_extra_negation = bool((chunk_words & negation_markers) - ssot_negations)
            if hits > 0 and (has_conflicting_nums or has_extra_negation):
                noul_val = (
                    round(min(1.0, max(0.65, overlap_ratio)), 3)
                    if overlap_ratio >= 0.25
                    else round(overlap_ratio, 3)
                )
            else:
                noul_val = round(0.15 * overlap_ratio, 3)
            results.append({**ch, "score": 0.0, "noul": noul_val, "confidence": 0.5, "engine": "fallback"})
        elif mode == "classify":
            best_label = next(iter(labels.keys()), "unknown")
            best_hits = -1
            for lbl, desc in labels.items():
                terms = [t.lower() for t in re.findall(r"\w+", f"{lbl} {desc}") if len(t) > 2]
                hits = sum(1 for t in terms if t in text_lower)
                if hits > best_hits:
                    best_hits = hits
                    best_label = lbl
            results.append({**ch, "choice": best_label, "confidence": 0.5, "engine": "fallback"})
        else:
            base = min(2.5, word_count / 60.0)
            bonus = (0.75 if has_code else 0.0) + (0.75 if has_table else 0.0)
            score_val = round(min(4.0, base + bonus), 3)
            results.append({**ch, "score": score_val, "noul": 0.0, "confidence": 0.5, "engine": "fallback"})

    return results


def run_laya_inference(
    chunks: List[Dict[str, Any]],
    mode: str,
    query: str,
    ssot: str,
    true_desc: str,
    false_desc: str,
    labels: Dict[str, str],
    lang_mode: str,
    batch_size: int,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Run neural System 1 inference with `laya` or fall back cleanly."""
    try:
        import laya  # type: ignore
    except ImportError:
        return fallback_evaluate(chunks, mode, query, ssot, labels), {
            "laya_available": False,
            "model": "pure-python-fallback",
            "device": "cpu",
        }

    sample_text = "\n".join(c["text"][:300] for c in chunks[:5]) + " " + query + " " + ssot
    if lang_mode == "en":
        use_english = True
    elif lang_mode == "multi":
        use_english = False
    else:
        use_english = bool(laya.is_english(sample_text)) and not bool(THAI_OR_NON_ASCII_RE.search(sample_text))

    if use_english:
        agent = laya.load("convaiinnovations/laya")
        model_id = "convaiinnovations/laya"
    else:
        agent = laya.load("convaiinnovations/laya", subfolder="multilingual")
        model_id = "convaiinnovations/laya (multilingual)"

    device_str = str(getattr(agent, "device", "cpu"))
    meta = {
        "laya_available": True,
        "laya_version": getattr(laya, "__version__", "unknown"),
        "model": model_id,
        "language_route": "english" if use_english else "multilingual",
        "device": device_str,
    }

    questions: Dict[str, Any] = {}
    if mode == "shortlist":
        questions["rel"] = {
            "type": "score",
            "instructions": f"Rate how directly this section answers or specifies: {query}",
            "criteria": DEFAULT_RELEVANCE_CRITERIA,
        }
    elif mode == "contradiction":
        questions["contra"] = {
            "type": "noul",
            "instructions": f"Does this text contradict the canonical truth: {ssot}",
            "criteria": {
                "false": false_desc or f"Consistent with or unrelated to: {ssot}",
                "true": true_desc or f"Directly contradicts or states outdated facts against: {ssot}",
            },
        }
    elif mode == "classify":
        questions["cat"] = {
            "type": "choice",
            "instructions": query or "Classify this text into the most accurate category.",
            "criteria": labels,
        }
    else:
        questions["rubric"] = {
            "type": "score",
            "instructions": query or "Rate the technical completeness and specificity of this documentation.",
            "criteria": DEFAULT_RUBRIC_CRITERIA,
        }
        if ssot:
            questions["contra"] = {
                "type": "noul",
                "instructions": f"Does this text contradict the canonical truth: {ssot}",
                "criteria": {
                    "false": false_desc or f"Consistent with canonical truth: {ssot}",
                    "true": true_desc or f"Contradicts canonical truth: {ssot}",
                },
            }

    state_texts = [c["text"] for c in chunks]
    if mode == "classify" and len(labels) > 20:
        embed_fn = laya.embed_fn_from_agent(agent)
        preds = [laya.predict_shortlist(agent, st, questions, embed_fn=embed_fn, k=20) for st in state_texts]
    else:
        preds = agent.predict_batch(state_texts, questions, batch_size=batch_size)

    enriched: List[Dict[str, Any]] = []
    for ch, pred in zip(chunks, preds):
        ans = pred["answers"]
        item = dict(ch)
        item["engine"] = model_id
        if mode == "shortlist":
            item["score"] = round(float(ans["rel"]["score"]), 3)
            item["confidence"] = round(float(ans["rel"]["confidence"]), 3)
        elif mode == "contradiction":
            item["noul"] = round(float(ans["contra"]["noul"]), 3)
            item["confidence"] = round(float(ans["contra"]["confidence"]), 3)
        elif mode == "classify":
            item["choice"] = ans["cat"]["choice"]
            item["confidence"] = round(float(ans["cat"]["confidence"]), 3)
        else:
            item["score"] = round(float(ans["rubric"]["score"]), 3)
            item["confidence"] = round(float(ans["rubric"]["confidence"]), 3)
            if "contra" in ans:
                item["noul"] = round(float(ans["contra"]["noul"]), 3)
            else:
                item["noul"] = 0.0
        enriched.append(item)

    return enriched, meta


def main() -> int:
    parser = argparse.ArgumentParser(
        description="XBoost /xlaya System 1 Semantic Triage & Heading Chunker CLI Engine"
    )
    parser.add_argument(
        "paths",
        nargs="+",
        help="Target files or directories to chunk and evaluate",
    )
    parser.add_argument(
        "--mode",
        choices=["rubric", "contradiction", "shortlist", "classify"],
        default="rubric",
        help="Evaluation mode (default: rubric)",
    )
    parser.add_argument(
        "--query",
        default="",
        help="Target query/instructions for shortlist, rubric, or classify modes",
    )
    parser.add_argument(
        "--ssot",
        default="",
        help="Canonical SSOT statement to test for contradictions (noul)",
    )
    parser.add_argument(
        "--true-desc",
        default="",
        help="Custom description for noul 'true' (contradiction/violation present)",
    )
    parser.add_argument(
        "--false-desc",
        default="",
        help="Custom description for noul 'false' (consistent/compliant)",
    )
    parser.add_argument(
        "--labels",
        default="architecture:Architecture & specs|cli:CLI scripts & commands|docs:General prose & guides",
        help="Label specification 'key1:desc1|key2:desc2' for classify mode",
    )
    parser.add_argument(
        "--lang",
        choices=["auto", "en", "multi"],
        default="auto",
        help="Language routing: auto (via laya.is_english), en, or multi",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1200,
        help="Maximum characters per chunk (default: 1200 ≈ 300 tokens, fitting ModernBERT 512 window)",
    )
    parser.add_argument(
        "--whole-file",
        action="store_true",
        help="Evaluate only the first max-chars of each file instead of splitting by heading",
    )
    parser.add_argument(
        "--max-chunks",
        type=int,
        default=2048,
        help="Maximum number of chunks to evaluate in one pass (default: 2048)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of top results to display in shortlist/contradiction/rubric output (default: 10)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.60,
        help="Probability threshold P(true) for flagging contradictions in contradiction mode (default: 0.60)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Batch size for agent.predict_batch (default: 16)",
    )
    parser.add_argument(
        "--pattern",
        default="*.md",
        help="Glob pattern when scanning directories (default: *.md)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON output",
    )

    args = parser.parse_args()
    files = collect_target_files(args.paths, pattern=args.pattern)
    if not files:
        print("[XLaya Sidecar] No matching files found for the given paths.", file=sys.stderr)
        return 0

    all_chunks: List[Dict[str, Any]] = []
    for f in files:
        all_chunks.extend(chunk_markdown_file(f, max_chars=args.max_chars, whole_file=args.whole_file))
        if len(all_chunks) >= args.max_chunks:
            all_chunks = all_chunks[: args.max_chunks]
            break

    if not all_chunks:
        print("[XLaya Sidecar] No non-empty text chunks extracted.", file=sys.stderr)
        return 0

    labels_dict = parse_label_spec(args.labels)
    results, meta = run_laya_inference(
        chunks=all_chunks,
        mode=args.mode,
        query=args.query,
        ssot=args.ssot,
        true_desc=args.true_desc,
        false_desc=args.false_desc,
        labels=labels_dict,
        lang_mode=args.lang,
        batch_size=args.batch_size,
    )

    # Sort according to mode
    if args.mode == "shortlist":
        results.sort(key=lambda r: (r.get("score", 0.0), r.get("confidence", 0.0)), reverse=True)
    elif args.mode == "contradiction":
        results.sort(key=lambda r: (r.get("noul", 0.0), r.get("confidence", 0.0)), reverse=True)
    elif args.mode == "rubric":
        results.sort(key=lambda r: (r.get("score", 0.0), -r.get("noul", 0.0)), reverse=True)

    shown = results[: args.top_k]

    if args.json:
        payload = {
            "meta": {
                **meta,
                "mode": args.mode,
                "files_scanned": len(files),
                "chunks_evaluated": len(results),
            },
            "results": [
                {k: v for k, v in item.items() if k != "text"}
                for item in shown
            ],
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    print(
        f"[XLaya Sidecar] model={meta.get('model')} | device={meta.get('device')} "
        f"| mode={args.mode} | files={len(files)} | chunks={len(results)}"
    )
    if meta.get("laya_available") and meta.get("device") == "cpu":
        print(
            "  Tip: PyTorch is currently running on CPU. Install a CUDA wheel matching your GPU "
            "for ~5-10× faster batch inference."
        )
    print("-" * 92)

    if args.mode == "contradiction":
        flagged = [r for r in results if r.get("noul", 0.0) >= args.threshold]
        print(
            f"Contradiction Sweep (threshold P ≥ {args.threshold:.2f}) → "
            f"{len(flagged)} flagged of {len(results)} chunks:"
        )
        for r in shown:
            flag_str = "FLAG" if r.get("noul", 0.0) >= args.threshold else "OK  "
            print(
                f"  [{flag_str}] P(contra)={r.get('noul', 0.0):.3f} | conf={r.get('confidence', 0.0):.3f} "
                f"| {r['ref']:36s} | {r['heading'][:34]}"
            )
    elif args.mode == "shortlist":
        print(f"Top-{len(shown)} Shortlisted Sections for query: {args.query!r}")
        for idx, r in enumerate(shown, start=1):
            print(
                f"  {idx:2d}. score={r.get('score', 0.0):.2f}/4.00 | conf={r.get('confidence', 0.0):.3f} "
                f"| {r['ref']:36s} | {r['heading'][:34]}"
            )
    elif args.mode == "classify":
        print(f"Classification Results (top {len(shown)} shown):")
        for r in shown:
            print(
                f"  choice={r.get('choice', ''):16s} | conf={r.get('confidence', 0.0):.3f} "
                f"| {r['ref']:36s} | {r['heading'][:34]}"
            )
    else:
        print(f"Rubric Completeness Sweep (top {len(shown)} of {len(results)} chunks):")
        for r in shown:
            contra_part = f" | P(contra)={r.get('noul', 0.0):.3f}" if args.ssot else ""
            print(
                f"  score={r.get('score', 0.0):.2f}/4.00 | conf={r.get('confidence', 0.0):.3f}{contra_part} "
                f"| {r['ref']:36s} | {r['heading'][:34]}"
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
