"""
`gai rm <file>` — remove a file from git tracking.
  default  : git rm --cached <file>   (untrack only, keep on disk)
  --hard   : git rm -f <file> + os.remove (untrack + delete from disk)
"""

import os
from pathlib import Path

from rich.console import Console
from rich.prompt import Confirm

from git_booster.core import git

console = Console()


def run(files: list[str], hard: bool = False, path: str | None = None) -> None:
    cwd = path or os.getcwd()

    if not git.is_git_repo(cwd):
        console.print("[red]Not inside a git repository.[/red]")
        return

    if not files:
        console.print("[yellow]No files specified. Usage: gai rm <file> [--hard][/yellow]")
        return

    repo_root = git.get_repo_root(cwd)

    for f in files:
        fpath = Path(repo_root) / f
        tracked = git.is_tracked(f, cwd)

        if hard:
            # Warn before physical deletion
            exists = fpath.exists()
            console.print(
                f"[bold red]--hard:[/bold red] will untrack and [bold]delete[/bold] "
                f"[yellow]{f}[/yellow] from disk."
            )
            if not Confirm.ask("Confirm permanent deletion?", default=False):
                console.print(f"[yellow]Skipped {f}[/yellow]")
                continue

            if tracked:
                git.rm_file(f, cwd, force=True)
                console.print(f"[green]Untracked {f} from git.[/green]")
            if exists:
                fpath.unlink()
                console.print(f"[red]Deleted {f} from disk.[/red]")
            elif not tracked:
                console.print(f"[yellow]{f} not found on disk and not tracked — nothing to do.[/yellow]")

        else:
            # Soft: untrack only
            if not tracked:
                console.print(f"[yellow]{f} is not tracked by git — nothing to untrack.[/yellow]")
                continue
            git.rm_file(f, cwd, force=False, cached=True)
            console.print(
                f"[green]Untracked {f}[/green] [dim](file kept on disk)[/dim]"
            )
