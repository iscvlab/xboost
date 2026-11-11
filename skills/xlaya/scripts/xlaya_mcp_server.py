# -*- coding: utf-8 -*-
"""
Zero-Extra-Dependency Model Context Protocol (MCP) JSON-RPC 2.0 `stdio` Server (`xlaya-mcp`).

Exposes warm in-RAM/VRAM Laya (`choice`, `score`, `noul`) and VegaML System 1.5 inference tools
with strict MCP Wire Purity (`sys.stdout` redirected to `sys.stderr`, JSON-RPC frames written
exclusively to `_JSONRPC_OUT`) and thread-safe idle VRAM auto-unload lifecycle management.
"""

import contextlib
import json
import os
import sys
import threading
from typing import Any, Dict, List, Optional

__version__ = "2.0.0"

sys.dont_write_bytecode = True

# Enforce HuggingFace / Transformers Wire Purity before any backend import.
os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")
if os.name == "nt":
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS", "1")
    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

_SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

_JSONRPC_OUT = sys.stdout
_SERVER_LOCK = threading.RLock()
_IDLE_TIMER: Optional[threading.Timer] = None
_DEFAULT_IDLE_TTL_SEC = 1800
_DEFAULT_PATTERN = "*.md,*.html,*.txt,*.json,*.jsonl,*.csv"


def _get_backend() -> Any:
    """Lazily import `laya_triage` from the co-located `scripts/` directory."""
    if _SCRIPTS_DIR not in sys.path:
        sys.path.insert(0, _SCRIPTS_DIR)
    import laya_triage

    return laya_triage


def _get_idle_ttl_sec() -> int:
    """Return idle VRAM auto-unload TTL in seconds (`0` disables auto-unload)."""
    raw = os.environ.get("LAYA_IDLE_TTL_SEC", str(_DEFAULT_IDLE_TTL_SEC)).strip()
    try:
        parsed = int(float(raw))
    except ValueError:
        return _DEFAULT_IDLE_TTL_SEC
    return max(0, parsed)


def _cancel_idle_timer() -> None:
    """Cancel any pending idle VRAM auto-unload timer under `_SERVER_LOCK`."""
    global _IDLE_TIMER
    with _SERVER_LOCK:
        if _IDLE_TIMER is not None:
            _IDLE_TIMER.cancel()
            _IDLE_TIMER = None


def _on_idle_timeout() -> None:
    """Daemon timer callback: unload warm Laya/VegaML models after idle TTL expires."""
    global _IDLE_TIMER
    with _SERVER_LOCK:
        _IDLE_TIMER = None
        backend = sys.modules.get("laya_triage")
        if backend is None or not hasattr(backend, "unload_models"):
            return
        try:
            with contextlib.redirect_stdout(sys.stderr):
                backend.unload_models()
        except Exception as exc:
            sys.stderr.write(f"[xlaya-mcp] idle auto-unload warning: {exc}\n")
            sys.stderr.flush()


def _reset_idle_timer() -> None:
    """Arm or replace the replaceable daemon idle VRAM auto-unload timer if enabled."""
    global _IDLE_TIMER
    with _SERVER_LOCK:
        if _IDLE_TIMER is not None:
            _IDLE_TIMER.cancel()
            _IDLE_TIMER = None
        ttl_sec = _get_idle_ttl_sec()
        if ttl_sec > 0:
            timer = threading.Timer(float(ttl_sec), _on_idle_timeout)
            timer.daemon = True
            timer.name = "xlaya-idle-unload-watchdog"
            _IDLE_TIMER = timer
            timer.start()


def _arg_str(args: Dict[str, Any], key: str, default: str = "") -> str:
    val = args.get(key)
    return default if val is None else str(val)


def _arg_int(args: Dict[str, Any], key: str, default: int = 0) -> int:
    val = args.get(key)
    return default if val is None else int(val)


def _arg_float(args: Dict[str, Any], key: str, default: float = 0.0) -> float:
    val = args.get(key)
    return default if val is None else float(val)


def _arg_bool(args: Dict[str, Any], key: str, default: bool = False) -> bool:
    val = args.get(key)
    if val is None:
        return default
    if isinstance(val, str):
        return val.strip().lower() in ("1", "true", "yes", "on")
    return bool(val)


def _normalize_dict_payload(res: Any) -> Dict[str, Any]:
    if isinstance(res, dict):
        return dict(res)
    return {"ok": True, "result": res}


MCP_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "xlaya_status",
        "description": (
            "Inspect XLaya System 1 runtime health, warm-loaded models (`en`, `multi`, `vegaml`), "
            "CUDA/VRAM availability, MCP server version, and idle auto-unload TTL."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "xlaya_triage",
        "description": (
            "Run high-throughput System 1 document/section triage (`shortlist`, `contradiction`, "
            "`rubric`, `classify`) across files or directories with optional VegaML escalation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "File or directory paths to scan and triage.",
                },
                "mode": {
                    "type": "string",
                    "enum": ["shortlist", "contradiction", "rubric", "classify"],
                    "default": "rubric",
                    "description": "Triage mode (`shortlist`, `contradiction`, `rubric`, `classify`).",
                },
                "query": {
                    "type": "string",
                    "default": "",
                    "description": "Target query or rubric prompt (`shortlist` / `rubric` modes).",
                },
                "ssot": {
                    "type": "string",
                    "default": "",
                    "description": "Canonical Single Source of Truth claim (`contradiction` mode).",
                },
                "true_desc": {
                    "type": "string",
                    "default": "",
                    "description": "Positive criterion description (`rubric` `noul` evaluation).",
                },
                "false_desc": {
                    "type": "string",
                    "default": "",
                    "description": "Negative criterion description (`rubric` `noul` evaluation).",
                },
                "labels_spec": {
                    "type": "string",
                    "default": "",
                    "description": "Label specification (`label:desc|label2:desc2`) for `classify` mode.",
                },
                "noul_labels": {
                    "type": "string",
                    "default": "",
                    "description": "Optional custom `noul` label pair (`false_label,true_label`).",
                },
                "lang": {
                    "type": "string",
                    "enum": ["auto", "en", "multi"],
                    "default": "auto",
                    "description": "Laya model language selector (`auto`, `en`, `multi`).",
                },
                "device": {
                    "type": "string",
                    "enum": ["auto", "cuda", "mps", "cpu"],
                    "default": "auto",
                    "description": "Compute device (`auto`, `cuda`, `mps`, `cpu`).",
                },
                "max_chars": {
                    "type": "integer",
                    "default": 1600,
                    "description": "Maximum characters per split section chunk.",
                },
                "whole_file": {
                    "type": "boolean",
                    "default": False,
                    "description": "Evaluate each file as a single unit instead of splitting headings.",
                },
                "max_chunks": {
                    "type": "integer",
                    "default": 2048,
                    "description": "Upper cap on total candidate chunks evaluated.",
                },
                "top_k": {
                    "type": "integer",
                    "description": "Maximum top-ranked results to return (defaults to 10, or 0/all in classify).",
                },
                "threshold": {
                    "type": "number",
                    "default": 0.55,
                    "description": "Minimum confidence/score threshold in `[0.0, 1.0]`.",
                },
                "batch_size": {
                    "type": "integer",
                    "default": 32,
                    "description": "Inference batch size.",
                },
                "pattern": {
                    "type": "string",
                    "default": _DEFAULT_PATTERN,
                    "description": "Comma-separated glob patterns when scanning directories.",
                },
                "lexical_prefilter": {
                    "type": "integer",
                    "default": 0,
                    "description": "Optional lexical prefilter cap before neural scoring (`0` disables).",
                },
                "vega": {
                    "type": "boolean",
                    "default": False,
                    "description": "Enable System 1.5 VegaML escalation on top candidates.",
                },
                "vega_model": {
                    "type": "string",
                    "enum": ["0.8b", "4b", "gemma-1b"],
                    "default": "0.8b",
                    "description": "VegaML model tier (`0.8b`, `4b`, `gemma-1b`).",
                },
                "vega_top_k": {
                    "type": "integer",
                    "default": 10,
                    "description": "Number of top Laya candidates to re-score with VegaML.",
                },
            },
            "required": ["paths"],
        },
    },
    {
        "name": "xlaya_predict",
        "description": (
            "Execute raw typed System 1 decisions (`choice`, `score`, `noul`) over a single `state` "
            "or batch `states` using warm Laya and optional VegaML escalation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "questions": {
                    "type": "object",
                    "description": (
                        "Mapping of `question_id -> {type: 'choice'|'score'|'noul', "
                        "instructions: str, criteria: dict|list}`."
                    ),
                },
                "state": {
                    "description": "Single state payload (string, object, or array) to evaluate.",
                },
                "states": {
                    "type": "array",
                    "items": {},
                    "description": "Batch list of state payloads to evaluate.",
                },
                "model": {
                    "type": "string",
                    "enum": ["auto", "en", "multi"],
                    "default": "auto",
                    "description": "Laya model selector (`auto`, `en`, `multi`).",
                },
                "device": {
                    "type": "string",
                    "enum": ["auto", "cuda", "mps", "cpu"],
                    "default": "auto",
                    "description": "Compute device (`auto`, `cuda`, `mps`, `cpu`).",
                },
                "batch_size": {
                    "type": "integer",
                    "default": 32,
                    "description": "Inference batch size.",
                },
                "group_size": {
                    "type": "integer",
                    "default": 16,
                    "description": "Question group size per forward pass.",
                },
                "vega": {
                    "type": "boolean",
                    "default": False,
                    "description": "Route or escalate evaluation through VegaML.",
                },
                "vega_model": {
                    "type": "string",
                    "enum": ["0.8b", "4b", "gemma-1b"],
                    "default": "0.8b",
                    "description": "VegaML model tier (`0.8b`, `4b`, `gemma-1b`).",
                },
            },
            "required": ["questions"],
        },
    },
    {
        "name": "xlaya_preload",
        "description": (
            "Pre-warm Laya (`en`, `multi`) and/or VegaML models in RAM/VRAM so subsequent MCP calls "
            "skip cold-start checkpoint loading."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "models": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["en", "multi"]},
                    "default": ["en"],
                    "description": "Laya models to preload (`['en']`, `['multi']`, or `['en', 'multi']`).",
                },
                "vega": {
                    "type": "boolean",
                    "default": False,
                    "description": "Also preload the VegaML escalation model.",
                },
                "vega_model": {
                    "type": "string",
                    "enum": ["0.8b", "4b", "gemma-1b"],
                    "default": "0.8b",
                    "description": "VegaML model tier (`0.8b`, `4b`, `gemma-1b`).",
                },
                "device": {
                    "type": "string",
                    "enum": ["auto", "cuda", "mps", "cpu"],
                    "default": "auto",
                    "description": "Compute device (`auto`, `cuda`, `mps`, `cpu`).",
                },
            },
        },
    },
    {
        "name": "xlaya_unload",
        "description": (
            "Cancel any pending idle watchdog timer and unload warm Laya/VegaML models from "
            "CPU RAM and CUDA VRAM."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def dispatch_mcp_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Dispatch an MCP tool call by name under `_SERVER_LOCK` and `redirect_stdout(sys.stderr)`
    so backend model logs/bars never leak onto the JSON-RPC `stdio` pipe.
    """
    args = arguments or {}
    with _SERVER_LOCK, contextlib.redirect_stdout(sys.stderr):
        backend = _get_backend()

        if name == "xlaya_status":
            payload = _normalize_dict_payload(backend.get_status())
            payload["mcp_version"] = __version__
            payload["idle_ttl_sec"] = _get_idle_ttl_sec()
            return payload

        if name == "xlaya_triage":
            raw_paths = args.get("paths")
            if isinstance(raw_paths, str):
                paths_list = [raw_paths] if raw_paths.strip() else []
            elif isinstance(raw_paths, (list, tuple)):
                paths_list = [str(p) for p in raw_paths if str(p).strip()]
            else:
                paths_list = []
            if not paths_list:
                raise ValueError("Parameter 'paths' requires at least one file or directory path.")

            _cancel_idle_timer()
            try:
                res = backend.run_triage(
                    paths=paths_list,
                    mode=_arg_str(args, "mode", "rubric"),
                    query=_arg_str(args, "query", ""),
                    ssot=_arg_str(args, "ssot", ""),
                    true_desc=_arg_str(args, "true_desc", ""),
                    false_desc=_arg_str(args, "false_desc", ""),
                    labels_spec=_arg_str(args, "labels_spec", ""),
                    noul_labels=_arg_str(args, "noul_labels", ""),
                    lang=_arg_str(args, "lang", "auto"),
                    device=_arg_str(args, "device", "auto"),
                    max_chars=_arg_int(args, "max_chars", 1600),
                    whole_file=_arg_bool(args, "whole_file", False),
                    max_chunks=_arg_int(args, "max_chunks", 2048),
                    top_k=None if args.get("top_k") is None else _arg_int(args, "top_k", 10),
                    threshold=_arg_float(args, "threshold", 0.55),
                    batch_size=_arg_int(args, "batch_size", 32),
                    pattern=_arg_str(args, "pattern", _DEFAULT_PATTERN),
                    lexical_prefilter=_arg_int(args, "lexical_prefilter", 0),
                    vega=_arg_bool(args, "vega", False),
                    vega_model=_arg_str(args, "vega_model", "0.8b"),
                    vega_top_k=_arg_int(args, "vega_top_k", 10),
                )
                return _normalize_dict_payload(res)
            finally:
                _reset_idle_timer()

        if name == "xlaya_predict":
            raw_questions = args.get("questions")
            if not isinstance(raw_questions, dict) or not raw_questions:
                raise ValueError("Parameter 'questions' must be a non-empty object.")
            raw_states = args.get("states")
            if raw_states is not None and not isinstance(raw_states, list):
                raise ValueError("Parameter 'states' must be an array when provided.")

            _cancel_idle_timer()
            try:
                res = backend.predict_direct(
                    questions=raw_questions,
                    state=args.get("state"),
                    states=raw_states,
                    model=_arg_str(args, "model", "auto"),
                    device=_arg_str(args, "device", "auto"),
                    batch_size=_arg_int(args, "batch_size", 32),
                    group_size=_arg_int(args, "group_size", 16),
                    vega=_arg_bool(args, "vega", False),
                    vega_model=_arg_str(args, "vega_model", "0.8b"),
                )
                return _normalize_dict_payload(res)
            finally:
                _reset_idle_timer()

        if name == "xlaya_preload":
            raw_models = args.get("models")
            if raw_models is None:
                models_list: List[str] = ["en"]
            elif isinstance(raw_models, str):
                cleaned = raw_models.strip()
                if cleaned.lower() == "all":
                    models_list = ["en", "multi"]
                else:
                    models_list = [m.strip() for m in cleaned.split(",") if m.strip()]
            elif isinstance(raw_models, (list, tuple)):
                models_list = [str(m).strip() for m in raw_models if str(m).strip()]
            else:
                raise ValueError("Parameter 'models' must be an array of strings or a string.")

            _cancel_idle_timer()
            try:
                res = backend.preload_models(
                    models=models_list,
                    vega=_arg_bool(args, "vega", False),
                    vega_model=_arg_str(args, "vega_model", "0.8b"),
                    device=_arg_str(args, "device", "auto"),
                )
                return _normalize_dict_payload(res)
            finally:
                _reset_idle_timer()

        if name == "xlaya_unload":
            _cancel_idle_timer()
            res = backend.unload_models()
            return _normalize_dict_payload(res)

    raise ValueError(f"Unknown MCP tool: {name}")


def handle_jsonrpc_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Process a single JSON-RPC 2.0 request and return the response dictionary (or `None`)."""
    method = str(req.get("method", ""))
    req_id = req.get("id")
    params = req.get("params") or {}

    if method == "notifications/initialized" or (method.startswith("notifications/") and req_id is None):
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "xlaya-mcp", "version": __version__},
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": MCP_TOOLS},
        }

    if method == "tools/call":
        tool_name = str(params.get("name", ""))
        tool_args = params.get("arguments") or {}
        if not isinstance(tool_args, dict):
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"ok": False, "error": "Tool arguments must be a JSON object."}),
                        }
                    ],
                    "isError": True,
                },
            }
        try:
            payload = dispatch_mcp_tool(tool_name, tool_args)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(payload, ensure_ascii=False)}],
                    "isError": not bool(payload.get("ok", True)),
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False),
                        }
                    ],
                    "isError": True,
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def run_self_check() -> Dict[str, Any]:
    """Validate JSON-RPC `initialize` + `tools/list` schema structure without stdin."""
    init_resp = handle_jsonrpc_request({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    if not init_resp or init_resp.get("result", {}).get("protocolVersion") != "2024-11-05":
        raise RuntimeError("initialize protocolVersion check failed")
    server_info = init_resp["result"].get("serverInfo", {})
    if server_info.get("name") != "xlaya-mcp" or server_info.get("version") != __version__:
        raise RuntimeError("initialize serverInfo check failed")

    notif_resp = handle_jsonrpc_request({"jsonrpc": "2.0", "method": "notifications/initialized"})
    if notif_resp is not None:
        raise RuntimeError("notifications/initialized must return None")

    ping_resp = handle_jsonrpc_request({"jsonrpc": "2.0", "id": 2, "method": "ping"})
    if not ping_resp or ping_resp.get("result") != {}:
        raise RuntimeError("ping check failed")

    list_resp = handle_jsonrpc_request({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
    tools = (list_resp or {}).get("result", {}).get("tools", [])
    expected_names = ["xlaya_status", "xlaya_triage", "xlaya_predict", "xlaya_preload", "xlaya_unload"]
    actual_names = [t.get("name") for t in tools]
    if actual_names != expected_names:
        raise RuntimeError(f"tools/list mismatch: expected {expected_names}, got {actual_names}")
    for tool in tools:
        schema = tool.get("inputSchema", {})
        if schema.get("type") != "object" or not isinstance(schema.get("properties"), dict):
            raise RuntimeError(f"Invalid inputSchema for tool {tool.get('name')}")

    unknown_resp = handle_jsonrpc_request({"jsonrpc": "2.0", "id": 4, "method": "unknown/method"})
    if not unknown_resp or unknown_resp.get("error", {}).get("code") != -32601:
        raise RuntimeError("unknown method -32601 check failed")

    return {
        "ok": True,
        "server": "xlaya-mcp",
        "version": __version__,
        "protocolVersion": "2024-11-05",
        "tools": actual_names,
        "idle_ttl_sec": _get_idle_ttl_sec(),
    }


def _reconfigure_utf8(stream: Any) -> None:
    if stream is not None and hasattr(stream, "reconfigure"):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception as exc:
            sys.stderr.write(f"[xlaya-mcp] stream reconfigure note: {exc}\n")


def main(argv: Optional[List[str]] = None) -> int:
    """Run the JSON-RPC 2.0 MCP server loop over `stdin`/`_JSONRPC_OUT` with Wire Purity."""
    global _JSONRPC_OUT
    args = list(sys.argv[1:] if argv is None else argv)

    _JSONRPC_OUT = sys.stdout
    _reconfigure_utf8(sys.stdin)
    _reconfigure_utf8(_JSONRPC_OUT)
    _reconfigure_utf8(sys.stderr)
    sys.stdout = sys.stderr

    if "--self-check" in args:
        summary = run_self_check()
        _JSONRPC_OUT.write(json.dumps(summary, ensure_ascii=False) + "\n")
        _JSONRPC_OUT.flush()
        return 0

    try:
        for raw_line in sys.stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
            except json.JSONDecodeError as exc:
                sys.stderr.write(f"[xlaya-mcp] ignoring malformed JSON frame: {exc}\n")
                sys.stderr.flush()
                continue
            if not isinstance(req, dict):
                continue
            resp = handle_jsonrpc_request(req)
            if resp is not None:
                _JSONRPC_OUT.write(json.dumps(resp, ensure_ascii=False) + "\n")
                _JSONRPC_OUT.flush()
    finally:
        _cancel_idle_timer()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
