"""
`gai update` — pull latest changes and reinstall git-booster.
"""

import sys
import subprocess
import shutil
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

console = Console()

GAI_DIR = Path(__file__).resolve().parents[2]
VENV_DIR = GAI_DIR / ".venv"

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

def _get_remote_url(cwd: str, remote: str) -> str:
    _, out, _ = _run(["git", "remote", "get-url", remote], cwd)
    return out

def _check_connectivity(cwd: str, remote: str) -> tuple[bool, str]:
    code, _, err = _run(["git", "ls-remote", "--exit-code", remote], cwd)
    return code == 0, err

def _list_remote_branches(cwd: str, remote: str) -> list[str]:
    _, out, _ = _run(["git", "branch", "-r"], cwd)
    branches = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith(f"{remote}/") and "HEAD" not in line:
            branches.append(line.replace(f"{remote}/", ""))
    return branches

def _rebuild_venv(project_dir: str) -> bool:
    """Delete .venv, recreate it, reinstall dependencies."""
    console.print("[bold cyan]Rebuilding virtual environment...[/bold cyan]")

    # 1. Delete old venv
    if VENV_DIR.exists():
        console.print(f"[dim]Removing {VENV_DIR}...[/dim]")
        shutil.rmtree(VENV_DIR)

    # 2. Create new venv with the system python3
    python = shutil.which("python3") or shutil.which("python") or sys.executable
    code, out, err = _run([python, "-m", "venv", str(VENV_DIR)], project_dir)
    if code != 0:
        console.print(f"[red]venv creation failed:[/red]\n{err or out}")
        return False

    # 3. Upgrade pip inside the new venv
    venv_pip = str(VENV_DIR / "bin" / "pip")
    _run([venv_pip, "install", "--upgrade", "pip", "--quiet"], project_dir)

    # 4. Install project in editable mode
    code, out, err = _run([venv_pip, "install", "-e", ".", "--quiet"], project_dir)
    if code != 0:
        console.print(f"[red]pip install failed:[/red]\n{err or out}")
        return False

    console.print(f"[green]Virtual environment rebuilt at {VENV_DIR}[/green]")
    return True

def run(path: str | None = None) -> None:
    project_dir = str(GAI_DIR)
    console.print(f"[dim]Project directory: {project_dir}[/dim]\n")

    branch = _get_current_branch(project_dir)
    remote = _get_remote(project_dir)

    if not remote:
        console.print("[red]No remote configured.[/red]")
        console.print("[dim]Add one with: git remote add origin <url>[/dim]")
        return

    remote_url = _get_remote_url(project_dir, remote)
    console.print(f"[dim]Remote: {remote} ({remote_url}) | Branch: {branch}[/dim]\n")

    console.print("[bold cyan]Checking connectivity...[/bold cyan]")
    ok, err = _check_connectivity(project_dir, remote)
    if not ok:
        console.print(f"[red]Cannot reach remote:[/red] {remote_url}")
        if "authentication" in err.lower() or "permission" in err.lower():
            console.print("[yellow]Authentication issue detected.[/yellow]")
            console.print("[dim]SSH key:  ssh-add ~/.ssh/id_rsa[/dim]")
            console.print("[dim]HTTPS:    use a personal access token as password[/dim]")
        else:
            console.print(f"[dim]{err}[/dim]")
        return

    console.print("[bold cyan]Checking for updates...[/bold cyan]")
    code, out, err = _run(["git", "pull", remote, branch], project_dir)

    if code != 0:
        console.print(f"[red]git pull failed:[/red]\n{err or out}")
        if "couldn't find remote ref" in err.lower():
            branches = _list_remote_branches(project_dir, remote)
            if branches:
                console.print("[yellow]Available branches on remote:[/yellow]")
                for b in branches:
                    console.print(f"  [dim]•[/dim] {b}")
        return

    already_up_to_date = "Already up to date" in out or "Déjà à jour" in out

    if already_up_to_date and VENV_DIR.exists():
        console.print("[green]Already up to date — nothing to do.[/green]")
        return

    if not already_up_to_date:
        console.print(f"[green]Pull succeeded.[/green]\n{out}")
        _, log, _ = _run(
            ["git", "log", "--oneline", "-10", "ORIG_HEAD..HEAD"],
            project_dir,
        )
        if log:
            console.print(Panel(log, title="What's new", border_style="cyan"))

    # Rebuild venv (always if pulled, or if venv missing)
    ok = _rebuild_venv(project_dir)
    if not ok:
        return

    console.print("\n[bold green]✓ gai updated successfully.[/bold green]")
    console.print(f"[dim]Restart your shell or run: source {VENV_DIR}/bin/activate[/dim]")

