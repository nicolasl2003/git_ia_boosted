"""
`gb add` — runs `git add .` then generates/updates .gitignore via AI.
"""

import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from git_booster.core import git
from git_booster.ai import client as ai, prompts

console = Console()


def run(path: str | None = None) -> None:
    cwd = path or os.getcwd()

    if not git.is_git_repo(cwd):
        console.print("[red]Not inside a git repository.[/red]")
        return

    repo_root = git.get_repo_root(cwd)

    # ---- 1. git add . -------------------------------------------------------
    console.print("[bold cyan]Running git add .[/bold cyan]")
    git.add_all(cwd)
    console.print("[green]All changes staged.[/green]")

    # ---- 2. Collect files for .gitignore analysis --------------------------
    console.print("\n[bold cyan]Analysing project files for .gitignore generation...[/bold cyan]")
    all_files = git.walk_all_files(repo_root)

    gitignore_path = Path(repo_root) / ".gitignore"
    existing = gitignore_path.read_text(encoding="utf-8") if gitignore_path.exists() else ""

    # ---- 3. Ask Claude -------------------------------------------------------
    with console.status("[bold yellow]Claude is generating .gitignore...[/bold yellow]"):
        system, user = prompts.gitignore_prompt(all_files, existing)
        generated = ai.ask(system, user)

    # ---- 4. Preview & confirm ------------------------------------------------
    console.print(Panel(generated, title=".gitignore (generated)", border_style="yellow"))

    action = "update" if existing else "create"
    if Confirm.ask(f"[bold]Do you want to {action} .gitignore with this content?[/bold]", default=True):
        gitignore_path.write_text(generated, encoding="utf-8")
        console.print(f"[green].gitignore {action}d at {gitignore_path}[/green]")

        # Stage the .gitignore too
        git.add([".gitignore"], cwd)
        console.print("[green].gitignore staged.[/green]")
    else:
        console.print("[yellow].gitignore not modified.[/yellow]")
