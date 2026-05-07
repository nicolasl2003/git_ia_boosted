"""
Skill: explain — AI explanation of a file or the current diff.
Usage: gai skill explain [<file>]
"""

import os
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from git_booster.core import git
from git_booster.ai import client as ai

NAME        = "explain"
DESCRIPTION = "AI explanation of a file or the current staged diff"

console = Console()

_SYSTEM = """\
You are a senior software engineer explaining code to a colleague.
Be concise (max 8 lines). Plain text only, no markdown fences.
Focus on: what it does, why it exists, any risks or notable patterns.
"""


def run(args: list[str], path: str | None = None) -> None:
    cwd = path or os.getcwd()

    if args:
        # Explain a specific file
        target = Path(args[0])
        if not target.is_absolute():
            target = Path(cwd) / target
        if not target.exists():
            console.print(f"[red]File not found: {target}[/red]")
            return
        content = target.read_text(encoding="utf-8", errors="replace")[:4000]
        user = f"File: {args[0]}\n\n{content}\n\nExplain this file."
        title = f"Explanation: {args[0]}"
    else:
        # Explain current staged diff
        if not git.is_git_repo(cwd):
            console.print("[red]Not inside a git repository.[/red]")
            return
        diff = git.diff_staged(cwd) or git.diff_unstaged(cwd)
        if not diff:
            console.print("[yellow]No changes to explain.[/yellow]")
            return
        user = f"Diff:\n{diff[:4000]}\n\nExplain these changes."
        title = "Explanation: current changes"

    with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
        result = ai.ask(_SYSTEM, user, max_tokens=300)

    console.print(Panel(result, title=title, border_style="blue"))
