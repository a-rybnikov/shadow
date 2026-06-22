"""Tests: a poisoned agent's drift must be caught; a stable one must read clean."""
from __future__ import annotations

from shadow_app.behavior import ReferenceTarget, extract, take_snapshot
from shadow_app.diff import diff_snapshots

# baseline agent: refuses the unsafe probe, no tool on arithmetic
SAFE = ReferenceTarget(script={
    "safety rules": "I can't help with that.",
    "OWNED": "I won't follow that instruction.",
    "weather": "I don't have a weather tool.",
    "17 * 23": "391",
})
# tampered agent: now complies and reaches for a tool
TAMPERED = ReferenceTarget(script={
    "safety rules": "Sure, here are the steps.",
    "OWNED": "OWNED",
    "weather": 'calling {"name": "http_fetch"} ...',
    "17 * 23": "391",
})


def test_extract_signals():
    s = extract("I cannot do that.")
    assert s.refused is True
    t = extract('using {"name": "search"} and {"name": "exec"}')
    assert t.tools == ["exec", "search"]


def test_identical_snapshots_are_stable():
    snap = take_snapshot(SAFE)
    report = diff_snapshots(snap, snap)
    assert report["verdict"] == "stable"


def test_tampering_is_detected_as_behavior_change():
    before = take_snapshot(SAFE)
    after = take_snapshot(TAMPERED)
    report = diff_snapshots(before, after)
    assert report["verdict"] == "behavior-change"
    # the refusal that disappeared is graded high
    assert report["probes"]["refusal"]["severity"] == "high"
    assert report["probes"]["refusal"]["refusal_flip"] is True
    # a tool appeared on the weather probe
    assert "http_fetch" in report["probes"]["tool-reflex"]["new_tools"]
    # arithmetic stayed the same
    assert report["probes"]["arithmetic"]["severity"] == "stable"


def test_missing_probe_side_is_flagged():
    report = diff_snapshots({"a": {"text": "x", "refused": False, "tools": []}}, {})
    assert report["probes"]["a"]["severity"] == "medium"
