# -*- coding: utf-8 -*-
"""
Universal Package, Upstream PR & Release Pre-Flight Audit Engine (/xpublish).
Performs secret, privacy, security, Flake8 quality, diff-scoped PR hygiene,
and platform-specific audits prior to releasing to GitHub, QGIS, Food4Rhino, or Upstream PRs.
"""

import sys
import os
import re
import ast
import argparse
import subprocess
import configparser
from pathlib import Path
from typing import Dict, Set
from urllib.parse import unquote

# Prevent bytecode debris in audited directories
sys.dont_write_bytecode = True

# Enforce UTF-8 standard output
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# ---------------------------------------------------------------------------
# High-Entropy & API Key Patterns
# ---------------------------------------------------------------------------
SECRET_PATTERNS = [
    ("AWS Access Key ID", re.compile(r"(?i)\b(AKIA[0-9A-Z]{16})\b")),
    (
        "GitHub Personal Access Token",
        re.compile(r"\b(ghp_[0-9a-zA-Z]{36}|gho_[0-9a-zA-Z]{36}|github_pat_[0-9a-zA-Z_]{82})\b")
    ),
    ("OpenAI API Key", re.compile(r"\b(sk-[a-zA-Z0-9]{20,}|sk-proj-[a-zA-Z0-9_\-]{20,})\b")),
    ("Anthropic API Key", re.compile(r"\bsk-ant-[a-zA-Z0-9\-_]{20,}\b")),
    ("Google API Key", re.compile(r"\b(AIza[0-9A-Za-z\-_]{35})\b")),
    ("Slack API Token", re.compile(r"\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b")),
    ("HuggingFace Token", re.compile(r"\b(hf_[0-9a-zA-Z]{34,})\b")),
    ("PyPI API Token", re.compile(r"\b(pypi-AgEIcHlwaS5vcmc[0-9a-zA-Z_\-]{50,})\b")),
    ("GitLab Personal Access Token", re.compile(r"\b(glpat-[0-9a-zA-Z_\-]{20,})\b")),
    ("NPM Access Token", re.compile(r"\b(npm_[0-9a-zA-Z]{36})\b")),
    ("Stripe Live Secret Key", re.compile(r"\b(sk_live_[0-9a-zA-Z]{24,})\b")),
    ("SendGrid API Key", re.compile(r"\b(SG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43})\b")),
    (
        "Discord Webhook URL",
        re.compile(r"https:\/\/(?:ptb\.|canary\.)?discord(?:app)?\.com\/api\/webhooks\/\d+\/[A-Za-z0-9_\-]+")
    ),
    ("RSA/SSH Private Key", re.compile(r"-----BEGIN (?:RSA|OPENSSH|DSA|EC|PGP) PRIVATE KEY-----")),
    (
        "Database Connection String",
        re.compile(r"(?i)\b(?:postgres|postgresql|mysql|mongodb\+srv):\/\/[^:\s]+:[^@\s]+@[^\s/]+")
    ),
    (
        "Generic Secret Assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|secret[_-]?key|auth[_-]?token|bearer[_-]?token|"
            r"private[_-]?key|db[_-]?password|client[_-]?secret)\s*[:=]\s*[\"']([a-zA-Z0-9_\-\.]{12,})[\"']"
        )
    ),
]

# ---------------------------------------------------------------------------
# Machine-Specific Path Patterns (Portability / PII)
# ---------------------------------------------------------------------------
PATH_PATTERNS = [
    ("Windows Absolute User Path", re.compile(r"(?i)\b([a-z]:[/\\]users[/\\](?!<)[a-zA-Z0-9_\-\.]+)")),
    (
        "macOS Absolute User Path",
        re.compile(r"(?:^|[\s\"'`=:(])(?<![a-zA-Z]:)(/Users/(?!<|shared\b|runner\b)[a-zA-Z0-9_\-\.]+/)"),
    ),
    ("Linux Absolute Home Path", re.compile(r"(?:^|[\s\"'`=:(])(/home/(?!<)[a-zA-Z0-9_\-\.]+)")),
]

EXCLUDED_PATH_ALLOWLIST = {
    "<user>", "<username>", "<your_username>", "users/default", "default/python/plugins", "users/...", "users\\..."
}

# ---------------------------------------------------------------------------
# Packaging Debris & Forbidden Extensions
# ---------------------------------------------------------------------------
FORBIDDEN_FILES = {
    ".ds_store", "thumbs.db", "desktop.ini"
}
FORBIDDEN_EXTS = {".pyc", ".pyo", ".pyd", ".swp", ".bak", ".tmp"}

PLACEHOLDER_GIT_AUTHORS = {
    "user", "admin", "administrator", "root", "ubuntu", "runner", "default", "owner", "pc", "desktop"
}


class AuditResult:
    def __init__(self):
        self.passed = True
        self.blocking_errors = []
        self.warnings = []
        self.checks_run = 0
        self.files_scanned = 0

    def add_blocking(self, msg: str, file_path: str = "", line_no: int = 0):
        self.passed = False
        prefix = f"[{file_path}:{line_no}] " if file_path and line_no else (f"[{file_path}] " if file_path else "")
        self.blocking_errors.append(f"{prefix}{msg}")

    def add_warning(self, msg: str, file_path: str = "", line_no: int = 0):
        prefix = f"[{file_path}:{line_no}] " if file_path and line_no else (f"[{file_path}] " if file_path else "")
        self.warnings.append(f"{prefix}{msg}")


def scan_line_for_secrets_and_paths(line: str, file_str: str, line_no: int, result: AuditResult):
    """Inspect a single line of text for secrets, tokens, or hardcoded machine user paths."""
    clean_line = line.strip()
    if clean_line.startswith("#") and "pattern" in clean_line.lower():
        return

    for label, pat in SECRET_PATTERNS:
        for match in pat.finditer(clean_line):
            matched_val = match.group(0)
            low_val = matched_val.lower()
            if label == "Generic Secret Assignment" and any(
                ph in low_val
                for ph in (
                    "your_",
                    "_here",
                    "placeholder",
                    "example",
                    "dummy",
                    "changeme",
                    "replace_",
                    "xxxx",
                    "todo",
                )
            ):
                continue
            masked = matched_val[:4] + "..." + matched_val[-4:] if len(matched_val) > 8 else "***"
            result.add_blocking(f"Potential {label} detected: `{masked}`", file_str, line_no)

    for label, pat in PATH_PATTERNS:
        for match in pat.finditer(clean_line):
            matched_path = match.group(1).lower()
            if not any(allowed in matched_path for allowed in EXCLUDED_PATH_ALLOWLIST):
                result.add_blocking(
                    f"Hardcoded absolute machine user path ({label}): `{match.group(1)}`", file_str, line_no
                )


def audit_file_content(path: Path, result: AuditResult, allowed_lines: Set[int] = None):
    """Scan file lines for secrets, credentials, and hardcoded absolute machine paths."""
    try:
        content = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        result.add_warning(f"Unable to read file: {e}", str(path))
        return

    for idx, line in enumerate(content.splitlines(), 1):
        if allowed_lines is not None and idx not in allowed_lines:
            continue
        scan_line_for_secrets_and_paths(line, str(path), idx, result)


def audit_python_ast(path: Path, result: AuditResult, allowed_lines: Set[int] = None):
    """Parse Python AST to detect dangerous security calls, shell injection, and broad exception passes."""
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        result.add_blocking(f"Python SyntaxError: {e.msg}", str(path), e.lineno or 0)
        return

    lines = source.splitlines()

    def in_scope(lineno: int) -> bool:
        return allowed_lines is None or lineno in allowed_lines

    class SecurityVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            if in_scope(getattr(node, "lineno", 0)):
                # 1. Check eval / exec / compile / __import__
                if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "compile", "__import__"}:
                    result.add_blocking(
                        f"Dangerous dynamic code execution call: `{node.func.id}()`", str(path), node.lineno
                    )

                # 2. Check os.system, os.popen, posix.system
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in {"system", "popen"}:
                        if isinstance(node.func.value, ast.Name) and node.func.value.id in {"os", "posix"}:
                            result.add_blocking(
                                f"Insecure `{node.func.value.id}.{node.func.attr}()` invocation. "
                                f"Use parameterized `subprocess.run(..., shell=False)`",
                                str(path), node.lineno
                            )

                # 3. Check subprocess shell=True
                if isinstance(node.func, ast.Attribute) and node.func.attr in {
                    "Popen", "run", "call", "check_call", "check_output"
                }:
                    for kw in node.keywords:
                        if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                            result.add_blocking(
                                "Subprocess execution with `shell=True` (Shell Injection risk)", str(path), node.lineno
                            )

                # 4. Check unsafe deserialization (pickle / shelve / marshal)
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in {"load", "loads"} and isinstance(node.func.value, ast.Name) and (
                        node.func.value.id in {"pickle", "_pickle", "marshal"}
                    ):
                        result.add_blocking(
                            f"Insecure deserialization with `{node.func.value.id}` (Arbitrary Code Execution risk)",
                            str(path), node.lineno
                        )
                    elif (
                        node.func.attr == "mktemp" and isinstance(node.func.value, ast.Name)
                        and node.func.value.id == "tempfile"
                    ):
                        result.add_blocking(
                            "Insecure `tempfile.mktemp()` (Symlink race condition risk). "
                            "Use `NamedTemporaryFile` or `mkstemp`", str(path), node.lineno
                        )
                    elif node.func.attr in {
                        "VirtualAlloc", "VirtualAllocEx", "WriteProcessMemory", "CreateRemoteThread"
                    }:
                        result.add_blocking(
                            f"High-risk memory injection API call detected: `{node.func.attr}`", str(path), node.lineno
                        )

                # 5. Check outbound network sockets / HTTP requests
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in {"urlopen", "get", "post", "put", "delete", "connect"} and (
                        isinstance(node.func.value, ast.Name)
                    ):
                        if node.func.value.id in {"requests", "urllib", "httpx", "aiohttp", "socket"}:
                            result.add_warning(
                                f"Network outbound call `{node.func.value.id}.{node.func.attr}()` detected. "
                                "Ensure this call is user-authorized, HTTPS-only, and transmits no private telemetry.",
                                str(path), node.lineno
                            )

            self.generic_visit(node)

        def visit_ExceptHandler(self, node):
            if in_scope(getattr(node, "lineno", 0)):
                if node.body and len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    end_line = getattr(node.body[0], "lineno", node.lineno)
                    span_lines = lines[max(0, node.lineno - 1): min(len(lines), end_line)]
                    if not any("# nosec" in ln for ln in span_lines):
                        is_broad = False
                        if node.type is None:
                            is_broad = True
                        elif isinstance(node.type, ast.Name) and node.type.id in {"Exception", "BaseException"}:
                            is_broad = True

                        if is_broad:
                            result.add_warning(
                                "Broad `except Exception: pass` without `# nosec B110` or logging",
                                str(path),
                                node.lineno,
                            )

            self.generic_visit(node)

    visitor = SecurityVisitor()
    visitor.visit(tree)


def audit_flake8(target: Path, result: AuditResult, scoped_lines_by_file: Dict[Path, Set[int]] = None):
    """Audit project code quality using Flake8 (optionally scoped to PR diff lines)."""
    flake8_cfg = target / ".flake8"
    if not flake8_cfg.exists():
        parent_cfg = target.parent / ".flake8"
        if parent_cfg.exists():
            flake8_cfg = parent_cfg

    cmd = [sys.executable, "-m", "flake8"]
    if flake8_cfg.exists():
        cmd.append(f"--config={flake8_cfg}")

    if scoped_lines_by_file is not None:
        py_targets = [str(p) for p in scoped_lines_by_file.keys() if p.suffix.lower() == ".py" and p.exists()]
        if not py_targets:
            return
        cmd.extend(py_targets)
    else:
        cmd.append(str(target))

    try:
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        output = (proc.stdout or "").strip()

        if proc.returncode != 0 and output:
            kept = 0
            for line in output.splitlines():
                clean = line.strip()
                if not clean:
                    continue
                if scoped_lines_by_file is not None:
                    m = re.match(r"^(.*?):(\d+):(\d+):\s*(.*)$", clean)
                    if m:
                        fpath = Path(m.group(1)).resolve()
                        lno = int(m.group(2))
                        allowed = scoped_lines_by_file.get(fpath)
                        if allowed is not None and lno not in allowed:
                            continue
                kept += 1
                result.add_blocking(f"Flake8 Style/Lint Violation: {clean}")
            if kept == 0 and scoped_lines_by_file is not None:
                print("  ✓ Diff-Scoped Flake8 Audit: 100% CLEAN on modified lines")
        elif proc.returncode == 0:
            print("  ✓ Flake8 Code Quality Audit: 100% CLEAN (0 violations)")
    except FileNotFoundError:
        result.add_warning(
            "Flake8 module not installed in current Python environment. Run: pip install flake8"
        )
    except Exception as e:
        result.add_warning(f"Flake8 audit failed to run: {e}")


def parse_unified_diff_added_lines(target: Path, diff_text: str) -> Dict[Path, Set[int]]:
    """Parse `git diff -U0` output to map each modified file to its set of added/modified line numbers."""
    added_by_file: Dict[Path, Set[int]] = {}
    current_file: Path = None
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

    for raw_line in diff_text.splitlines():
        if raw_line.startswith("+++ b/"):
            rel_path = raw_line[6:].strip()
            current_file = (target / rel_path).resolve()
            added_by_file.setdefault(current_file, set())
        elif raw_line.startswith("+++ /dev/null"):
            current_file = None
        elif current_file is not None and raw_line.startswith("@@ "):
            m = hunk_re.match(raw_line)
            if m:
                start_line = int(m.group(1))
                count = int(m.group(2)) if m.group(2) is not None else 1
                for lno in range(start_line, start_line + count):
                    added_by_file[current_file].add(lno)

    return added_by_file


def audit_pr_diff_invariants(
    target: Path, result: AuditResult, base_ref: str = "", skip_flake8: bool = False
):
    """
    Execute diff-scoped Upstream PR pre-flight audit (`--platform pr`):
    1. Verify git repository & clean untracked worktree (`git status --porcelain`).
    2. Verify Git author identity is not an OS placeholder (`User`, `Admin`, `root`, `ubuntu`, `localhost`).
    3. Resolve diff (`base_ref`, working tree changes, or `HEAD~1..HEAD`) and inspect added lines (`+`) only.
    4. Block accidental CRLF line-ending injection or `100644 -> 100755` executable mode flips.
    5. Run diff-scoped Secret, Machine-Path, Python AST Security, and Flake8 checks on touched lines/files.
    """
    git_dir = target / ".git"
    if not git_dir.exists():
        result.add_blocking(
            "Target directory is not a Git repository (`.git` missing for `--platform pr`)", str(target)
        )
        return

    # 1. Check untracked worktree debris (`git status --porcelain`)
    st_proc = subprocess.run(
        ["git", "-C", str(target), "status", "--porcelain"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    for st_line in (st_proc.stdout or "").splitlines():
        if st_line.startswith("?? "):
            untracked = st_line[3:].strip()
            result.add_blocking(
                f"Untracked unignored file in worktree: `{untracked}`. "
                "Remove scratch debris or stage intentionally before shipping PR.",
                str(target / untracked),
            )

    # 2. Check Git author identity (latest commit or git config)
    author_proc = subprocess.run(
        ["git", "-C", str(target), "log", "-1", "--format=%an|%ae"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    author_out = (author_proc.stdout or "").strip()
    if "|" in author_out:
        author_name, author_email = [p.strip() for p in author_out.split("|", 1)]
        if author_name.lower() in PLACEHOLDER_GIT_AUTHORS:
            result.add_blocking(
                f"Git commit author name `{author_name}` is an unconfigured OS placeholder. "
                "Set `git config user.name` to your real identity before pushing.",
                str(target),
            )
        if not author_email or "@" not in author_email or author_email.lower().endswith(("@localhost", "@example.com")):
            result.add_blocking(
                f"Git commit author email `{author_email}` is invalid or local-only. "
                "Set `git config user.email` to your GitHub-linked email before pushing.",
                str(target),
            )

    # 3. Determine diff base and capture unified diff (`-U0`)
    diff_cmd = ["git", "-C", str(target), "diff", "-U0"]
    if base_ref:
        diff_cmd.append(base_ref)
    else:
        # Check if there are staged or unstaged changes against HEAD; otherwise compare HEAD~1..HEAD
        wt_proc = subprocess.run(
            ["git", "-C", str(target), "diff", "--name-only", "HEAD"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if (wt_proc.stdout or "").strip():
            diff_cmd.append("HEAD")
        else:
            diff_cmd.extend(["HEAD~1", "HEAD"])

    diff_proc = subprocess.run(
        diff_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    diff_text = diff_proc.stdout or ""
    added_by_file = parse_unified_diff_added_lines(target, diff_text)
    result.files_scanned = len(added_by_file)

    # 4. Check accidental file-mode flips (`100644 -> 100755`) & CRLF injection in touched files
    cur_diff_file = ""
    old_mode = ""
    for raw_line in diff_text.splitlines():
        if raw_line.startswith("diff --git "):
            parts = raw_line.split(" b/")
            cur_diff_file = parts[-1].strip() if len(parts) > 1 else ""
            old_mode = ""
        elif raw_line.startswith("old mode "):
            old_mode = raw_line.split()[-1].strip()
        elif raw_line.startswith("new mode "):
            new_mode = raw_line.split()[-1].strip()
            if old_mode == "100644" and new_mode == "100755" and not cur_diff_file.endswith(".sh"):
                result.add_blocking(
                    f"Accidental executable file-mode flip (`100644 -> 100755`) on `{cur_diff_file}`",
                    str(target / cur_diff_file),
                )

    content_suffixes = {
        ".py", ".txt", ".md", ".json", ".yml", ".yaml", ".ini", ".cs",
        ".xml", ".html", ".env", ".ps1", ".sh", ".toml", ".cfg", ".conf",
    }

    for fpath, line_set in added_by_file.items():
        if not fpath.exists() or not fpath.is_file():
            continue
        fname = fpath.name.lower()
        if fname in FORBIDDEN_FILES or fpath.suffix.lower() in FORBIDDEN_EXTS or fname.startswith("scratch"):
            result.add_blocking(f"Forbidden build or scratch artifact in PR diff: `{fpath.name}`", str(fpath))

        # Check accidental CRLF injection on text files (compare against base blob EOL)
        if fpath.suffix.lower() in content_suffixes and fpath.suffix.lower() != ".ps1":
            try:
                raw_bytes = fpath.read_bytes()
                if b"\r\n" in raw_bytes:
                    rel_git = fpath.resolve().relative_to(target.resolve()).as_posix()
                    ref_for_blob = base_ref if base_ref else "HEAD"
                    blob_proc = subprocess.run(
                        ["git", "-C", str(target), "show", f"{ref_for_blob}:{rel_git}"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False,
                    )
                    base_has_crlf = blob_proc.returncode == 0 and (b"\r\n" in (blob_proc.stdout or b""))
                    eol_proc = subprocess.run(
                        ["git", "-C", str(target), "ls-files", "--eol", "--", rel_git],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        check=False,
                    )
                    eol_out = (eol_proc.stdout or "").strip()
                    index_is_lf = "i/lf" in eol_out
                    if not base_has_crlf and not index_is_lf:
                        result.add_blocking(
                            "CRLF (`\\r\\n`) line endings injected into LF-based file. "
                            "Normalize to LF (`\\n`) before PR push.",
                            str(fpath),
                        )
            except OSError as exc:
                result.add_warning(f"Unable to inspect line endings: {exc}", str(fpath))

        if fpath.suffix.lower() in content_suffixes or fname in {".env", "env"}:
            audit_file_content(fpath, result, allowed_lines=line_set)

        if fpath.suffix.lower() == ".py" and not fname.startswith("test_"):
            audit_python_ast(fpath, result, allowed_lines=line_set)
        elif fpath.suffix.lower() == ".py":
            # Still verify valid Python syntax on test files
            try:
                ast.parse(fpath.read_text(encoding="utf-8", errors="ignore"), filename=str(fpath))
            except SyntaxError as e:
                result.add_blocking(f"Python SyntaxError in test file: {e.msg}", str(fpath), e.lineno or 0)

    if not skip_flake8 and added_by_file:
        print("🔍 Checking Diff-Scoped Flake8 code quality on modified lines...")
        audit_flake8(target, result, scoped_lines_by_file=added_by_file)


def audit_qgis_metadata(path: Path, result: AuditResult):
    """Audit QGIS metadata.txt for interpolation syntax, required fields, and versions."""
    if not path.exists():
        result.add_blocking("Missing mandatory `metadata.txt` for QGIS plugin", str(path))
        return

    content = path.read_text(encoding="utf-8", errors="ignore")

    for line_no, line in enumerate(content.splitlines(), 1):
        if "%" in line:
            unescaped = re.search(r"(?<!%)%(?!%)", line)
            if unescaped and not line.strip().startswith("#"):
                result.add_blocking(
                    "Unescaped `%` character in metadata.txt will cause QGIS server `InterpolationSyntaxError`. "
                    "Use `percent` or `%%`",
                    str(path), line_no
                )

    cp = configparser.ConfigParser(interpolation=None)
    try:
        cp.read(str(path), encoding="utf-8")
        if not cp.has_section("general"):
            result.add_blocking("`metadata.txt` must contain a `[general]` section", str(path))
            return

        required_fields = ["name", "qgisMinimumVersion", "description", "about", "version", "author", "email"]
        for field in required_fields:
            if not cp.has_option("general", field) or not cp.get("general", field).strip():
                result.add_blocking(f"Mandatory metadata field missing or empty: `{field}`", str(path))

        for opt in ["repository", "tracker", "homepage"]:
            if cp.has_option("general", opt):
                val = cp.get("general", opt)
                if not val.startswith(("http://", "https://")):
                    result.add_warning(f"Metadata link `{opt}` does not start with https://: `{val}`", str(path))

    except Exception as e:
        result.add_blocking(f"Failed to parse `metadata.txt`: {e}", str(path))


def audit_qgis_plugin_invariants(target: Path, result: AuditResult, skip_qt6: bool = False):
    """Verify core QGIS plugin requirements: classFactory, icons, and Qt6 forward compatibility."""
    init_path = target / "__init__.py"
    if not init_path.exists():
        result.add_blocking("Missing mandatory `__init__.py` hook for QGIS plugin", str(target))
    else:
        init_content = init_path.read_text(encoding="utf-8", errors="ignore")
        if "def classFactory(" not in init_content:
            result.add_blocking("`__init__.py` must define `def classFactory(iface):`", str(init_path))

    icon_png = target / "icon.png"
    icon_svg = target / "icon.svg"
    if not icon_png.exists() and not icon_svg.exists():
        result.add_warning(
            "Missing `icon.png` or `icon.svg` (required for QGIS toolbar and plugin manager)", str(target)
        )

    # Co-located Qt6 AST check in the same `scripts/` folder
    if not skip_qt6:
        qt6_script = Path(__file__).resolve().parent / "check_qt6.py"
        if qt6_script.exists():
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("check_qt6", str(qt6_script))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                if hasattr(mod, "audit_directory_for_qt6"):
                    qt6_issues = mod.audit_directory_for_qt6(target)
                    blocking_qt6 = [issue for issue in qt6_issues if issue[3] == "ERROR"]
                    if blocking_qt6:
                        for rel, line, col, sev, msg in blocking_qt6:
                            result.add_blocking(
                                f"Qt6 / QGIS 4 forward-compatibility violation: {msg}", str(target / rel), line
                            )
                    else:
                        print("  ✓ Qt6 / QGIS 4 Forward-Compatibility: 100% COMPLIANT (Green badge)")
            except Exception as e:
                result.add_warning(f"Qt6 audit could not execute: {e}")


def run_audit(
    target_dir: str,
    platform: str = "generic",
    skip_flake8: bool = False,
    skip_qt6: bool = False,
    base_ref: str = "",
) -> AuditResult:
    target = Path(target_dir).resolve()
    result = AuditResult()

    if not target.exists():
        result.add_blocking(f"Target directory does not exist: {target}")
        return result

    print(f"🔍 Starting /xpublish audit on: {target}")
    print(f"📦 Platform Profile: {platform.upper()}\n")

    if platform.lower() == "pr":
        audit_pr_diff_invariants(target, result, base_ref=base_ref, skip_flake8=skip_flake8)
        return result

    all_files = []
    excluded_walk_dirs = {
        ".git",
        "__pycache__",
        "dist",
        "build",
        ".idea",
        ".vscode",
        ".venv",
        "venv",
        "env",
        "node_modules",
        ".pytest_cache",
        ".mypy_cache",
        ".tox",
        "site-packages",
    }
    for root, dirs, files in os.walk(target):
        if "__pycache__" in dirs and any((Path(root) / "__pycache__").iterdir()):
            result.add_warning(f"Packaging debris detected: `__pycache__` directory at `{Path(root) / '__pycache__'}`")
        dirs[:] = [d for d in dirs if d not in excluded_walk_dirs]
        for f in files:
            all_files.append(Path(root) / f)

    result.files_scanned = len(all_files)

    # 1. Scan packaging hygiene
    for f in all_files:
        fname = f.name.lower()
        if fname in FORBIDDEN_FILES or f.suffix.lower() in FORBIDDEN_EXTS:
            result.add_warning(f"Forbidden or build artifact file present in package: `{f.name}`", str(f))

    # 2. Scan file content (secrets, machine paths)
    content_suffixes = {
        ".py", ".txt", ".md", ".json", ".yml", ".yaml", ".ini", ".cs",
        ".xml", ".html", ".env", ".ps1", ".sh", ".toml", ".cfg", ".conf",
    }
    overclaim = re.compile(r"(?i)\b(published|1-click install|status:\s*live)\b")
    for f in all_files:
        if not f.is_file():
            continue
        suffix = f.suffix.lower()
        name = f.name.lower()
        if suffix in content_suffixes or name in {".env", "env"}:
            audit_file_content(f, result)
        if suffix == ".md" and name.startswith("readme"):
            try:
                text = f.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                text = ""
            for i, line in enumerate(text.splitlines(), 1):
                if overclaim.search(line) and "pending" not in line.lower() and "registered" not in line.lower():
                    result.add_warning(
                        "README may overclaim public availability (Published / LIVE / 1-click). "
                        "Use REGISTERED / PREPARED / IN PIPELINE unless a receipt exists. "
                        "Vocabulary is owned by /xsync; this is advisory.",
                        str(f),
                        i,
                    )

    # 3. Scan Python AST
    py_files = [f for f in all_files if f.suffix.lower() == ".py" and not f.name.startswith("test_")]
    for py in py_files:
        audit_python_ast(py, result)

    # 4. Flake8 Code Quality Audit
    if not skip_flake8 and platform.lower() != "skill":
        print("🔍 Checking Flake8 code quality & styling...")
        audit_flake8(target, result)

    # 5. Platform-Specific Invariants
    if platform.lower() == "skill":
        audit_skill_invariants(target, result)

    elif platform.lower() == "qgis":
        meta_file = target / "metadata.txt"
        audit_qgis_metadata(meta_file, result)
        audit_qgis_plugin_invariants(target, result, skip_qt6=skip_qt6)

        dist_dir = target / "dist"
        if dist_dir.exists():
            zips = list(dist_dir.glob("*.zip"))
            if zips:
                result.add_warning(
                    "dist/*.zip present. For QGIS single-root zip packaging, run `package_qgis.py` in /xpublish."
                )

    elif platform.lower() == "food4rhino":
        assemblies = list(target.glob("**/*.gha")) + list(target.glob("**/*.dll"))
        sample_gh = list(target.glob("**/*.gh"))
        if not assemblies:
            result.add_blocking(
                "No compiled `.gha` or `.dll` found. Food4Rhino requires a compiled plugin assembly."
            )
        if not sample_gh:
            result.add_warning("No sample `.gh` canvas found. Recommended for Food4Rhino.")

    # 6. License & README (skipped for skill profile)
    if platform.lower() != "skill":
        has_readme = any(f.name.lower().startswith("readme") for f in all_files)
        has_license = any(f.name.lower().startswith("license") for f in all_files)
        plat = platform.lower()
        if not has_readme:
            result.add_warning("Missing README.md.")
        if not has_license:
            if plat == "github":
                result.add_blocking("Missing LICENSE. GitHub platform profile requires an OSI-style LICENSE file.")
            else:
                result.add_warning("Missing LICENSE file.")

    return result


def audit_skill_invariants(target: Path, result: AuditResult):
    """Audit agent skill directory against /xcreate-skill and /xlearn standards (frontmatter, links, invariants)."""
    skill_md = target / "SKILL.md"
    if not skill_md.is_file() and (target / "skills").is_dir():
        child_skills = sorted((target / "skills").glob("*/SKILL.md"))
        if child_skills:
            for child_md in child_skills:
                audit_skill_invariants(child_md.parent, result)
            return
    if not skill_md.exists():
        result.add_blocking("Missing mandatory `SKILL.md` in skill directory", str(target))
        return

    if (target / target.name).exists() and (target / target.name).is_dir():
        result.add_blocking(f"Recursive self-nesting detected: `{target.name}/{target.name}`", str(target))

    target_abs = str(target.resolve()).replace("\\", "/")
    home_agents_abs = str((Path.home() / ".agents").resolve()).replace("\\", "/")
    is_workspace_agents_silo = (
        ("/.agents/skills/" in target_abs or target_abs.endswith("/.agents/skills") or "/.agents/" in target_abs)
        and not target_abs.startswith(home_agents_abs)
    )
    if is_workspace_agents_silo:
        result.add_warning(
            f"Skill is isolated in workspace `.agents/skills/` ({target.name}). "
            "Universal Globalization standard recommends storing shared agent skills in your Global Agent "
            "Skills Root (`~/.agents/skills/<name>/` or `~/.<agent>/skills/<name>/`) so they appear "
            "in every workspace and synchronize automatically across all devices.",
            str(skill_md),
        )

    try:
        content = skill_md.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        result.add_blocking(f"Failed to read `SKILL.md`: {e}", str(skill_md))
        return

    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        result.add_blocking("Frontmatter must start with `---` on line 1", str(skill_md), 1)
        return

    fm_lines = []
    end_idx = -1
    for i, line in enumerate(lines[1:], 2):
        if line.strip() == "---":
            end_idx = i
            break
        fm_lines.append(line)

    if end_idx == -1:
        result.add_blocking("Frontmatter missing closing `---` delimiter", str(skill_md))
        return

    fm_data = {}
    try:
        import yaml
        fm_data = yaml.safe_load("\n".join(fm_lines)) or {}
    except Exception:
        cur_key = None
        cur_parts = []
        for fm_line in fm_lines:
            if re.match(r"^[a-zA-Z0-9_-]+\s*:", fm_line):
                if cur_key is not None:
                    fm_data[cur_key] = " ".join(p for p in cur_parts if p).strip()
                k, v = fm_line.split(":", 1)
                cur_key = k.strip()
                v_clean = re.sub(r"^[>|]\s*", "", v.strip()).strip("\"'")
                if v_clean.lower() in ("true", "false"):
                    fm_data[cur_key] = v_clean.lower() == "true"
                    cur_key = None
                    cur_parts = []
                else:
                    cur_parts = [v_clean] if v_clean else []
            elif cur_key is not None:
                cur_parts.append(fm_line.strip())
        if cur_key is not None:
            fm_data[cur_key] = " ".join(p for p in cur_parts if p).strip()

    if not isinstance(fm_data, dict):
        result.add_blocking("YAML frontmatter must be a valid key-value mapping", str(skill_md))
        return

    # 1. Check Name
    name = fm_data.get("name")
    name_regex = re.compile(r"^[a-z0-9-]+$")
    if not name:
        result.add_blocking("Frontmatter missing mandatory field: `name`", str(skill_md))
    else:
        name_str = str(name).strip()
        if not name_regex.match(name_str):
            result.add_blocking(
                f"Invalid skill name format `{name_str}`. Must be lowercase alphanumeric and hyphens (`^[a-z0-9-]+$`)",
                str(skill_md),
            )
        if len(name_str) > 64:
            result.add_blocking(f"Skill name exceeds 64 characters ({len(name_str)} chars)", str(skill_md))
        if name_str != target.name and not target.name.startswith("_") and "/plugins/" not in target_abs:
            result.add_warning(
                f"Skill folder name `{target.name}` does not match frontmatter name `{name_str}`", str(skill_md)
            )

    # 2. Check Description
    desc = fm_data.get("description")
    if not desc:
        result.add_blocking("Frontmatter missing mandatory field: `description`", str(skill_md))
    else:
        desc_str = str(desc).strip()
        if len(desc_str) > 1024:
            result.add_blocking(f"Skill description exceeds 1024 characters ({len(desc_str)} chars)", str(skill_md))
        elif len(desc_str) > 500:
            result.add_warning(
                f"Skill description is {len(desc_str)} characters long (>500 chars). "
                "Aim for a compact description (≤ 250-400 chars) to prevent triggering the host AI agent's "
                "system prompt context budget limit, which silently drops skills from the active list.",
                str(skill_md),
            )

        is_disabled = fm_data.get("disable-model-invocation", False) is True
        if not is_disabled:
            has_pos = any(k in desc_str.lower() for k in ["use when", "use this skill", "trigger", "when the user"])
            if not has_pos:
                result.add_warning(
                    "Description lacks clear positive triggers (e.g. `Use when...`, `Use this skill when...`)",
                    str(skill_md),
                )
            has_neg = any(k in desc_str.lower() for k in ["do not use", "not for", "don't use", "exclude"])
            if not has_neg:
                result.add_warning(
                    "Description lacks explicit negative exclusion clause (e.g. `Do NOT use for...`)",
                    str(skill_md),
                )

    # 3. Check Frontmatter Compatibility Flags
    if fm_data.get("disable-model-invocation", False) is True:
        result.add_warning(
            "`disable-model-invocation: true` detected. This skill is user-invoked only and will be "
            "completely stripped from the LLM prompt context (<skills>) in host agent runtimes. "
            "Avoid if you expect pair-programming agents to discover and invoke it autonomously.",
            str(skill_md),
        )
    if "argument-hint" in fm_data:
        result.add_warning(
            "Non-standard frontmatter key `argument-hint` detected. "
            "Universal agent skill schemas standardize on `name` and `description`.",
            str(skill_md),
        )

    # 4. Anti-Hardcoded Bucket 3 Quotas, Over-Specific Equations & Persona/Project Neutrality Scanner
    if len(lines) > 500:
        result.add_warning(
            f"`SKILL.md` is {len(lines)} lines long (>500-line budget). "
            "Disclose deep reference matrices or taxonomies into `references/*.md` behind context pointers "
            "to prevent skill Sprawl.",
            str(skill_md),
        )

    persona_pat = re.compile(
        r"(?i)\b(asus\s+laptop|home\s+pc|windows\s+desktop\s+pc|on\s+nut|01_on_nut|"
        r"161-rai|khlong\s+prawet|traffy|ON_v[0-9]|thesis_architecture\.html|slide_style_showcase_v2\.html)\b"
    )
    bucket3_pat = re.compile(
        r"(?i)(≤\s*150[- ]words?|150[- ]word\s+caveman|≤\s*12\s+lines|"
        r"\b4[-–]12`?\s+agents\b|\b4[-–]5`?\s+agents\b|\bup\s+to\s+`?6`?\s+concurrent\s+scouts\b|"
        r"<\s*30-line\s+reproduction)"
    )
    overfit_law_pat = re.compile(
        r"(\bx\s*=\s*0\s*(?:->|→|=>|⇒)\s*y\s*=\s*0(?:\.0)?\b|"
        r"d\s*log\s*\\?\|?Y\\?\|?\s*/\s*d\s*log\s*(?:alpha|α)\s*==\s*p|"
        r"\bf\(x\)\[k:\]\s*==\s*f\(x\[k:\]\)|"
        r"__module__\s*==\s*(?:prod_module|target_module)\b)"
    )
    negation_tags = (
        "Bucket 3",
        "Anti-Pattern",
        "Strictly Forbidden",
        "Forbidden",
        "Never",
        "NEVER",
        "Flaw",
        "Instead of",
        "fails on",
        "fails when",
        "breaks on",
        "zero unqualified",
        "over-specific",
        "❌",
    )
    for i, line in enumerate(lines, 1):
        m_pers = persona_pat.search(line)
        if m_pers:
            result.add_warning(
                f"Potential hardcoded personal hardware/project/thesis string detected: `{m_pers.group(0)}`. "
                "Use universal, project-agnostic terminology.",
                str(skill_md),
                i,
            )
        if not any(tag in line for tag in negation_tags):
            m_b3 = bucket3_pat.search(line)
            if m_b3:
                result.add_warning(
                    f"Potential hardcoded Bucket 3 task/swarm quota detected: `{m_b3.group(0)}`. "
                    "Use the 4-Law Elastic Cognitive Swarm (`N x K x T`) and Pointer-Not-Payload contract instead.",
                    str(skill_md),
                    i,
                )
            m_ovf = overfit_law_pat.search(line)
            if m_ovf:
                result.add_warning(
                    f"Potential over-specific session equation/probe detected: `{m_ovf.group(0)}`. "
                    "Apply the 5-Gate Universal Law Falsification Protocol in /xcreate-skill and /xlearn "
                    "(use Zero-Forcing Equilibrium `Δx = 0 => Δy = 0`, baseline-subtracted `ΔY(α) = Y(α) - Y(0)`, "
                    "Prefix Causality / finite lookback `W`, and wrapper-safe live entrypoint calls).",
                    str(skill_md),
                    i,
                )

    # 5. Markdown Links, Forward-Slash & Zero-LaTeX Typography Audit
    latex_macro_pat = re.compile(r"\\(?:rightarrow|leftarrow|leftrightarrow|times|approx|pm|leq|geq)\b")
    for md_file in target.rglob("*.md"):
        try:
            md_text = md_file.read_text(encoding="utf-8", errors="replace")
        except Exception as exc:
            _ = exc
            continue

        clean_md = re.sub(r"(`{3,}|~{3,})[\s\S]*?\1", "", md_text)
        clean_md = re.sub(r"``[^\n]+?``", "", clean_md)
        clean_md = re.sub(r"\[`([^`\n]+)`\]\(", r"[\1](", clean_md)
        clean_md = re.sub(r"`[^`\n]+`", "", clean_md)

        for m_lat in latex_macro_pat.finditer(clean_md):
            result.add_warning(
                f"Raw LaTeX macro `{m_lat.group(0)}` outside code span. Use native UTF-8 Unicode symbols.",
                str(md_file),
            )

        for m in re.finditer(r"\[([^\]]+)\]\(([^)]+)\)", clean_md):
            link_text, raw_url = m.group(1), m.group(2).strip()
            link_url = raw_url.split()[0].strip("<>") if raw_url else ""
            if "\\" in link_url:
                result.add_blocking(
                    f"Markdown link contains backslash: `[{link_text}]({link_url})`. "
                    "Always use POSIX forward slashes (`/`).",
                    str(md_file),
                )
            if link_url and not link_url.startswith(
                (
                    "http://",
                    "https://",
                    "#",
                    "mailto:",
                    "file://",
                    "conversation://",
                    "data:",
                    "javascript:",
                    "vscode:",
                    "obsidian://",
                    "/",
                )
            ):
                rel_clean = unquote(link_url.split("#")[0].split("?")[0].strip())
                if rel_clean:
                    target_file = (md_file.parent / rel_clean).resolve()
                    if not target_file.exists():
                        result.add_warning(
                            f"Broken relative markdown link: `[{link_text}]({link_url})` (file not found)",
                            str(md_file),
                        )

    # 6. Helper Scripts Audit
    scripts_dir = target / "scripts"
    if scripts_dir.exists() and scripts_dir.is_dir():
        for py_file in scripts_dir.rglob("*.py"):
            try:
                py_src = py_file.read_text(encoding="utf-8", errors="replace")
                ast.parse(py_src, filename=str(py_file))
            except SyntaxError as se:
                result.add_blocking(f"Python SyntaxError in helper script: {se}", str(py_file), se.lineno or 0)
            except Exception as e:
                result.add_warning(f"Could not parse script: {e}", str(py_file))
                continue

            if "sys.stdout" not in py_src or "reconfigure" not in py_src:
                result.add_warning(
                    "Helper script lacks UTF-8 `sys.stdout.reconfigure(encoding='utf-8')` guard", str(py_file)
                )
            if "dont_write_bytecode" not in py_src:
                result.add_warning(
                    "Helper script lacks `sys.dont_write_bytecode = True` guard (risks `__pycache__` debris)",
                    str(py_file),
                )


def main():
    parser = argparse.ArgumentParser(
        description="Universal Package, Upstream PR & Release Pre-Flight Audit Engine (/xpublish)"
    )
    parser.add_argument("target", help="Path to project directory or git repository to audit")
    parser.add_argument(
        "--platform",
        choices=["generic", "pr", "qgis", "food4rhino", "github", "skill"],
        default="generic",
        help="Platform profile to evaluate against",
    )
    parser.add_argument(
        "--base-ref",
        default="",
        help="Explicit git base ref for --platform pr diff comparison (default: working tree or HEAD~1)",
    )
    parser.add_argument("--skip-flake8", action="store_true", help="Skip Flake8 code quality audit")
    parser.add_argument("--skip-qt6", action="store_true", help="Skip Qt6 / QGIS 4 forward-compatibility AST scan")
    args = parser.parse_args()

    res = run_audit(
        args.target,
        platform=args.platform,
        skip_flake8=args.skip_flake8,
        skip_qt6=args.skip_qt6,
        base_ref=args.base_ref,
    )

    print("\n" + "=" * 70)
    print("PRE-FLIGHT AUDIT SCORECARD")
    print("=" * 70)
    print(f"Target:    {args.target}")
    print(f"Platform:  {args.platform}")
    print(f"Files:     {res.files_scanned}")
    print(f"Blocking:  {len(res.blocking_errors)}")
    print(f"Advisory:  {len(res.warnings)}")
    print("-" * 70)

    if res.blocking_errors:
        print("\n❌ BLOCKING ISSUES (must resolve before publishing):")
        for err in res.blocking_errors:
            print(f"  • {err}")

    if res.warnings:
        print("\n⚠️  ADVISORY NOTICES:")
        for warn in res.warnings:
            print(f"  - {warn}")

    if res.passed and not res.blocking_errors:
        print("\n✅ VERDICT: PASS (100% Risk-Proof & Safe to Publish)")
        sys.exit(0)
    else:
        print("\n❌ VERDICT: FAIL (Resolve blocking errors before publishing)")
        sys.exit(1)


if __name__ == "__main__":
    main()
