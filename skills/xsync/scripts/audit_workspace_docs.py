#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Universal Workspace Documentation & Cross-File Consistency Auditor (/xsync).
Repository-agnostic deterministic verifier for Markdown (.md) and HTML (.html) suites:
  1. Relative Markdown Link Integrity (verifies local targets exist on disk)
  2. Zero-LaTeX Math Policy (flags inline $...$ or \\rightarrow / \\times outside code spans)
  3. Zero-Stale Deprecated Value Sweep (--deprecated "old_term_1,old_term_2")
  4. Exact SHA-256 Distribution Mirror Parity (--mirror "src:dst" + auto docs_reference/ detection)
  5. Optional Delegation to Repo-Local Auditor (scripts/audit_docs.py)
"""

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

sys.dont_write_bytecode = True
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".venv",
    "venv",
    ".idea",
    ".vscode",
    ".pytest_cache",
}
UNSAFE_PARENT_NAMES = {"desktop", "documents", "downloads", "users", "home", ""}

LATEX_CMD_RE = re.compile(r"\\(?:rightarrow|leftarrow|leftrightarrow|times|approx|pm|leq|geq)\b")
INLINE_DOLLAR_RE = re.compile(
    r"(?<![\\`\w])\$(?!\s|\d[\d,.]*(?:\s|$|[),.;:|]))([^$\n`|]{1,80}?)(?<!\s|\\)\$(?![\w`])"
)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def sha256_bytes(path: Path) -> str:
    """Compute SHA-256 hex digest of file bytes (normalizing CRLF to LF for cross-OS parity)."""
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def strip_code_regions(text: str, suffix: str) -> str:
    """Strip fenced code blocks, inline code spans, and HTML script/style blocks before prose scanning."""
    cleaned = text
    if suffix == ".md":
        cleaned = re.sub(r"(`{3,}|~{3,})[\s\S]*?\1", "", cleaned)
        cleaned = re.sub(r"``[^\n]+?``", "", cleaned)
        cleaned = re.sub(r"\[`([^`\n]+)`\]\(", r"[\1](", cleaned)
        cleaned = re.sub(r"`[^`\n]+`", "", cleaned)
    elif suffix == ".html":
        cleaned = re.sub(r"<script\b[^>]*>[\s\S]*?</script>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<style\b[^>]*>[\s\S]*?</style>", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"<code\b[^>]*>[\s\S]*?</code>", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def discover_doc_files(workspace_root: Path, include_obsidian: bool = False) -> list:
    """Discover active .md and .html files in workspace, respecting /xsync exclusion boundaries."""
    docs = []
    ws_resolved = workspace_root.resolve()
    for root, dirs, files in os.walk(workspace_root):
        root_path = Path(root)
        if root_path.resolve() != ws_resolved and (root_path / ".git").exists():
            dirs[:] = []
            continue
        # Skip Obsidian vaults unless --include-obsidian is explicitly enabled
        if not include_obsidian and (root_path / ".obsidian").is_dir():
            dirs[:] = []
            continue
        dirs[:] = [
            d for d in dirs
            if d not in EXCLUDED_DIRS
            and not d.startswith("_audit")
            and d.lower() != "scratch"
            and not (root_path / d / ".git").exists()
            and (include_obsidian or not (root_path / d / ".obsidian").is_dir())
        ]
        for fname in files:
            fpath = root_path / fname
            if fpath.suffix.lower() in {".md", ".html"}:
                docs.append(fpath)
    return sorted(docs)


LEGACY_GHOST_SKILLS = {
    "xpublish-audit", "xpublish-qgis", "boostx", "briefx", "contextx",
    "create-skillx", "deep-researchx", "kickoffx", "layax", "learnx",
    "mousex", "obsidianx", "ocrx", "planx", "publishx-audit",
    "publishx-qgis", "researchx", "syncx", "ultrax", "unlimited-ocr",
}


def discover_agent_skill_roots() -> list:
    """Discover all installed global AI agent skill roots on the host machine (excluding repo source tree)."""
    home = Path.home()
    script_root = Path(__file__).resolve().parents[2]
    env_root = os.environ.get("AGENT_SKILLS_DIR", "").strip()
    candidates = []
    if env_root:
        candidates.append(Path(env_root))
    candidates.extend([
        home / ".gemini" / "config" / "skills",
        home / ".agents" / "skills",
        home / ".claude" / "skills",
        home / ".codex" / "skills",
        home / ".cursor" / "skills",
        home / ".grok" / "skills",
    ])
    for dot_dir in sorted(home.glob(".*")):
        if dot_dir.is_dir():
            if (dot_dir / "skills").is_dir():
                candidates.append(dot_dir / "skills")
            if (dot_dir / "config" / "skills").is_dir():
                candidates.append(dot_dir / "config" / "skills")
    repo_skills_resolved = (
        script_root.resolve()
        if (script_root.parent / ".git").exists() and script_root.name == "skills"
        else None
    )
    roots = []
    seen = set()
    for c in candidates:
        if c.is_dir():
            rp = c.resolve()
            if repo_skills_resolved and rp == repo_skills_resolved:
                continue
            if rp not in seen:
                seen.add(rp)
                roots.append(c)
    return roots


def discover_federated_context(ws_root: Path, include_obsidian: bool = False) -> tuple:
    """Discover up-tree sibling skill/protocol/profile mirrors and multi-agent skill roots (--federated)."""
    extra_docs = []
    auto_mirrors = []
    ghost_errors = []
    script_root = Path(__file__).resolve().parents[2]
    agent_roots = discover_agent_skill_roots()
    primary_host_root = agent_roots[0] if agent_roots else (Path.home() / ".gemini" / "config" / "skills")
    proto_master = (
        (ws_root / "skills" / "xpublish" / "references" / "github_readme_protocol.md")
        if (ws_root / "skills" / "xpublish" / "references" / "github_readme_protocol.md").is_file()
        else (script_root / "xpublish" / "references" / "github_readme_protocol.md")
        if (script_root / "xpublish" / "references" / "github_readme_protocol.md").is_file()
        else (primary_host_root / "xpublish" / "references" / "github_readme_protocol.md")
    )

    # Check all installed local agent skill roots for legacy deprecated skill directories
    for aroot in agent_roots:
        for sdir in sorted(aroot.iterdir()):
            if not sdir.is_dir() or sdir.name.startswith("."):
                continue
            if sdir.name in LEGACY_GHOST_SKILLS:
                ghost_errors.append(
                    f"[{aroot}/{sdir.name}] Legacy deprecated skill directory still present"
                )

    ancestors = []
    cur_anc = ws_root.parent
    for _ in range(2):
        if (
            cur_anc != ws_root
            and cur_anc != cur_anc.parent
            and cur_anc != Path.home()
            and cur_anc.name.lower() not in UNSAFE_PARENT_NAMES
        ):
            ancestors.append(cur_anc)
            cur_anc = cur_anc.parent
        else:
            break

    candidates = [ws_root]
    seen_candidates = {ws_root.resolve()}
    for anc in ancestors:
        for pfile in sorted(anc.glob("*.md")):
            if pfile.is_file() and any(
                k in pfile.name.upper() for k in ("PLAYBOOK", "PROTOCOL", "PLAN", "PORTFOLIO", "STANDARD")
            ):
                extra_docs.append(pfile)
                if pfile.name == "GITHUB_PUBLISHING_PROTOCOL.md" and proto_master.is_file():
                    if pfile.resolve() != proto_master.resolve():
                        auto_mirrors.append((proto_master, pfile))
        for sib in sorted(anc.iterdir()):
            if (
                not sib.is_dir()
                or sib.resolve() in seen_candidates
                or sib.name.startswith(".")
                or sib.name.startswith("_audit")
                or sib.name.lower() == "scratch"
                or sib.name in EXCLUDED_DIRS
            ):
                continue
            if not include_obsidian and (sib / ".obsidian").is_dir():
                continue
            seen_candidates.add(sib.resolve())
            candidates.append(sib)

    org_profile_docs = []
    org_profile_mirrors = []
    seen_skill_names = set()

    for cand in candidates:
        # 1. Skill Tree Mirrors (skills/<name>/** <-> matching installed host agent skill roots)
        skills_sub = cand / "skills"
        if skills_sub.is_dir():
            unclaimed_skills = [
                sdir for sdir in sorted(skills_sub.iterdir())
                if sdir.is_dir() and not sdir.name.startswith(".") and sdir.name not in seen_skill_names
            ]
            if cand != ws_root and unclaimed_skills:
                extra_docs.extend(discover_doc_files(cand, include_obsidian=include_obsidian))
            for sdir in unclaimed_skills:
                seen_skill_names.add(sdir.name)
                if sdir.name in LEGACY_GHOST_SKILLS:
                    ghost_errors.append(
                        f"[{cand.name}/skills/{sdir.name}] Legacy deprecated skill directory still present"
                    )
                    continue
                matching_host_dirs = [
                    aroot / sdir.name
                    for aroot in agent_roots
                    if (aroot / sdir.name).is_dir() and (aroot / sdir.name).resolve() != sdir.resolve()
                ]
                if (
                    cand == ws_root
                    and primary_host_root.is_dir()
                    and primary_host_root.resolve() != skills_sub.resolve()
                    and not (primary_host_root / sdir.name).is_dir()
                ):
                    ghost_errors.append(
                        f"[{cand.name}/skills/{sdir.name}] Skill directory not installed in primary host root"
                    )
                    continue
                if not matching_host_dirs and agent_roots:
                    ghost_errors.append(
                        f"[{cand.name}/skills/{sdir.name}] Ghost skill directory not present in any host skills root"
                    )
                    continue
                for hdir in matching_host_dirs:
                    for sfile in sorted(sdir.rglob("*")):
                        if not sfile.is_file() or "__pycache__" in sfile.parts or sfile.suffix == ".pyc":
                            continue
                        rel_f = sfile.relative_to(sdir)
                        auto_mirrors.append((sfile, hdir / rel_f))

        # 2. Canonical Root Protocol Mirrors (GITHUB_PUBLISHING_PROTOCOL.md)
        cand_proto = cand / "GITHUB_PUBLISHING_PROTOCOL.md"
        if cand_proto.is_file():
            if cand != ws_root:
                extra_docs.append(cand_proto)
            if proto_master.is_file() and cand_proto.resolve() != proto_master.resolve():
                auto_mirrors.append((proto_master, cand_proto))

        # 2b. Compound Learning Playbooks, Protocols & Standards across sibling workspaces
        playbook_scan_dirs = [
            cand,
            cand / "docs",
            cand / "03_simulations" / "grasshopper_simulations" / "plant_studio",
        ]
        for s_dir in playbook_scan_dirs:
            if s_dir.is_dir():
                for md_f in sorted(s_dir.glob("*.md")):
                    if (
                        md_f.is_file()
                        and md_f.name.upper() != "UI_THEME_PROTOCOL.MD"
                        and any(k in md_f.name.upper() for k in ("PLAYBOOK", "PROTOCOL", "STANDARD"))
                    ):
                        extra_docs.append(md_f)

        # 3. Organization Profile README Mirrors (docs/GITHUB_ORG_PROFILE_README.md <-> */profile/README.md)
        doc_prof = cand / "docs" / "GITHUB_ORG_PROFILE_README.md"
        if doc_prof.is_file():
            org_profile_docs.append(doc_prof)
        for prof_readme in cand.glob("*/profile/README.md"):
            if prof_readme.is_file():
                org_profile_mirrors.append(prof_readme)

        # 4. First-Party Sister Git Repo Root READMEs referencing shared skill/bridge ecosystems
        readme_p = cand / "README.md"
        if cand != ws_root and (cand / ".git").exists() and readme_p.is_file():
            try:
                rtxt = readme_p.read_text(encoding="utf-8", errors="ignore")
                if any(k in rtxt for k in ("xboost", "boostx", "mcp-bridges", "/xpublish")):
                    extra_docs.append(readme_p)
            except OSError:
                pass

    for src_prof in org_profile_docs:
        for dst_prof in org_profile_mirrors:
            auto_mirrors.append((src_prof, dst_prof))

    dedup_docs = sorted({p.resolve(): p for p in extra_docs}.values())
    return dedup_docs, auto_mirrors, ghost_errors


def audit_workspace(args) -> int:
    ws_root = Path(args.workspace).resolve()
    if not ws_root.is_dir():
        print(f"ERROR: Workspace directory not found: {ws_root}", file=sys.stderr)
        return 1

    docs = discover_doc_files(ws_root, include_obsidian=args.include_obsidian)
    extra_docs, fed_mirrors, fed_errors = (
        discover_federated_context(ws_root, include_obsidian=args.include_obsidian)
        if getattr(args, "federated", False)
        else ([], [], [])
    )
    seen_paths = {p.resolve() for p in docs}
    for ed in extra_docs:
        if ed.resolve() not in seen_paths:
            docs.append(ed)
            seen_paths.add(ed.resolve())

    deprecated_terms = [t.strip() for t in re.split(r"(?<!\d),|,(?!\d{3}\b)", args.deprecated) if t.strip()]

    errors = list(fed_errors)
    warnings = []
    passes = []

    broken_links = 0
    latex_hits = 0
    deprecated_hits = 0

    for doc in docs:
        rel_doc = (
            doc.relative_to(ws_root).as_posix()
            if doc.is_relative_to(ws_root)
            else doc.relative_to(ws_root.parent).as_posix()
            if doc.is_relative_to(ws_root.parent)
            else doc.as_posix()
        )
        try:
            text = doc.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            warnings.append(f"[{rel_doc}] Unable to read file: {e}")
            continue

        suffix = doc.suffix.lower()
        prose = strip_code_regions(text, suffix)

        # 1. Relative Markdown Link Verification
        if suffix == ".md":
            for m in MD_LINK_RE.finditer(prose):
                label, raw_target = m.group(1), m.group(2).strip()
                target_url = raw_target.split()[0].strip("<>") if raw_target else ""
                if not target_url or target_url.startswith(
                    (
                        "http://",
                        "https://",
                        "mailto:",
                        "#",
                        "file://",
                        "conversation://",
                        "data:",
                        "javascript:",
                        "vscode:",
                        "obsidian://",
                        "/",
                    )
                ):
                    continue
                clean_rel = unquote(target_url.split("#")[0].split("?")[0].strip())
                if not clean_rel:
                    continue
                resolved = (doc.parent / clean_rel).resolve()
                if not resolved.exists():
                    broken_links += 1
                    errors.append(f"[{rel_doc}] Broken relative link: `[{label}]({target_url})`")

        # 2. Zero-LaTeX Math Policy Check
        if not args.allow_latex:
            for m in LATEX_CMD_RE.finditer(prose):
                latex_hits += 1
                errors.append(f"[{rel_doc}] LaTeX command `{m.group(0)}` detected (use native Unicode symbols).")
            if suffix == ".md":
                for m in INLINE_DOLLAR_RE.finditer(prose):
                    inner = m.group(1)
                    if any(op in inner for op in ("\\", "^", "_", "=", "\\times", "\\rightarrow")):
                        latex_hits += 1
                        errors.append(f"[{rel_doc}] Inline LaTeX math `${inner}$` detected (use native Unicode).")

        # 3. Deprecated Term Zero-Hit Sweep (skip immutable changelogs)
        is_historical = "changelog" in doc.name.lower() or "history" in doc.name.lower()
        if deprecated_terms and not is_historical:
            for term in deprecated_terms:
                if term[0].isalnum() and term[-1].isalnum():
                    matched = bool(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", prose))
                else:
                    matched = term in prose
                if matched:
                    deprecated_hits += 1
                    errors.append(f"[{rel_doc}] Deprecated value still present: `{term}`")

    if broken_links == 0:
        passes.append(f"Relative Markdown links verified across {len(docs)} files (0 broken links).")
    if not args.allow_latex and latex_hits == 0:
        passes.append("Zero-LaTeX Math Policy verified (0 inline LaTeX leaks).")
    if deprecated_terms and deprecated_hits == 0:
        passes.append(f"Deprecated value sweep clean (0 hits for {deprecated_terms}).")

    # 4. Exact Content / SHA-256 Distribution Mirror Parity
    mirror_pairs = list(fed_mirrors)
    for pair_str in args.mirror:
        if ":" in pair_str:
            src_s, dst_s = pair_str.split(":", 1)
            mirror_pairs.append((ws_root / src_s.strip(), ws_root / dst_s.strip()))

    # Auto-detect docs/ -> */docs_reference/ mirrors if present in workspace
    docs_dir = ws_root / "docs"
    if docs_dir.is_dir():
        for ref_dir in ws_root.glob("*/docs_reference"):
            if ref_dir.is_dir():
                for mirrored_file in ref_dir.iterdir():
                    primary_file = docs_dir / mirrored_file.name
                    if mirrored_file.is_file() and primary_file.is_file():
                        mirror_pairs.append((primary_file, mirrored_file))

    for src_p, dst_p in mirror_pairs:
        if not src_p.is_file():
            errors.append(f"Mirror source missing: {src_p}")
            continue
        if not dst_p.is_file():
            errors.append(f"Mirror target missing: {dst_p}")
            continue
        src_hash = sha256_bytes(src_p)
        dst_hash = sha256_bytes(dst_p)
        rel_src = src_p.relative_to(ws_root).as_posix() if src_p.is_relative_to(ws_root) else src_p.as_posix()
        rel_dst = dst_p.relative_to(ws_root).as_posix() if dst_p.is_relative_to(ws_root) else dst_p.as_posix()
        if src_hash == dst_hash:
            passes.append(f"Mirror SHA-256 parity verified: `{rel_src}` == `{rel_dst}`")
        else:
            errors.append(
                f"Mirror content drift detected: `{rel_src}` ({src_hash[:8]}) != `{rel_dst}` ({dst_hash[:8]})"
            )

    # 5. Optional Delegation to Repo-Local scripts/audit_docs.py
    local_auditor = ws_root / "scripts" / "audit_docs.py"
    if local_auditor.is_file() and local_auditor.resolve() != Path(__file__).resolve():
        proc = subprocess.run(
            [sys.executable, str(local_auditor), str(ws_root)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if proc.returncode == 2 and "unrecognized arguments" in (proc.stderr or ""):
            proc = subprocess.run(
                [sys.executable, str(local_auditor)],
                cwd=str(ws_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        if proc.returncode == 0:
            passes.append("Repo-local `scripts/audit_docs.py` passed (exit code 0).")
        else:
            errors.append(f"Repo-local `scripts/audit_docs.py` failed:\n{proc.stdout}\n{proc.stderr}")

    print("=" * 70)
    print("XSYNC WORKSPACE DOCUMENTATION AUDIT SCORECARD")
    print("=" * 70)
    print(f"Workspace: {ws_root}")
    print(f"Files:     {len(docs)} (.md / .html)")
    print(f"Blocking:  {len(errors)}")
    print(f"Advisory:  {len(warnings)}")
    print("-" * 70)

    for p in passes:
        print(f"  ✓ {p}")
    for w in warnings:
        print(f"  ! {w}")
    for err in errors:
        print(f"  ✗ {err}")

    if errors:
        print("\n❌ VERDICT: FAIL (Resolve synchronization errors above)")
        return 1

    print("\n✅ VERDICT: PASS (100% Workspace Sync Invariants Verified)")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Universal Workspace Documentation Auditor (/xsync)")
    parser.add_argument("workspace", nargs="?", default=".", help="Target workspace root directory (default: .)")
    parser.add_argument(
        "--deprecated",
        type=str,
        default="",
        help="Comma-separated list of deprecated values/counts that must have 0 hits",
    )
    parser.add_argument(
        "--mirror",
        action="append",
        default=[],
        help="Explicit mirror pair 'src_rel_path:dst_rel_path' for SHA-256 content parity check",
    )
    parser.add_argument("--allow-latex", action="store_true", help="Allow inline LaTeX math syntax in docs")
    parser.add_argument(
        "--include-obsidian",
        action="store_true",
        help="Include directories containing .obsidian/ (use only when /xsync /xobsidian is active)",
    )
    parser.add_argument(
        "--federated",
        action="store_true",
        help="Enable 3-Signal Bounded Up-Tree & Cross-Repo Mirror Federation across sibling repos and global skills",
    )
    args = parser.parse_args()
    sys.exit(audit_workspace(args))


if __name__ == "__main__":
    main()
