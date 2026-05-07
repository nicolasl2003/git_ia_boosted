"""
`gb commit` — generates a commit message from the staged diff via AI,
then asks the user to confirm/edit before committing.
"""

import os
import subprocess
import tempfile

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from git_booster.core import git
from git_booster.ai import client as ai, prompts

console = Console()


def _edit_in_editor(message: str) -> str:
    """Open the message in the user's $EDITOR and return the edited content."""
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        f.write(message)
        tmpfile = f.name
    subprocess.run([editor, tmpfile])
    with open(tmpfile, encoding="utf-8") as f:
        result = f.read().strip()
    os.unlink(tmpfile)
    return result


def run(path: str | None = None, no_confirm: bool = False) -> None:
    cwd = path or os.getcwd()

    if not git.is_git_repo(cwd):
        console.print("[red]Not inside a git repository.[/red]")
        return

    # ---- 1. Check there is something staged ---------------------------------
    diff = git.diff_staged(cwd)
    if not diff:
        console.print("[yellow]Nothing staged. Run `gb add` or `git add` first.[/yellow]")
        return

    raw_status = git.status(cwd)

    # ---- 2. Generate message -------------------------------------------------
    with console.status("[bold yellow]Claude is writing the commit message...[/bold yellow]"):
        system, user = prompts.commit_prompt(diff, raw_status)
        message = ai.ask(system, user, max_tokens=256)

    console.print(Panel(message, title="Generated commit message", border_style="green"))

    if no_confirm:
        final_message = message
    else:
        choice = Prompt.ask(
            "[bold]What do you want to do?[/bold]",
            choices=["commit", "edit", "abort"],
            default="commit",
        )

        if choice == "abort":
            console.print("[yellow]Commit aborted.[/yellow]")
            return
        elif choice == "edit":
            final_message = _edit_in_editor(message)
            if not final_message:
                console.print("[red]Empty message — commit aborted.[/red]")
                return
            console.print(Panel(final_message, title="Final commit message", border_style="blue"))
            if not Confirm.ask("Confirm commit with this message?", default=True):
                console.print("[yellow]Commit aborted.[/yellow]")
                return
        else:
            final_message = message

    # ---- 3. Commit -----------------------------------------------------------
    output = git.commit(final_message, cwd)
    console.print(f"[green]{output}[/green]")
