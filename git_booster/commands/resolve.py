"""
`gb resolve` — detects merge conflicts and resolves them using AI.
"""

import os

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

    if not git.has_merge_conflicts(cwd):
        console.print("[green]No merge conflicts detected.[/green]")
        return

    repo_root = git.get_repo_root(cwd)
    conflict_files = git.get_conflict_files(cwd)

    console.print(
        f"[bold red]Found {len(conflict_files)} file(s) with merge conflicts:[/bold red]"
    )
    for f in conflict_files:
        console.print(f"  [yellow]• {f}[/yellow]")

    console.print()

    resolved_count = 0

    for filepath in conflict_files:
        console.rule(f"[bold]{filepath}[/bold]")

        content = git.read_conflict_file(filepath, repo_root)

        # Preview conflicts
        conflict_lines = [
            line for line in content.splitlines()
            if line.startswith("<<<<<<<") or line.startswith("=======") or line.startswith(">>>>>>>")
        ]
        console.print(f"[dim]{len(conflict_lines) // 3} conflict block(s) found[/dim]")

        if not Confirm.ask(f"Let Claude resolve conflicts in [bold]{filepath}[/bold]?", default=True):
            console.print(f"[yellow]Skipped {filepath}[/yellow]")
            continue

        with console.status(f"[bold yellow]A.I is processing {filepath}...[/bold yellow]"):
            system, user = prompts.conflict_prompt(filepath, content)
            resolved = ai.ask(system, user, max_tokens=4096)

        # Show a diff-like preview (just the resolved file, truncated)
        preview_lines = resolved.splitlines()[:40]
        preview = "\n".join(preview_lines)
        if len(resolved.splitlines()) > 40:
            preview += "\n... (truncated)"

        console.print(Panel(preview, title=f"Resolved: {filepath}", border_style="green"))

        if Confirm.ask("Apply this resolution?", default=True):
            git.write_resolved_file(filepath, resolved, repo_root)
            git.mark_resolved(filepath, cwd)
            console.print(f"[green]{filepath} resolved and staged.[/green]")
            resolved_count += 1
        else:
            console.print(f"[yellow]{filepath} not modified.[/yellow]")

    console.print()
    if resolved_count > 0:
        console.print(
            f"[bold green]{resolved_count}/{len(conflict_files)} conflict(s) resolved.[/bold green]"
        )
        console.print("You can now run [bold]gai commit[/bold] to finalise the merge.")
    else:
        console.print("[yellow]No files were modified.[/yellow]")
