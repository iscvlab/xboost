# -*- coding: utf-8 -*-
"""
Deterministic Evidence, Deep-Link URL, and Dataset Schema Verifier for /xdeep-research.
Validates Markdown (.md) and JSON (.json) research deliverables against:
  1. Unfinished placeholders ([TBD], TODO, FIXME, example.com)
  2. Lazy root-domain URLs (e.g., https://domain.org/ with no specific path/query)
  3. JSON dataset schema completeness, record quotas, and numeric/year bounds
  4. Optional concurrent HTTP reachability probing (--check-http)
"""

import sys
import re
import json
import argparse
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.dont_write_bytecode = True
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

PLACEHOLDER_PATTERNS = [
    (
        "Unresolved [TBD] / [TODO] / [FIXME] marker",
        re.compile(r"\[(?:TBD|TODO|FIXME|INSERT[^\]]*)\]", re.IGNORECASE),
    ),
    ("Dummy example domain", re.compile(r"https?://(?:www\.)?example\.(?:com|org|net)\b", re.IGNORECASE)),
    ("Truncated placeholder URL", re.compile(r"https?://\.\.\.")),
]

URL_REGEX = re.compile(r"https?://[^\s\]>\"'`|]+")


def extract_urls(text: str):
    """Extract unique HTTP/HTTPS URLs from text, preserving balanced parentheses inside URLs."""
    raw = URL_REGEX.findall(text)
    cleaned = []
    seen = set()
    for u in raw:
        u_clean = u.rstrip(".,;:!?'\"*_~>")
        # Strip trailing ')' only when unmatched (e.g. closing a Markdown link '[label](url)')
        while u_clean.endswith(")") and u_clean.count(")") > u_clean.count("("):
            u_clean = u_clean[:-1].rstrip(".,;:!?'\"*_~>")
        if u_clean and u_clean not in seen:
            seen.add(u_clean)
            cleaned.append(u_clean)
    return cleaned


def is_root_domain_url(url: str) -> bool:
    """Return True if the URL points only to a bare domain homepage with no path or query."""
    try:
        parsed = urlparse(url)
        path = (parsed.path or "").strip("/")
        return len(path) == 0 and not parsed.query and not parsed.fragment
    except Exception:
        return True


def check_url_http(url: str, timeout: float = 8.0):
    """Probe URL reachability via HEAD then GET fallback with a standard browser User-Agent."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    for method in ("HEAD", "GET"):
        try:
            req = Request(url, headers=headers, method=method)
            with urlopen(req, timeout=timeout) as resp:
                code = getattr(resp, "status", 200)
                if 200 <= code < 400:
                    return True, code, "OK"
        except HTTPError as e:
            if method == "HEAD":
                continue
            if e.code in (401, 403, 406, 429, 503):
                # Bot-protected / rate-limited server, but route exists (not 404)
                return True, e.code, f"Protected/Rate-Limited ({e.code})"
            return False, e.code, f"HTTP {e.code}"
        except URLError as e:
            if method == "HEAD":
                continue
            reason_str = str(e.reason)
            if "CERTIFICATE_VERIFY_FAILED" in reason_str:
                return True, 0, "SSL-Chain-Warning (Host Reachable)"
            return False, 0, f"URLError ({e.reason})"
        except Exception as e:
            if method == "HEAD":
                continue
            return False, 0, f"Error ({e})"
    return False, 0, "Unreachable"


def audit_json_dataset(path: Path, args, blocking: list, warnings: list):
    """Audit structured JSON research dataset for quota parity, required keys, and year bounds."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        blocking.append(f"[{path.name}] Invalid JSON syntax: {e}")
        return

    records = None
    if isinstance(data, list):
        records = data
    elif isinstance(data, dict):
        meta = data.get("metadata", {})
        for candidate_key in ("case_studies", "records", "items", "data", "results", "entries"):
            if isinstance(data.get(candidate_key), list):
                records = data[candidate_key]
                break
        if records is None:
            for val in data.values():
                if isinstance(val, list) and val and isinstance(val[0], dict):
                    records = val
                    break
        if records is not None and isinstance(meta, dict) and "total_records" in meta:
            declared = meta["total_records"]
            if declared != len(records):
                blocking.append(
                    f"[{path.name}] Metadata total_records ({declared}) != actual count ({len(records)})"
                )

    if records is None:
        return

    if args.expected_count is not None and len(records) != args.expected_count:
        blocking.append(
            f"[{path.name}] Record count ({len(records)}) does not match --expected-count ({args.expected_count})"
        )

    req_fields = [f.strip() for f in args.required_fields.split(",") if f.strip()] if args.required_fields else []
    year_min, year_max = None, None
    if args.year_range:
        if ":" not in args.year_range:
            err_msg = (
                f"[CLI Flag Error] Invalid --year-range '{args.year_range}': "
                "expected 'MIN:MAX' format (e.g. '2020:2026')."
            )
            if err_msg not in blocking:
                blocking.append(err_msg)
        else:
            parts = args.year_range.split(":", 1)
            try:
                year_min, year_max = int(parts[0].strip()), int(parts[1].strip())
                if year_min > year_max:
                    raise ValueError("min > max")
            except ValueError:
                err_msg = (
                    f"[CLI Flag Error] Invalid --year-range '{args.year_range}': "
                    "expected 'MIN:MAX' format (e.g. '2020:2026')."
                )
                if err_msg not in blocking:
                    blocking.append(err_msg)
                year_min, year_max = None, None

    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            continue
        label = rec.get("project_name") or rec.get("name") or rec.get("title") or rec.get("id") or f"Record #{idx}"
        for rf in req_fields:
            if rf not in rec or rec[rf] in (None, "", []):
                blocking.append(f"[{path.name} -> {label}] Missing or empty required field: `{rf}`")

        if year_min is not None and args.year_field in rec:
            yr = rec.get(args.year_field)
            yr_int = None
            if isinstance(yr, int) and not isinstance(yr, bool):
                yr_int = yr
            elif isinstance(yr, str) and yr.strip().isdigit():
                yr_int = int(yr.strip())
            if yr_int is None or yr_int < year_min or yr_int > year_max:
                blocking.append(
                    f"[{path.name} -> {label}] `{args.year_field}`={yr} outside required range [{year_min}..{year_max}]"
                )


def main():
    parser = argparse.ArgumentParser(description="XDeep-Research Evidence & Schema Verifier (/xdeep-research)")
    parser.add_argument("target", help="Path to Markdown (.md) or JSON (.json) research deliverable")
    parser.add_argument("--check-http", action="store_true", help="Probe extracted URLs for HTTP 200 reachability")
    parser.add_argument("--allow-root-urls", action="store_true", help="Allow bare root-domain homepage URLs")
    parser.add_argument("--expected-count", type=int, default=None, help="Expected number of records in JSON array")
    parser.add_argument("--required-fields", type=str, default="", help="Comma-separated required JSON keys per record")
    parser.add_argument("--year-field", type=str, default="year_built", help="JSON key for year range validation")
    parser.add_argument(
        "--year-range", type=str, default="", help="Allowed year range formatted as MIN:MAX (e.g. 2020:2026)"
    )
    args = parser.parse_args()

    target_path = Path(args.target).resolve()
    if not target_path.exists():
        print(f"ERROR: Target file not found: {target_path}", file=sys.stderr)
        sys.exit(1)

    text = target_path.read_text(encoding="utf-8", errors="replace")
    blocking = []
    warnings = []

    if args.year_range:
        parts = args.year_range.split(":", 1) if ":" in args.year_range else []
        valid_yr = False
        if len(parts) == 2:
            try:
                y0, y1 = int(parts[0].strip()), int(parts[1].strip())
                valid_yr = y0 <= y1
            except ValueError:
                valid_yr = False
        if not valid_yr:
            blocking.append(
                f"[CLI Flag Error] Invalid --year-range '{args.year_range}': "
                "expected 'MIN:MAX' format (e.g. '2020:2026')."
            )

    # 1. Placeholder Scan (strip fenced code blocks and inline code spans in Markdown first)
    if target_path.suffix.lower() == ".md":
        scan_text = re.sub(r"(`{3,}|~{3,})[\s\S]*?\1", "", text)
        scan_text = re.sub(r"``[^\n]+?``", "", scan_text)
        scan_text = re.sub(r"`[^`\n]+`", "", scan_text)
    else:
        scan_text = text
    for label, pat in PLACEHOLDER_PATTERNS:
        for m in pat.finditer(scan_text):
            blocking.append(f"[{target_path.name}] {label} detected: `{m.group(0)}`")

    # 2. Extract URLs & Check Deep-Link Requirement
    urls = extract_urls(scan_text)
    if not urls:
        warnings.append(f"[{target_path.name}] Zero external http/https URLs found in document.")
    else:
        has_deep_links = any(not is_root_domain_url(u) for u in urls)
        for u in urls:
            if not args.allow_root_urls and is_root_domain_url(u):
                msg = f"[{target_path.name}] Root-domain homepage URL detected (prefer specific deep link): `{u}`"
                if target_path.suffix.lower() == ".md" and has_deep_links:
                    warnings.append(msg)
                else:
                    blocking.append(msg)

    # 3. JSON Dataset Schema & Quota Audit
    if target_path.suffix.lower() == ".json":
        audit_json_dataset(target_path, args, blocking, warnings)

    # 4. Optional Live HTTP Probe
    if args.check_http and urls:
        with ThreadPoolExecutor(max_workers=8) as pool:
            future_map = {pool.submit(check_url_http, u): u for u in urls}
            for fut in as_completed(future_map):
                u = future_map[fut]
                ok, code, msg = fut.result()
                if not ok:
                    blocking.append(f"[{target_path.name}] Broken or unreachable URL ({msg}): `{u}`")

    print("=" * 70)
    print("XDEEP-RESEARCH EVIDENCE AUDIT SCORECARD")
    print("=" * 70)
    print(f"Target:    {target_path}")
    print(f"URLs:      {len(urls)}")
    print(f"Blocking:  {len(blocking)}")
    print(f"Advisory:  {len(warnings)}")
    print("-" * 70)

    if blocking:
        print("\nBLOCKING EVIDENCE FAILURES:")
        for b in blocking:
            print(f"  - {b}")
    if warnings:
        print("\nADVISORY NOTICES:")
        for w in warnings:
            print(f"  - {w}")

    if blocking:
        print("\nVERDICT: FAIL (Prune or re-verify flagged evidence before completion)")
        sys.exit(1)
    else:
        print("\n✅ VERDICT: PASS (100% Evidence & Schema Gates Verified)")
        sys.exit(0)


if __name__ == "__main__":
    main()
