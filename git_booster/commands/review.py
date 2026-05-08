"""
`gai review` — AI code review of staged changes before committing.
"""

import os

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule

from git_booster.core import git
from git_booster.ai import client as ai, prompts

console = Console()


def run(path: str | None = None, commit_ref: str | None = None) -> None:
    cwd = path or os.getcwd()

    if not git.is_git_repo(cwd):
        console.print("[red]Not inside a git repository.[/red]")
        return

    branch = git.get_branch(cwd)

    # --- Commit review mode ---
    if commit_ref:
        try:
            diff = git.diff_commit(commit_ref, cwd)
            info = git.get_commit_info(commit_ref, cwd)
        except git.GitError as e:
            console.print(f"[red]{e}[/red]")
            return

        if not diff:
            console.print(f"[yellow]Commit {commit_ref} has no diff (empty or merge commit).[/yellow]")
            return

        console.print(Rule(f"[bold]Code Review[/bold] — commit: [cyan]{commit_ref}[/cyan]  branch: [cyan]{branch}[/cyan]"))
        console.print(f"[dim]{info}[/dim]\n")

        with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
            system, user = prompts.review_prompt(diff, info)
            review = ai.ask(system, user, max_tokens=1024)

        console.print(Panel(review, title=f"AI Code Review — {commit_ref}", border_style="magenta"))
        return

    # --- Staged / unstaged mode ---
    diff = git.diff_staged(cwd)
    if not diff:
        diff = git.diff_unstaged(cwd)
        if not diff:
            console.print("[yellow]No changes to review (nothing staged or modified).[/yellow]")
            return
        console.print("[dim]No staged changes — reviewing unstaged diff instead.[/dim]")

    raw_status = git.status(cwd)

    console.print(Rule(f"[bold]Code Review[/bold] — branch: [cyan]{branch}[/cyan]"))

    with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
        system, user = prompts.review_prompt(diff, raw_status)
        review = ai.ask(system, user, max_tokens=1024)

    console.print(Panel(review, title="AI Code Review", border_style="magenta"))
