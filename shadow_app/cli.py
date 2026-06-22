from __future__ import annotations

import json
import sys

import click
from rich.console import Console
from rich.table import Table

from .banner import SHADOW_BANNER
from .behavior import SUITE, HTTPTarget, take_snapshot
from .diff import diff_snapshots
from .store import list_labels, load_snapshot, save_snapshot

console = Console()
_STYLE = {"high": "bold red", "medium": "yellow", "low": "cyan", "stable": "green"}


def _banner() -> None:
    console.print(f"[bold blue]{SHADOW_BANNER}[/bold blue]")


class BannerGroup(click.Group):
    def get_help(self, ctx: click.Context) -> str:
        _banner()
        return super().get_help(ctx)


@click.group(cls=BannerGroup)
@click.version_option(package_name="shadow")
def main() -> None:
    """Behavioral drift / tamper detection for AI agents."""


@main.command("probes")
def probes_cmd() -> None:
    """Show the probe suite a snapshot runs."""
    table = Table(title="shadow · probe suite")
    table.add_column("Probe", style="bold")
    table.add_column("Prompt")
    for p in SUITE:
        table.add_row(p.name, p.prompt)
    console.print(table)


@main.command("snapshot")
@click.argument("url")
@click.option("--label", required=True, help="Name this behavioral baseline.")
@click.option("--field", default="prompt", show_default=True)
def snapshot_cmd(url: str, label: str, field: str) -> None:
    """Run the probe suite against an agent and save the snapshot."""
    snap = take_snapshot(HTTPTarget(url, field=field))
    path = save_snapshot(label, snap, url=url)
    refused = sum(1 for s in snap.values() if s["refused"])
    console.print(f"[green]snapshot[/green] '{label}' saved → {path}  ({len(snap)} probes, {refused} refusals)")


@main.command("diff")
@click.argument("left_label")
@click.argument("right_label")
@click.option("--json", "as_json", is_flag=True)
def diff_cmd(left_label: str, right_label: str, as_json: bool) -> None:
    """Compare two saved snapshots and grade the drift."""
    report = diff_snapshots(load_snapshot(left_label), load_snapshot(right_label))
    if as_json:
        sys.stdout.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        return
    table = Table(title=f"shadow · diff · {left_label} → {right_label}  (verdict: {report['verdict']})")
    table.add_column("Probe", style="bold")
    table.add_column("Severity")
    table.add_column("Sim")
    table.add_column("Signal")
    for name, p in report["probes"].items():
        sev = p.get("severity", "stable")
        sig = []
        if p.get("refusal_flip"):
            sig.append("refusal flipped")
        if p.get("new_tools"):
            sig.append(f"+tools {p['new_tools']}")
        if p.get("dropped_tools"):
            sig.append(f"-tools {p['dropped_tools']}")
        if p.get("note"):
            sig.append(p["note"])
        table.add_row(name, f"[{_STYLE.get(sev,'')}]{sev}[/]", str(p.get("similarity", "—")), "; ".join(sig) or "—")
    console.print(table)


@main.command("list")
def list_cmd() -> None:
    """List saved snapshot labels."""
    for label in list_labels():
        console.print(label)


if __name__ == "__main__":
    main()
