"""
`gai review` — AI code review of staged changes before committing.
"""

import os

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.prompt import Prompt

from git_booster.core import git
from git_booster.ai import client as ai, prompts

console = Console()


def _chat_loop(review: str, diff: str, context: str) -> None:
    """Interactive chat loop after the initial review."""

    console.print("\n[dim]You can now ask questions about this review.[/dim]")
    console.print("[dim]Type [bold]exit[/bold] or [bold]q[/bold] or leave empty to quit.[/dim]\n")

    history: list[dict] = [
        {
            "role": "system",
            "content": (
                "You are an expert code reviewer. "
                "You just reviewed a git diff and produced the following review:\n\n"
                f"{review}\n\n"
                "The user may now ask you questions about the review, the code, "
                "or request clarifications. Answer concisely and helpfully.\n\n"
                f"Context:\n{context}\n\n"
                f"Original diff:\n{diff}"
            ),
        },
        {
            "role": "assistant",
            "content": review,
        },
    ]

    while True:
        try:
            user_input = Prompt.ask("[bold cyan]You[/bold cyan]").strip()
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Chat ended.[/dim]")
            break

        if not user_input or user_input.lower() in {"exit", "q", "quit"}:
            console.print("[dim]Chat ended.[/dim]")
            break

        history.append({"role": "user", "content": user_input})

        with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
            try:
                answer = ai.ask_with_history(history)
            except Exception as e:
                console.print(f"[red]AI error: {e}[/red]")
                history.pop()  # remove the unanswered user message
                continue

        history.append({"role": "assistant", "content": answer})

        console.print(Panel(answer, title="[bold green]A.I[/bold green]", border_style="green"))


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

        _chat_loop(review=review, diff=diff, context=info)
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

    _chat_loop(review=review, diff=diff, context=raw_status)
