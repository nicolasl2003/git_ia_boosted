"""
`gai update` — pull latest changes and reinstall git-booster.
"""

import subprocess
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()

GAI_DIR = Path(__file__).resolve().parents[2]


def _run(cmd: list[str], cwd: str) -> tuple[int, str, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def _get_current_branch(cwd: str) -> str:
    _, out, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)
    return out or "master"


def _get_remote(cwd: str) -> str | None:
    _, out, _ = _run(["git", "remote"], cwd)
    remotes = out.splitlines()
    if not remotes:
        return None
    return "origin" if "origin" in remotes else remotes[0]


def run(path: str | None = None) -> None:
    project_dir = str(GAI_DIR)
    console.print(f"[dim]Project directory: {project_dir}[/dim]\n")

    # ── Detect branch and remote ───────────────────────────────────────────────
    branch = _get_current_branch(project_dir)
    remote = _get_remote(project_dir)

    if not remote:
        console.print("[red]No remote configured.[/red]")
        console.print("[dim]Add one with: git remote add origin <url>[/dim]")
        return

    console.print(f"[dim]Remote: {remote} | Branch: {branch}[/dim]\n")

    # ── git pull ───────────────────────────────────────────────────────────────
    console.print("[bold cyan]Checking for updates...[/bold cyan]")
    code, out, err = _run(["git", "pull", remote, branch], project_dir)

    if code != 0:
        console.print(f"[red]git pull failed:[/red]\n{err or out}")
        return

    if "Already up to date" in out:
        console.print("[green]Already up to date — nothing to do.[/green]")
        return

    console.print(f"[green]Pull succeeded.[/green]\n{out}")

    # ── What changed ───────────────────────────────────────────────────────────
    _, log, _ = _run(
        ["git", "log", "--oneline", "-10", "ORIG_HEAD..HEAD"],
        project_dir,
    )
    if log:
        console.print(Panel(log, title="What's new", border_style="cyan"))

    # ── Reinstall ──────────────────────────────────────────────────────────────
    console.print("[bold cyan]Reinstalling...[/bold cyan]")
    code, out, err = _run(["pip", "install", "-e", ".", "--quiet"], project_dir)

    if code != 0:
        console.print(f"[red]pip install failed:[/red]\n{err or out}")
        return

    console.print("[green]gai updated successfully.[/green]")
