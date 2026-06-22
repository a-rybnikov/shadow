"""Persist behavioral snapshots by label."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path.home() / ".local" / "share" / "mad" / "shadow"


def save_snapshot(label: str, snapshot: dict[str, Any], *, url: str | None = None) -> Path:
    ROOT.mkdir(parents=True, exist_ok=True)
    path = ROOT / f"{label}.json"
    path.write_text(json.dumps({"label": label, "url": url, "snapshot": snapshot}, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_snapshot(label: str) -> dict[str, Any]:
    path = ROOT / f"{label}.json"
    if not path.exists():
        raise FileNotFoundError(label)
    return json.loads(path.read_text(encoding="utf-8"))["snapshot"]


def list_labels() -> list[str]:
    if not ROOT.exists():
        return []
    return sorted(p.stem for p in ROOT.glob("*.json"))
