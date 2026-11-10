#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Context Compaction & Token Telemetry Diagnostic Helper (check_context.py)
Analyzes active AI agent conversation transcripts (JSONL) and SQLite step databases
to determine the current compaction round, active window pressure, step metrics,
memory drift risk, and cross-agent token consumption (--tokens, --days N, --all-time).

Part of the /xcontext skill. Cross-platform (Windows, macOS, Linux).
Zero external dependencies (Python stdlib only).
"""

import sys
sys.dont_write_bytecode = True

import argparse  # noqa: E402
import collections  # noqa: E402
import datetime  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import sqlite3  # noqa: E402
import time  # noqa: E402

# XBoost UTF-8 stream guards
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

ESTIMATED_STEPS_PER_COMPACTION = 170


def get_platform_roots():
    """Resolve all installed Antigravity platform roots across Windows, macOS, and Linux."""
    candidates = [
        ("Antigravity 2.0", os.path.expanduser("~/.gemini/antigravity")),
        ("Antigravity IDE", os.path.expanduser("~/.gemini/antigravity-ide")),
        ("Antigravity CLI", os.path.expanduser("~/.gemini/antigravity-cli")),
        ("Antigravity macOS", os.path.expanduser("~/Library/Application Support/antigravity")),
        ("Antigravity IDE macOS", os.path.expanduser("~/Library/Application Support/antigravity-ide")),
    ]
    roots = []
    seen = set()
    for label, path in candidates:
        if os.path.isdir(path):
            real_p = os.path.realpath(path)
            if real_p not in seen:
                seen.add(real_p)
                roots.append((label, path))
    return roots


def get_brain_dirs():
    """Resolve the platform-appropriate brain directories for Antigravity installations."""
    dirs = []
    for _, root in get_platform_roots():
        bdir = os.path.join(root, "brain")
        if os.path.isdir(bdir):
            dirs.append(bdir)
    return dirs


# ---------------------------------------------------------------------------
# Pure-Stdlib Protobuf Wire Decoder for Antigravity SQLite step metadata
# ---------------------------------------------------------------------------
def _read_varint(buf, pos):
    val = 0
    shift = 0
    size = len(buf)
    while pos < size:
        b = buf[pos]
        pos += 1
        val |= (b & 0x7F) << shift
        if not (b & 0x80):
            return val, pos
        shift += 7
    return val, pos


def _parse_proto(buf):
    pos = 0
    out = {}
    size = len(buf)
    while pos < size:
        tag, pos = _read_varint(buf, pos)
        field_num = tag >> 3
        wire_type = tag & 0x07
        if wire_type == 0:
            val, pos = _read_varint(buf, pos)
            out.setdefault(field_num, []).append(val)
        elif wire_type == 2:
            length, pos = _read_varint(buf, pos)
            sub = buf[pos: pos + length]
            pos += length
            out.setdefault(field_num, []).append(sub)
        elif wire_type == 1:
            pos += 8
        elif wire_type == 5:
            pos += 4
        else:
            break
    return out


def extract_db_step_telemetry(db_path):
    """Extract token telemetry and timestamps from a SQLite conversations/<id>.db file."""
    stats = {
        "steps": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "thinking_tokens": 0,
        "response_tokens": 0,
        "first_ts": 0,
        "last_ts": 0,
        "models": collections.Counter(),
    }
    if not os.path.isfile(db_path):
        return stats

    try:
        conn = sqlite3.connect(db_path, timeout=1.5)
        cur = conn.cursor()
        cur.execute("SELECT metadata FROM steps WHERE metadata IS NOT NULL")
        for (meta,) in cur.fetchall():
            stats["steps"] += 1
            if not isinstance(meta, (bytes, bytearray)):
                continue
            top = _parse_proto(meta)
            if 1 in top and isinstance(top[1][0], (bytes, bytearray)):
                ts_msg = _parse_proto(top[1][0])
                sec = ts_msg.get(1, [0])[0]
                if sec > 1500000000:
                    if stats["first_ts"] == 0 or sec < stats["first_ts"]:
                        stats["first_ts"] = sec
                    if sec > stats["last_ts"]:
                        stats["last_ts"] = sec
            if 9 in top and isinstance(top[9][0], (bytes, bytearray)):
                tok_msg = _parse_proto(top[9][0])
                in_tok = tok_msg.get(2, [0])[0]
                out_tok = tok_msg.get(3, [0])[0]
                cache_tok = tok_msg.get(5, [0])[0]
                think_tok = tok_msg.get(9, [0])[0]
                resp_tok = tok_msg.get(10, [0])[0]
                model_bytes = tok_msg.get(1, [b""])[0]
                model_str = (
                    model_bytes.decode("utf-8", errors="ignore")
                    if isinstance(model_bytes, (bytes, bytearray))
                    else "unknown"
                )
                stats["input_tokens"] += in_tok
                stats["output_tokens"] += out_tok
                stats["cache_read_tokens"] += cache_tok
                stats["thinking_tokens"] += think_tok
                stats["response_tokens"] += resp_tok
                if model_str:
                    stats["models"][model_str] += in_tok + out_tok
        conn.close()
    except Exception:
        return stats
    return stats


def is_user_conversation(transcript_path):
    """Return True if transcript belongs to a main user chat rather than an isolated subagent."""
    try:
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            first_line = f.readline()
            if not first_line:
                return False
            first_obj = json.loads(first_line)
            return (
                first_obj.get("source") == "USER_EXPLICIT"
                or first_obj.get("type") == "USER_INPUT"
            )
    except Exception:
        return False


def find_active_conversation_dir(conv_id=None):
    """Find conversation directory by ID or by latest main user conversation modification time."""
    brain_dirs = get_brain_dirs()
    if not brain_dirs:
        return None

    if conv_id:
        for bdir in brain_dirs:
            target = os.path.join(bdir, conv_id)
            if os.path.isdir(target):
                return target
            for d in os.listdir(bdir):
                if d.startswith(conv_id):
                    candidate = os.path.join(bdir, d)
                    if os.path.isdir(candidate):
                        return candidate

    user_entries = []
    all_entries = []
    for bdir in brain_dirs:
        for d in os.listdir(bdir):
            full_p = os.path.join(bdir, d)
            transcript_p = os.path.join(full_p, ".system_generated", "logs", "transcript.jsonl")
            if not os.path.isfile(transcript_p):
                transcript_p = os.path.join(full_p, ".system_generated", "logs", "transcript_full.jsonl")
            if os.path.isdir(full_p) and not d.startswith(".") and os.path.isfile(transcript_p):
                mtime = os.path.getmtime(transcript_p)
                all_entries.append((mtime, full_p))
                if is_user_conversation(transcript_p):
                    user_entries.append((mtime, full_p))

    if user_entries:
        return max(user_entries, key=lambda x: x[0])[1]
    if all_entries:
        return max(all_entries, key=lambda x: x[0])[1]
    return None


def analyze_transcript(conv_dir_or_file):
    """Parse transcript.jsonl (or any agent JSONL session log + companion SQLite .db) for context & token metrics."""
    if os.path.isfile(conv_dir_or_file):
        transcript_path = conv_dir_or_file
        conv_dir = os.path.dirname(os.path.abspath(conv_dir_or_file))
        if (
            os.path.basename(conv_dir) == "logs"
            and os.path.basename(os.path.dirname(conv_dir)) == ".system_generated"
        ):
            conv_dir = os.path.dirname(os.path.dirname(conv_dir))
    else:
        conv_dir = os.path.abspath(conv_dir_or_file)
        if (
            os.path.basename(conv_dir) == "logs"
            and os.path.basename(os.path.dirname(conv_dir)) == ".system_generated"
        ):
            conv_dir = os.path.dirname(os.path.dirname(conv_dir))
        elif os.path.basename(conv_dir) == ".system_generated":
            conv_dir = os.path.dirname(conv_dir)
        transcript_path = os.path.join(conv_dir, ".system_generated", "logs", "transcript.jsonl")
        if not os.path.isfile(transcript_path):
            full_candidate = os.path.join(conv_dir, ".system_generated", "logs", "transcript_full.jsonl")
            if os.path.isfile(full_candidate):
                transcript_path = full_candidate
    if not os.path.isfile(transcript_path):
        return None

    total_steps = 0
    user_inputs = 0
    subagents_spawned = 0
    compaction_checkpoints = []
    input_tokens = 0
    output_tokens = 0
    cache_read_tokens = 0
    thinking_tokens = 0

    with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
        for step_num, line in enumerate(f, 1):
            total_steps = step_num
            try:
                data = json.loads(line)
            except Exception as exc:
                _ = exc
                continue

            msg_type = data.get("type", "")
            source = data.get("source", "")
            content = str(data.get("content", ""))

            input_tokens += int(data.get("input_tokens", 0) or 0)
            output_tokens += int(data.get("output_tokens", 0) or 0)
            cache_read_tokens += int(data.get("cache_read_tokens", 0) or 0)

            if msg_type == "USER_INPUT" and source == "USER_EXPLICIT":
                user_inputs += 1
            elif msg_type == "user" and not data.get("isSidechain"):
                user_inputs += 1

            is_checkpoint = msg_type in ("CHECKPOINT", "summary", "compaction") or (
                source == "SYSTEM"
                and msg_type != "SYSTEM_MESSAGE"
                and content.lstrip().startswith("# Resuming from a compaction")
            )
            if is_checkpoint:
                compaction_checkpoints.append(step_num)

            if msg_type == "PLANNER_RESPONSE":
                for tc in data.get("tool_calls", []) or []:
                    if isinstance(tc, dict) and tc.get("name") in ("invoke_subagent", "Task"):
                        subagents_spawned += 1

    # Fallback to companion SQLite conversations/<id>.db if transcript omits token fields (Antigravity IDE)
    conv_id = os.path.basename(conv_dir)
    platform_root = os.path.dirname(os.path.dirname(conv_dir))
    db_path = os.path.join(platform_root, "conversations", f"{conv_id}.db")
    if os.path.isfile(db_path):
        db_stats = extract_db_step_telemetry(db_path)
        if db_stats["input_tokens"] > input_tokens:
            input_tokens = db_stats["input_tokens"]
            output_tokens = db_stats["output_tokens"]
            cache_read_tokens = db_stats["cache_read_tokens"]
            thinking_tokens = db_stats["thinking_tokens"]

    total_prompt = input_tokens + cache_read_tokens
    cache_hit_pct = (
        round((cache_read_tokens / float(total_prompt)) * 100, 1) if total_prompt > 0 else 0.0
    )

    compaction_round = len(compaction_checkpoints)
    last_compaction_step = compaction_checkpoints[-1] if compaction_checkpoints else 0
    steps_since_compaction = (
        (total_steps - last_compaction_step) if compaction_checkpoints else total_steps
    )
    window_fill_pct = min(
        100, int(round((steps_since_compaction / float(ESTIMATED_STEPS_PER_COMPACTION)) * 100))
    )

    # 4-Tier Health Rubric (combining Cumulative Compaction Round + Active Window Pressure)
    if (
        compaction_round >= 3
        or (compaction_round == 2 and steps_since_compaction >= 120)
        or total_steps >= 450
    ):
        health = "CRITICAL"
        level_icon = "🔴"
        risk_desc = (
            f"Heavy cumulative compaction (Round {compaction_round}, {total_steps} total steps). "
            "High risk of early constraint drift and session timeouts."
        )
        recommendation = (
            "Strongly recommend starting a fresh conversation now. "
            "Run `/xkickoff` to verify doc sync and generate the prompt for the next session."
        )
        action = "START_NEW_CHAT"
    elif (
        compaction_round == 2
        or (compaction_round == 1 and steps_since_compaction >= 130)
        or total_steps >= 250
    ):
        health = "CAUTION"
        level_icon = "🟠"
        risk_desc = (
            f"Moderate memory pruning active (Round {compaction_round}, "
            f"{steps_since_compaction} steps since last compaction / ~{window_fill_pct}% active window load)."
        )
        recommendation = (
            "Safe to finish the current task, then wrap up the milestone and run `/xkickoff` "
            "before starting a new major phase."
        )
        action = "PREPARE_TRANSITION"
    elif compaction_round == 1 or steps_since_compaction >= 100 or total_steps >= 120:
        health = "NOMINAL"
        level_icon = "🟡"
        risk_desc = (
            f"Good context retention (Round {compaction_round}, "
            f"{steps_since_compaction} steps in active window / ~{window_fill_pct}% load)."
        )
        recommendation = "Safe for continued execution. Keep edits focused."
        action = "CONTINUE"
    else:
        health = "HEALTHY"
        level_icon = "🟢"
        risk_desc = (
            f"Optimal context capacity (Round 0, {steps_since_compaction} steps / "
            f"~{window_fill_pct}% active window load)."
        )
        recommendation = "Safe to continue in the current conversation."
        action = "CONTINUE"

    return {
        "conv_id": conv_id,
        "compaction_round": compaction_round,
        "checkpoint_steps": compaction_checkpoints,
        "total_steps": total_steps,
        "user_inputs": user_inputs,
        "subagents_spawned": subagents_spawned,
        "steps_since_compaction": steps_since_compaction,
        "window_fill_pct": window_fill_pct,
        "input_tokens": input_tokens,
        "cache_read_tokens": cache_read_tokens,
        "output_tokens": output_tokens,
        "thinking_tokens": thinking_tokens,
        "cache_hit_pct": cache_hit_pct,
        "health": health,
        "level_icon": level_icon,
        "risk_desc": risk_desc,
        "recommendation": recommendation,
        "action": action,
    }


def _scan_transcript_tokens(transcript_path, cutoff_ts=0):
    """Scan a transcript.jsonl file for token counts and timestamps."""
    stats = {
        "steps": 0,
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "thinking_tokens": 0,
        "subagents": 0,
        "last_ts": 0,
    }
    try:
        mtime = os.path.getmtime(transcript_path)
        if cutoff_ts > 0 and mtime < cutoff_ts:
            return stats
        stats["last_ts"] = int(mtime)
        with open(transcript_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                stats["steps"] += 1
                try:
                    obj = json.loads(line)
                except Exception as exc:
                    _ = exc
                    continue
                stats["input_tokens"] += int(obj.get("input_tokens", 0) or 0)
                stats["output_tokens"] += int(obj.get("output_tokens", 0) or 0)
                stats["cache_read_tokens"] += int(obj.get("cache_read_tokens", 0) or 0)
                if obj.get("type") == "PLANNER_RESPONSE":
                    for tc in obj.get("tool_calls", []) or []:
                        if isinstance(tc, dict) and tc.get("name") in ("invoke_subagent", "Task"):
                            stats["subagents"] += 1
    except Exception:
        return stats
    return stats


def aggregate_cross_platform_telemetry(days=None, all_time=False):
    """Aggregate token telemetry across all installed Antigravity platforms."""
    cutoff_ts = 0
    if days is not None and not all_time:
        cutoff_ts = time.time() - (float(days) * 86400.0)

    platforms_out = []
    global_models = collections.Counter()
    monthly_buckets = collections.defaultdict(
        lambda: {"convs": 0, "steps": 0, "in": 0, "cache": 0, "out": 0}
    )

    for label, root in get_platform_roots():
        conv_map = {}

        # 1. Scan SQLite conversations/*.db (primary store for Antigravity IDE & CLI)
        conv_db_dir = os.path.join(root, "conversations")
        if os.path.isdir(conv_db_dir):
            for fname in os.listdir(conv_db_dir):
                if not fname.endswith(".db"):
                    continue
                cid = fname[:-3]
                db_p = os.path.join(conv_db_dir, fname)
                try:
                    mtime = os.path.getmtime(db_p)
                except Exception as exc:
                    _ = exc
                    continue
                if cutoff_ts > 0 and mtime < cutoff_ts:
                    continue
                db_st = extract_db_step_telemetry(db_p)
                ts_ref = db_st["last_ts"] or int(mtime)
                conv_map[cid] = {
                    "steps": db_st["steps"],
                    "in": db_st["input_tokens"],
                    "cache": db_st["cache_read_tokens"],
                    "out": db_st["output_tokens"],
                    "think": db_st["thinking_tokens"],
                    "subagents": 0,
                    "ts": ts_ref,
                }
                for m_id, tok_sum in db_st["models"].items():
                    global_models[m_id] += tok_sum

        # 2. Scan brain/*/.system_generated/logs/transcript.jsonl (primary store for Antigravity 2.0 + subagents)
        brain_dir = os.path.join(root, "brain")
        if os.path.isdir(brain_dir):
            for cid in os.listdir(brain_dir):
                if cid.startswith("."):
                    continue
                tp = os.path.join(brain_dir, cid, ".system_generated", "logs", "transcript.jsonl")
                if not os.path.isfile(tp):
                    tp = os.path.join(brain_dir, cid, ".system_generated", "logs", "transcript_full.jsonl")
                if not os.path.isfile(tp):
                    continue
                tr_st = _scan_transcript_tokens(tp, cutoff_ts=cutoff_ts)
                if tr_st["steps"] == 0:
                    continue
                if cid in conv_map:
                    conv_map[cid]["subagents"] = max(conv_map[cid]["subagents"], tr_st["subagents"])
                    if tr_st["input_tokens"] > conv_map[cid]["in"]:
                        conv_map[cid]["in"] = tr_st["input_tokens"]
                        conv_map[cid]["cache"] = tr_st["cache_read_tokens"]
                        conv_map[cid]["out"] = tr_st["output_tokens"]
                        conv_map[cid]["steps"] = max(conv_map[cid]["steps"], tr_st["steps"])
                else:
                    conv_map[cid] = {
                        "steps": tr_st["steps"],
                        "in": tr_st["input_tokens"],
                        "cache": tr_st["cache_read_tokens"],
                        "out": tr_st["output_tokens"],
                        "think": 0,
                        "subagents": tr_st["subagents"],
                        "ts": tr_st["last_ts"],
                    }

        p_convs = len(conv_map)
        p_steps = sum(v["steps"] for v in conv_map.values())
        p_in = sum(v["in"] for v in conv_map.values())
        p_cache = sum(v["cache"] for v in conv_map.values())
        p_out = sum(v["out"] for v in conv_map.values())
        p_think = sum(v["think"] for v in conv_map.values())
        p_sub = sum(v["subagents"] for v in conv_map.values())

        for v in conv_map.values():
            if v["ts"] > 0:
                ym = datetime.datetime.fromtimestamp(v["ts"]).strftime("%Y-%m")
                monthly_buckets[ym]["convs"] += 1
                monthly_buckets[ym]["steps"] += v["steps"]
                monthly_buckets[ym]["in"] += v["in"]
                monthly_buckets[ym]["cache"] += v["cache"]
                monthly_buckets[ym]["out"] += v["out"]

        platforms_out.append({
            "platform": label,
            "conversations": p_convs,
            "steps": p_steps,
            "input_tokens": p_in,
            "cache_read_tokens": p_cache,
            "output_tokens": p_out,
            "thinking_tokens": p_think,
            "subagents_spawned": p_sub,
        })

    return {
        "window": "All-Time" if all_time else f"Last {days} Days",
        "platforms": platforms_out,
        "monthly": dict(sorted(monthly_buckets.items())),
        "models": dict(global_models.most_common(10)),
    }


def _fmt_tok(val):
    if val >= 1_000_000_000:
        return f"{val / 1_000_000_000:.2f}B"
    if val >= 1_000_000:
        return f"{val / 1_000_000:.2f}M"
    if val >= 1_000:
        return f"{val / 1_000:.1f}K"
    return str(val)


def print_telemetry_report(report):
    """Render Markdown tables for cross-platform token telemetry."""
    print(f"\n### Cross-Platform Token Telemetry ({report['window']})\n")
    print("| Platform | Convs | Steps | Input Tokens | Cache Read | Output Tokens | Subagents |")
    print("|:---|---:|---:|---:|---:|---:|---:|")
    tot_c = tot_s = tot_in = tot_ca = tot_out = tot_sub = 0
    for p in report["platforms"]:
        tot_c += p["conversations"]
        tot_s += p["steps"]
        tot_in += p["input_tokens"]
        tot_ca += p["cache_read_tokens"]
        tot_out += p["output_tokens"]
        tot_sub += p["subagents_spawned"]
        print(
            f"| **{p['platform']}** | {p['conversations']:,} | {p['steps']:,} | "
            f"`{_fmt_tok(p['input_tokens'])}` | `{_fmt_tok(p['cache_read_tokens'])}` | "
            f"`{_fmt_tok(p['output_tokens'])}` | {p['subagents_spawned']:,} |"
        )
    tot_prompt = tot_in + tot_ca
    hit_pct = round((tot_ca / float(tot_prompt)) * 100, 1) if tot_prompt > 0 else 0.0
    print(
        f"| **TOTAL** | **{tot_c:,}** | **{tot_s:,}** | **`{_fmt_tok(tot_in)}`** | "
        f"**`{_fmt_tok(tot_ca)}` ({hit_pct}%)** | **`{_fmt_tok(tot_out)}`** | **{tot_sub:,}** |\n"
    )

    if report["monthly"]:
        print("#### Monthly Breakdown\n")
        print("| Month | Convs | Steps | Input Tokens | Cache Read | Output Tokens |")
        print("|:---|---:|---:|---:|---:|---:|")
        for ym, mb in report["monthly"].items():
            print(
                f"| `{ym}` | {mb['convs']:,} | {mb['steps']:,} | `{_fmt_tok(mb['in'])}` | "
                f"`{_fmt_tok(mb['cache'])}` | `{_fmt_tok(mb['out'])}` |"
            )
        print()


def main():
    parser = argparse.ArgumentParser(
        description="Analyze agent context compaction & cross-session token telemetry"
    )
    parser.add_argument(
        "--conv-id", type=str, default=None, help="Target conversation ID (full UUID or prefix)"
    )
    parser.add_argument(
        "--transcript", type=str, default=None, help="Explicit path to any agent JSONL transcript file"
    )
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of markdown")
    parser.add_argument(
        "--tokens", action="store_true", help="Include cross-platform token telemetry summary"
    )
    parser.add_argument(
        "--days", type=int, default=None, help="Aggregate cross-platform token telemetry over last N days"
    )
    parser.add_argument(
        "--all-time", action="store_true", help="Aggregate all-time cross-platform token telemetry"
    )
    args = parser.parse_args()

    conv_dir = args.transcript if args.transcript else find_active_conversation_dir(args.conv_id)
    if not conv_dir:
        print("Error: Could not locate active conversation directory or transcript.", file=sys.stderr)
        sys.exit(1)

    metrics = analyze_transcript(conv_dir)
    if not metrics:
        print(f"Error: Could not read transcript logs in {conv_dir}", file=sys.stderr)
        sys.exit(1)

    telemetry = None
    if args.tokens or args.days is not None or args.all_time:
        telemetry = aggregate_cross_platform_telemetry(
            days=args.days if args.days is not None else 30,
            all_time=args.all_time,
        )
        metrics["cross_platform_telemetry"] = telemetry

    if args.json:
        print(json.dumps(metrics, indent=2))
        return

    ckpt_list = (
        ", ".join(f"step {s}" for s in metrics["checkpoint_steps"])
        if metrics["checkpoint_steps"]
        else "none"
    )
    round_str = f"Round {metrics['compaction_round']} ({ckpt_list})"
    status_str = f"{metrics['level_icon']} {metrics['health']}"
    window_str = (
        f"{metrics['steps_since_compaction']} steps "
        f"(~{metrics['window_fill_pct']}% of ~{ESTIMATED_STEPS_PER_COMPACTION}-step window)"
    )
    tok_str = (
        f"`{_fmt_tok(metrics['input_tokens'])}` in • "
        f"`{_fmt_tok(metrics['cache_read_tokens'])}` cache ({metrics['cache_hit_pct']}%) • "
        f"`{_fmt_tok(metrics['output_tokens'])}` out"
    )

    print("\n### Context & Compaction Scorecard\n")
    print("| Metric | Value | Status |")
    print("|:---|:---|:---:|")
    print(f"| **Compaction Round** | {round_str} | {status_str} |")
    print(f"| **Steps Since Last Compaction** | {window_str} | — |")
    print(f"| **Total Session Steps** | {metrics['total_steps']} steps | — |")
    sub_str = f"{metrics['user_inputs']} prompts • {metrics['subagents_spawned']} subagents"
    print(f"| **User Prompts / Subagents** | {sub_str} | — |")
    print(f"| **Session Tokens (In / Cache / Out)** | {tok_str} | — |")
    print(f"| **Conversation ID** | `{metrics['conv_id'][:8]}...` | — |\n")
    print(f"**Diagnostic Assessment**: {metrics['risk_desc']}\n")
    print(f"**Recommendation**: {metrics['recommendation']}\n")

    if telemetry:
        print_telemetry_report(telemetry)

    if metrics["action"] in ("PREPARE_TRANSITION", "START_NEW_CHAT"):
        print(
            "👉 **Next Step**: Run `/xkickoff` to verify document synchronization, "
            "review next-phase options, and generate a pristine prompt for your fresh conversation.\n"
        )


if __name__ == "__main__":
    main()
