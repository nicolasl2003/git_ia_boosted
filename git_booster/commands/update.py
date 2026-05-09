"""
`gai update` — pull latest changes and reinstall git-booster.
"""

import os
import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()

GAI_DIR = Path(__file__).resolve().parents[2]


def _run(cmd: list[str], cwd: str) -> tuple[int, str, str]:
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def run(path: str | None = None) -> None:
    project_dir = str(GAI_DIR)
    console.print(f"[dim]Project directory: {project_dir}[/dim]\n")

    # ── 1. git pull ────────────────────────────────────────────────────────────
    console.print("[bold cyan]Checking for updates...[/bold cyan]")
    code, out, err = _run(["git", "pull", "origin", "main"], project_dir)

    if code != 0:
        console.print(f"[red]git pull failed:[/red]\n{err or out}")
        return

    if "Already up to date" in out:
        console.print("[green]Already up to date — nothing to do.[/green]")
        return

    console.print(f"[green]Pull succeeded.[/green]\n{out}")

    # ── 2. Show what changed ───────────────────────────────────────────────────
    _, log, _ = _run(
        ["git", "log", "--oneline", "-10", "ORIG_HEAD..HEAD"],
        project_dir,
    )
    if log:
        console.print(Panel(log, title="What's new", border_style="cyan"))

    # ── 3. Reinstall ───────────────────────────────────────────────────────────
    console.print("[bold cyan]Reinstalling...[/bold cyan]")
    code, out, err = _run(
        ["pip", "install", "-e", ".", "--quiet"],
        project_dir,
    )

    if code != 0:
        console.print(f"[red]pip install failed:[/red]\n{err or out}")
        return

    console.print("[green]gai updated successfully.[/green]")
