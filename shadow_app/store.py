from __future__ import annotations

import difflib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

ROOT = Path.home() / ".local" / "share" / "mad" / "shadow"


def _label_dir(label: str) -> Path:
    path = ROOT / label
    path.mkdir(parents=True, exist_ok=True)
    return path


def _stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")


def _trace_path(label: str) -> Path:
    return _label_dir(label) / f"{_stamp()}.json"


def record_trace(url: str, label: str, prompt: str = "baseline trace request") -> Path:
    started = datetime.now(timezone.utc)
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        response = client.post(url, json={"prompt": prompt, "label": label})
    ended = datetime.now(timezone.utc)
    trace = {
        "label": label,
        "timestamp": started.isoformat(),
        "url": url,
        "prompt": prompt,
        "response": response.text,
        "response_time_ms": int((ended - started).total_seconds() * 1000),
        "tool_calls": [],
        "tokens_used": None,
    }
    path = _trace_path(label)
    path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_traces() -> list[Path]:
    if not ROOT.exists():
        return []
    return sorted(ROOT.glob("*/*.json"))


def load_latest(label: str) -> dict[str, Any]:
    files = sorted((ROOT / label).glob("*.json"))
    if not files:
        raise FileNotFoundError(label)
    return json.loads(files[-1].read_text(encoding="utf-8"))


def diff_traces(left_label: str, right_label: str) -> dict[str, Any]:
    left = load_latest(left_label)
    right = load_latest(right_label)
    if left == right:
        return {"changed": False, "summary": "no changes", "diff": "", "time_delta_ms": 0}
    diff = "\n".join(
        difflib.unified_diff(
            left["response"].splitlines(),
            right["response"].splitlines(),
            fromfile=left_label,
            tofile=right_label,
            lineterm="",
        )
    )
    left_tools = set(left.get("tool_calls", []))
    right_tools = set(right.get("tool_calls", []))
    return {
        "changed": True,
        "summary": "changes detected",
        "diff": diff or "(response differs but no unified diff lines)",
        "new_tools": sorted(right_tools - left_tools),
        "removed_tools": sorted(left_tools - right_tools),
        "time_delta_ms": right.get("response_time_ms", 0) - left.get("response_time_ms", 0),
    }


def export_html(left_label: str, right_label: str) -> Path:
    report = diff_traces(left_label, right_label)
    out = ROOT / f"{left_label}_vs_{right_label}.html"
    html = f"""<html><body><h1>shadow diff</h1><p>{report['summary']}</p><pre>{report.get('diff', '')}</pre></body></html>"""
    out.write_text(html, encoding="utf-8")
    return out
