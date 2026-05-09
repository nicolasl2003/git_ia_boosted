"""
`gai update` — pull latest changes, rebuild venv, fix alias, log changelog.
"""

import sys
import subprocess
import shutil
import os
import datetime
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

console = Console()

GAI_DIR      = Path(__file__).resolve().parents[2]
VENV_DIR     = GAI_DIR / ".venv"
VENV_BAK     = GAI_DIR / ".venv.bak"
CONFIG_DIR   = Path.home() / ".config" / "git-booster"
UPDATE_LOG   = CONFIG_DIR / "update.log"
SHELL_FILES  = [
    Path.home() / ".zshrc",
    Path.home() / ".bashrc",
    Path.home() / ".bash_profile",
    Path.home() / ".profile",
]

# ─── helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
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

# ─── python detection ─────────────────────────────────────────────────────────

def _best_python() -> str:
    """
    Prefer brew/pyenv python over system python on macOS.
    Falls back to sys.executable.
    """
    candidates = []

    # pyenv shim
    pyenv_root = os.environ.get("PYENV_ROOT", str(Path.home() / ".pyenv"))
    pyenv_python = Path(pyenv_root) / "shims" / "python3"
    if pyenv_python.exists():
        candidates.append(str(pyenv_python))

    # Homebrew (Apple Silicon + Intel)
    for brew_prefix in ["/opt/homebrew", "/usr/local"]:
        for minor in range(13, 9, -1):
            p = Path(f"{brew_prefix}/bin/python3.{minor}")
            if p.exists():
                candidates.append(str(p))
        p = Path(f"{brew_prefix}/bin/python3")
        if p.exists():
            candidates.append(str(p))

    # PATH python3
    which = shutil.which("python3") or shutil.which("python")
    if which:
        candidates.append(which)

    candidates.append(sys.executable)

    for candidate in candidates:
        code, out, _ = _run([candidate, "--version"])
        if code == 0:
            console.print(f"[dim]Using python: {candidate} ({out})[/dim]")
            return candidate

    return sys.executable

# ─── venv health check ────────────────────────────────────────────────────────

def _venv_is_healthy() -> bool:
    """Return True if .venv/bin/gai exists and runs without error."""
    gai_bin = VENV_DIR / "bin" / "gai"
    if not gai_bin.exists():
        return False
    code, _, _ = _run([str(gai_bin), "--version"])
    return code == 0

# ─── alias fix ────────────────────────────────────────────────────────────────

def _fix_alias() -> None:
    """Ensure shell rc files point to the correct .venv/bin/gai."""
    correct_bin  = str(VENV_DIR / "bin" / "gai")
    alias_line   = f"alias gai='{correct_bin}'"
    alias_prefix = "alias gai="

    for rc in SHELL_FILES:
        if not rc.exists():
            continue

        lines   = rc.read_text().splitlines()
        current = next((l for l in lines if alias_prefix in l), None)

        if current is None:
            # No alias at all — add it
            with rc.open("a") as f:
                f.write(f"\n# git-booster\n{alias_line}\n")
            console.print(f"[green]Alias added[/green] → {rc.name}")

        elif current.strip() != alias_line:
            # Wrong alias — fix it
            new_lines = [alias_line if alias_prefix in l else l for l in lines]
            rc.write_text("\n".join(new_lines) + "\n")
            console.print(f"[yellow]Alias fixed[/yellow] → {rc.name}")
            console.print(f"  [dim]was:[/dim] {current.strip()}")
            console.print(f"  [dim]now:[/dim] {alias_line}")

        else:
            console.print(f"[dim]Alias OK in {rc.name}[/dim]")

# ─── changelog ────────────────────────────────────────────────────────────────

COMMIT_TYPES = {
    "feat":     ("✨", "cyan",   "Features"),
    "fix":      ("🐛", "red",    "Bug fixes"),
    "perf":     ("⚡", "yellow", "Performance"),
    "refactor": ("♻️", "blue",   "Refactoring"),
    "docs":     ("📝", "white",  "Documentation"),
    "test":     ("🧪", "magenta","Tests"),
    "chore":    ("🔧", "dim",    "Chores"),
    "ci":       ("🤖", "dim",    "CI"),
    "style":    ("🎨", "dim",    "Style"),
}

def _parse_commits(log: str) -> dict[str, list[str]]:
    """Group commits by conventional commit type."""
    groups: dict[str, list[str]] = {}
    for line in log.splitlines():
        parts = line.split(" ", 1)
        if len(parts) < 2:
            continue
        msg = parts[1]
        matched = False
        for ctype in COMMIT_TYPES:
            if msg.lower().startswith(f"{ctype}(") or msg.lower().startswith(f"{ctype}:"):
                groups.setdefault(ctype, []).append(msg)
                matched = True
                break
        if not matched:
            groups.setdefault("other", []).append(msg)
    return groups

def _display_changelog(log: str) -> None:
    """Display a nicely formatted changelog from git log --oneline."""
    if not log:
        return

    groups = _parse_commits(log)

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column(style="bold")
    table.add_column()

    for ctype, (icon, color, label) in COMMIT_TYPES.items():
        if ctype in groups:
            for i, msg in enumerate(groups[ctype]):
                prefix = f"{icon} [{color}]{label}[/{color}]" if i == 0 else "  "
                table.add_row(prefix, msg)

    if "other" in groups:
        for i, msg in enumerate(groups["other"]):
            prefix = "📦 [dim]Other[/dim]" if i == 0 else "  "
            table.add_row(prefix, msg)

    console.print(Panel(table, title="What's new", border_style="cyan"))

def _save_changelog(log: str, version: str) -> None:
    """Append changelog entry to update.log."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with UPDATE_LOG.open("a") as f:
        f.write(f"\n{'─'*60}\n")
        f.write(f"Update: {timestamp}  |  HEAD: {version}\n")
        f.write(f"{'─'*60}\n")
        f.write(log + "\n")
    console.print(f"[dim]Changelog saved → {UPDATE_LOG}[/dim]")

# ─── venv rebuild ─────────────────────────────────────────────────────────────

def _rebuild_venv(project_dir: str) -> bool:
    """Backup old venv, create a new one, reinstall dependencies."""

    # 1. Backup old venv
    if VENV_DIR.exists():
        if VENV_BAK.exists():
            shutil.rmtree(VENV_BAK)
        VENV_DIR.rename(VENV_BAK)
        console.print(f"[dim]Old venv backed up → {VENV_BAK.name}[/dim]")

    python = _best_python()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:

        # 2. Create venv
        task = progress.add_task("Creating virtual environment...", total=None)
        code, out, err = _run([python, "-m", "venv", str(VENV_DIR)], project_dir)
        if code != 0:
            console.print(f"[red]venv creation failed:[/red]\n{err or out}")
            # Rollback
            if VENV_BAK.exists():
                VENV_BAK.rename(VENV_DIR)
                console.print("[yellow]Rolled back to previous venv.[/yellow]")
            return False

        venv_pip = str(VENV_DIR / "bin" / "pip")

        # 3. Upgrade pip
        progress.update(task, description="Upgrading pip...")
        _run([venv_pip, "install", "--upgrade", "pip", "--quiet"], project_dir)

        # 4. Install project
        progress.update(task, description="Installing git-booster...")
        code, out, err = _run(
            [venv_pip, "install", "-e", ".", "--quiet"], project_dir
        )
        if code != 0:
            console.print(f"[red]pip install failed:[/red]\n{err or out}")
            # Rollback
            shutil.rmtree(VENV_DIR, ignore_errors=True)
            if VENV_BAK.exists():
                VENV_BAK.rename(VENV_DIR)
                console.print("[yellow]Rolled back to previous venv.[/yellow]")
            return False

        progress.update(task, description="Done!")

    # 5. Clean up backup on success
    if VENV_BAK.exists():
        shutil.rmtree(VENV_BAK)
        console.print("[dim]Backup venv removed.[/dim]")

    return True

# ─── main ─────────────────────────────────────────────────────────────────────

def run() -> None:
    project_dir = str(GAI_DIR)
    branch      = _get_current_branch(project_dir)

    console.print(Panel(
        f"[bold]Project:[/bold] {project_dir}\n"
        f"[bold]Branch:[/bold]  {branch}",
        title="gai update",
        border_style="cyan",
    ))

    remote = _get_remote(project_dir)
    if not remote:
        console.print("[red]No remote configured.[/red]")
        console.print("[dim]Add one: git remote add origin <url>[/dim]")
        return

    remote_url = _get_remote_url(project_dir, remote)
    console.print(f"[dim]Remote: {remote} ({remote_url})[/dim]\n")

    # ── connectivity ──
    console.print("[bold cyan]Checking connectivity...[/bold cyan]")
    ok, err = _check_connectivity(project_dir, remote)
    if not ok:
        console.print(f"[red]Cannot reach remote:[/red] {remote_url}")
        if "authentication" in err.lower() or "permission" in err.lower():
            console.print("[yellow]Authentication issue.[/yellow]")
            console.print("[dim]SSH:   ssh-add ~/.ssh/id_rsa[/dim]")
            console.print("[dim]HTTPS: use a personal access token[/dim]")
        else:
            console.print(f"[dim]{err}[/dim]")
        return

    # ── pull ──
    console.print("[bold cyan]Checking for updates...[/bold cyan]")
    code, out, err = _run(["git", "pull", remote, branch], project_dir)

    if code != 0:
        console.print(f"[red]git pull failed:[/red]\n{err or out}")
        if "couldn't find remote ref" in err.lower():
            branches = _list_remote_branches(project_dir, remote)
            if branches:
                console.print("[yellow]Available branches:[/yellow]")
                for b in branches:
                    console.print(f"  [dim]•[/dim] {b}")
        return

    already_up_to_date = (
        "Already up to date" in out or "Déjà à jour" in out
    )

    # ── changelog ──
    _, log, _ = _run(
        ["git", "log", "--oneline", "-20", "ORIG_HEAD..HEAD"],
        project_dir,
    )

    need_rebuild = not already_up_to_date or not _venv_is_healthy()

    if already_up_to_date and not need_rebuild:
        console.print("[green]Already up to date — nothing to do.[/green]")
        return

    if not already_up_to_date:
        console.print(f"[green]Pull succeeded.[/green]")
        if log:
            _display_changelog(log)
            _, head, _ = _run(["git", "rev-parse", "--short", "HEAD"], project_dir)
            _save_changelog(log, head)

    # ── rebuild venv ──
    console.print()
    ok = _rebuild_venv(project_dir)
    if not ok:
        return

    # ── fix alias ──
    console.print()
    console.print("[bold cyan]Checking shell alias...[/bold cyan]")
    _fix_alias()

    # ── done ──
    console.print()
    console.print("[bold green]✓ gai updated successfully.[/bold green]")
    console.print(
        f"[dim]Reload your shell:  source ~/.zshrc  or open a new terminal[/dim]"
    )
