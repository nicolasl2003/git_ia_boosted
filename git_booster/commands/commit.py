"""
`gai commit` — generates a commit message from the staged diff via AI,
asks the user to validate/modify, then commits and optionally pushes.
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
    """Open the message in $EDITOR and return the edited content."""
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


def _get_remotes(cwd: str) -> list[str]:
    """Return list of configured git remotes."""
    try:
        result = subprocess.run(
            ["git", "remote"],
            cwd=cwd, capture_output=True, text=True
        )
        return [r for r in result.stdout.splitlines() if r.strip()]
    except Exception:
        return []


def _push(remote: str, branch: str, cwd: str) -> None:
    """Push to a remote and display result."""
    with console.status(f"[bold cyan]Pushing to {remote}/{branch}...[/bold cyan]"):
        result = subprocess.run(
            ["git", "push", remote, branch],
            cwd=cwd, capture_output=True, text=True
        )
    if result.returncode == 0:
        console.print(f"[green]Pushed to {remote}/{branch}.[/green]")
    else:
        console.print(f"[red]Push failed:[/red] {result.stderr.strip()}")


def run(path: str | None = None, no_confirm: bool = False) -> None:
    cwd = path or os.getcwd()

    if not git.is_git_repo(cwd):
        console.print("[red]Not inside a git repository.[/red]")
        return

    # ---- 1. Check there is something staged ---------------------------------
    diff = git.diff_staged(cwd)
    if not diff:
        unstaged = git.diff_unstaged(cwd)
        untracked = git.list_untracked_files(cwd)
        if unstaged or untracked:
            console.print(
                "[bold red]Nothing staged.[/bold red] You have unstaged changes.\n"
                "Run [bold cyan]gai add[/bold cyan] or [bold cyan]git add .[/bold cyan] first, then retry."
            )
        else:
            console.print(
                "[bold yellow]Nothing to commit.[/bold yellow] "
                "Working tree is clean."
            )
        return

    raw_status = git.status(cwd)

    # ---- 2. Generate message -------------------------------------------------
    with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
        system, user = prompts.commit_prompt(diff, raw_status)
        message = ai.ask(system, user, max_tokens=256)

    # ---- 3. Validate / modify loop ------------------------------------------
    while True:
        console.print(Panel(message, title="Generated commit message", border_style="green"))

        if no_confirm:
            final_message = message
            break

        choice = Prompt.ask(
            "[bold]What do you want to do?[/bold]",
            choices=["commit", "edit", "regenerate", "abort"],
            default="commit",
        )

        if choice == "abort":
            console.print("[yellow]Commit aborted.[/yellow]")
            return

        elif choice == "regenerate":
            feedback = Prompt.ask("[cyan]What should be different in the message?[/cyan]")
            with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
                regen_system, regen_user = prompts.commit_prompt(diff, raw_status)
                regen_user += f"\n\nUser feedback: {feedback}\nRewrite the message accordingly."
                message = ai.ask(regen_system, regen_user, max_tokens=256)
            continue

        elif choice == "edit":
            edited = _edit_in_editor(message)
            if not edited:
                console.print("[red]Empty message — commit aborted.[/red]")
                return
            console.print(Panel(edited, title="Final commit message", border_style="blue"))
            if not Confirm.ask("Confirm commit with this message?", default=True):
                console.print("[yellow]Commit aborted.[/yellow]")
                return
            final_message = edited
            break

        else:  # commit
            final_message = message
            break

    # ---- 4. Commit -----------------------------------------------------------
    output = git.commit(final_message, cwd)
    console.print(f"[green]{output}[/green]")

    # ---- 5. Push (optional) --------------------------------------------------
    remotes = _get_remotes(cwd)
    if not remotes:
        return

    if not Confirm.ask("[bold]Push to remote?[/bold]", default=False):
        return

    branch = git.get_branch(cwd)

    if len(remotes) == 1:
        _push(remotes[0], branch, cwd)
    else:
        console.print("[bold]Available remotes:[/bold]")
        for i, r in enumerate(remotes, 1):
            console.print(f"  [cyan]{i}.[/cyan] {r}")
        console.print(f"  [cyan]{len(remotes) + 1}.[/cyan] all")

        choices = [str(i) for i in range(1, len(remotes) + 2)]
        pick = Prompt.ask("Push to which remote?", choices=choices, default="1")
        idx = int(pick) - 1

        if idx == len(remotes):
            for r in remotes:
                _push(r, branch, cwd)
        else:
            _push(remotes[idx], branch, cwd)
