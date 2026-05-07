"""
`gb status` — shows `git status` then prints an AI-generated summary.
"""

import os

from rich.console import Console
from rich.rule import Rule
from rich.panel import Panel

from git_booster.core import git
from git_booster.ai import client as ai, prompts

console = Console()


def run(path: str | None = None) -> None:
    cwd = path or os.getcwd()

    if not git.is_git_repo(cwd):
        console.print("[red]Not inside a git repository.[/red]")
        return

    # ---- 1. Raw git status --------------------------------------------------
    raw_status = git.status(cwd)
    branch = git.get_branch(cwd)
    log = git.get_log(n=5, path=cwd)

    console.print(Rule(f"[bold]git status[/bold] — branch: [cyan]{branch}[/cyan]"))
    console.print(raw_status)
    if not log:
        console.print("[dim]No commits yet.[/dim]")
    console.print()

    # ---- 2. AI summary -------------------------------------------------------
    with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
        log_display = log if log else "No commits yet."
        system, user = prompts.status_prompt(raw_status, log_display, branch)
        summary = ai.ask(system, user, max_tokens=512)

    console.print(Panel(summary, title="AI Summary", border_style="cyan"))
