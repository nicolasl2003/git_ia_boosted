"""
`gai add` — stage changes then manage .gitignore smartly.

Modes:
  gai add               → git add . (all)
  gai add file1 file2   → git add <files> (specific)

.gitignore behaviour:
  - Absent     : AI generates one from scratch
  - Present    : show untracked files, user selects what to ignore,
                 AI appends only the NEW rules needed
"""

import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.rule import Rule

from git_booster.core import git
from git_booster.ai import client as ai, prompts

console = Console()

ALWAYS_IGNORE = """\
# Python build artifacts (always ignore)
__pycache__/
*.py[cod]
*.egg-info/
*.dist-info/
__editable__*
.eggs/
dist/
build/
.venv/
venv/
"""


def _ensure_base_patterns(gitignore_path: Path, cwd: str) -> None:
    """Append any missing ALWAYS_IGNORE patterns to an existing .gitignore."""
    existing = gitignore_path.read_text(encoding="utf-8")
    missing_lines = [
        line for line in ALWAYS_IGNORE.splitlines()
        if line and not line.startswith("#") and line not in existing
    ]
    if missing_lines:
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("\n# Python build artifacts (auto-added)\n")
            f.write("\n".join(missing_lines) + "\n")
        git.add([".gitignore"], cwd)


def _select_files_to_ignore(untracked: list[str]) -> list[str]:
    """Interactive multi-select: pick which untracked files to add to .gitignore."""
    if not untracked:
        return []

    console.print(Rule("[bold]Untracked files[/bold]"))
    t = Table(show_header=True, header_style="bold cyan", box=None)
    t.add_column("#", style="cyan", width=4)
    t.add_column("File")
    for i, f in enumerate(untracked, 1):
        t.add_row(str(i), f)
    console.print(t)
    console.print()
    console.print(
        "[dim]Numbers (e.g. 1,3,5) | [bold]a[/bold] = all | [bold]n[/bold] = none[/dim]"
    )

    while True:
        raw = Prompt.ask("Select files to ignore", default="n").strip().lower()
        if raw == "n":
            return []
        if raw == "a":
            return untracked
        try:
            indices = [int(x.strip()) for x in raw.split(",")]
            selected = [untracked[i - 1] for i in indices if 1 <= i <= len(untracked)]
            if selected:
                return selected
            console.print("[yellow]No valid selection.[/yellow]")
        except (ValueError, IndexError):
            console.print("[yellow]Invalid input — use numbers like 1,2,3 or 'a' or 'n'.[/yellow]")


def _handle_gitignore(cwd: str, repo_root: str) -> None:
    """Generate or update .gitignore depending on whether it exists."""
    gitignore_path = Path(repo_root) / ".gitignore"

    # ── No .gitignore → generate from scratch ─────────────────────────────────
    if not gitignore_path.exists():
        console.print("\n[bold cyan]No .gitignore found — generating one...[/bold cyan]")
        all_files = git.walk_all_files(repo_root)
        with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
            system, user = prompts.gitignore_prompt(all_files)
            generated = ai.ask(system, user)
        final_content = ALWAYS_IGNORE + "\n" + generated.strip() + "\n"
        console.print(Panel(final_content, title=".gitignore (generated)", border_style="yellow"))
        if Confirm.ask("Create .gitignore with this content?", default=True):
            gitignore_path.write_text(final_content, encoding="utf-8")
            git.add([".gitignore"], cwd)
            console.print("[green].gitignore created and staged.[/green]")
        else:
            console.print("[yellow].gitignore not created.[/yellow]")
        return

    # ── .gitignore exists → ensure base patterns first ────────────────────────
    _ensure_base_patterns(gitignore_path, cwd)

    # ── selective append ───────────────────────────────────────────────────────
    untracked = git.list_untracked_files(cwd)
    if not untracked:
        console.print("[dim].gitignore up to date — no untracked files.[/dim]")
        return

    console.print(
        f"\n[bold cyan].gitignore exists.[/bold cyan] "
        f"[bold]{len(untracked)}[/bold] untracked file(s) found."
    )

    selected = _select_files_to_ignore(untracked)
    if not selected:
        console.print("[yellow]Nothing added to .gitignore.[/yellow]")
        return

    existing = gitignore_path.read_text(encoding="utf-8")
    with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
        system, user = prompts.gitignore_rules_prompt([], existing, selected)
        new_rules = ai.ask(system, user, max_tokens=512)

    if new_rules.strip().upper() == "NOTHING":
        console.print("[green]Already covered by .gitignore — no changes needed.[/green]")
        return

    console.print(Panel(new_rules, title="New rules to append", border_style="yellow"))
    if Confirm.ask("Append these rules to .gitignore?", default=True):
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("\n" + new_rules.strip() + "\n")
        git.add([".gitignore"], cwd)
        console.print("[green].gitignore updated and staged.[/green]")
    else:
        console.print("[yellow].gitignore not modified.[/yellow]")


def run(files: list[str] | None = None, path: str | None = None) -> None:
    cwd = path or os.getcwd()

    if not git.is_git_repo(cwd):
        console.print("[red]Not inside a git repository.[/red]")
        return

    repo_root = git.get_repo_root(cwd)

    # ── Stage files ────────────────────────────────────────────────────────────
    if files:
        valid, missing = [], []
        for f in files:
            p = Path(f) if Path(f).is_absolute() else Path(cwd) / f
            if p.exists():
                valid.append(f)
            else:
                missing.append(f)
        for m in missing:
            console.print(f"[yellow]Not found: {m}[/yellow]")
        if not valid:
            console.print("[red]No valid files to stage.[/red]")
            return
        git.add(valid, cwd)
        console.print(f"[green]Staged: {', '.join(valid)}[/green]")
    else:
        console.print("[bold cyan]Staging all changes...[/bold cyan]")
        git.add_all(cwd)
        console.print("[green]All changes staged.[/green]")

    # ── Handle .gitignore ──────────────────────────────────────────────────────
    _handle_gitignore(cwd, repo_root)
