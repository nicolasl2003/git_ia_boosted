"""
`gb review` — AI code review of staged changes before committing.
"""

import os

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from git_booster.core import git
from git_booster.ai import client as ai, prompts

console = Console()


def run(path: str | None = None) -> None:
    cwd = path or os.getcwd()

    if not git.is_git_repo(cwd):
        console.print("[red]Not inside a git repository.[/red]")
        return

    diff = git.diff_staged(cwd)
    if not diff:
        # Fall back to unstaged changes
        diff = git.diff_unstaged(cwd)
        if not diff:
            console.print("[yellow]No changes to review (nothing staged or modified).[/yellow]")
            return
        console.print("[dim]No staged changes — reviewing unstaged diff instead.[/dim]")

    raw_status = git.status(cwd)
    branch = git.get_branch(cwd)

    console.print(Rule(f"[bold]Code Review[/bold] — branch: [cyan]{branch}[/cyan]"))

    with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
        system, user = prompts.review_prompt(diff, raw_status)
        review = ai.ask(system, user, max_tokens=1024)

    console.print(Panel(review, title="AI Code Review", border_style="magenta"))
