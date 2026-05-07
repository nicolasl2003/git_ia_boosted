"""
`gai status` — native git status output, no AI, instant.
Use `gai review` for an AI-powered analysis.
"""

import os
import subprocess

from rich.console import Console
from rich.rule import Rule

from git_booster.core import git

console = Console()


def run(path: str | None = None) -> None:
    cwd = path or os.getcwd()

    if not git.is_git_repo(cwd):
        console.print("[red]Not inside a git repository.[/red]")
        return

    branch = git.get_branch(cwd)
    console.print(Rule(f"[bold]git status[/bold] — branch: [cyan]{branch}[/cyan]"))

    # Pass-through: stream raw git output directly to terminal
    subprocess.run(["git", "status"], cwd=cwd)
