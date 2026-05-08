"""
`gai add` — stage all changes then manage .gitignore smartly:
  - No .gitignore: AI generates one from scratch
  - .gitignore exists: show untracked files, let user select what to ignore,
    AI generates only the NEW rules to append
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


def _select_files_to_ignore(untracked: list[str]) -> list[str]:
    """Interactive multi-select: user picks which untracked files to add to .gitignore."""
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
        "[dim]Enter numbers to ignore (e.g. 1,3,5), "
        "[bold]a[/bold] for all, [bold]n[/bold] for none.[/dim]"
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
            return selected
        except (ValueError, IndexError):
            console.print("[yellow]Invalid input. Use numbers like 1,2,3 or 'a' or 'n'.[/yellow]")


def run(path: str | None = None) -> None:
    cwd = path or os.getcwd()

    if not git.is_git_repo(cwd):
        console.print("[red]Not inside a git repository.[/red]")
        return

    repo_root = git.get_repo_root(cwd)
    gitignore_path = Path(repo_root) / ".gitignore"

    # ── 1. git add . ──────────────────────────────────────────────────────────
    console.print("[bold cyan]Staging all changes...[/bold cyan]")
    git.add_all(cwd)
    console.print("[green]All changes staged.[/green]\n")

    # ── 2. .gitignore absent → generate from scratch ──────────────────────────
    if not gitignore_path.exists():
        console.print("[bold cyan]No .gitignore found — generating one...[/bold cyan]")
        all_files = git.walk_all_files(repo_root)

        with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
            system, user = prompts.gitignore_prompt(all_files)
            generated = ai.ask(system, user)

        console.print(Panel(generated, title=".gitignore (generated)", border_style="yellow"))

        if Confirm.ask("Create .gitignore with this content?", default=True):
            gitignore_path.write_text(generated, encoding="utf-8")
            git.add([".gitignore"], cwd)
            console.print("[green].gitignore created and staged.[/green]")
        else:
            console.print("[yellow].gitignore not created.[/yellow]")
        return

    # ── 3. .gitignore exists → show untracked, selective ignore ───────────────
    untracked = git.list_untracked_files(cwd)

    if not untracked:
        console.print("[green].gitignore already exists. No untracked files to ignore.[/green]")
        return

    console.print(
        f"[bold cyan].gitignore exists.[/bold cyan] "
        f"Found [bold]{len(untracked)}[/bold] untracked file(s).\n"
    )

    selected = _select_files_to_ignore(untracked)

    if not selected:
        console.print("[yellow]No files selected — .gitignore not modified.[/yellow]")
        return

    existing = gitignore_path.read_text(encoding="utf-8")

    with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
        system, user = prompts.gitignore_rules_prompt([], existing, selected)
        new_rules = ai.ask(system, user, max_tokens=512)

    if new_rules.strip().upper() == "NOTHING":
        console.print("[green]All selected files are already covered by .gitignore.[/green]")
        return

    console.print(Panel(new_rules, title="New rules to add", border_style="yellow"))

    if Confirm.ask("Append these rules to .gitignore?", default=True):
        with open(gitignore_path, "a", encoding="utf-8") as f:
            f.write("\n" + new_rules.strip() + "\n")
        git.add([".gitignore"], cwd)
        console.print("[green].gitignore updated and staged.[/green]")
    else:
        console.print("[yellow].gitignore not modified.[/yellow]")
