"""
`gai commit` — generates a commit message from the staged diff via AI,
asks the user to validate/modify, then commits and optionally pushes.
"""

import os
import tempfile
import subprocess

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from git_booster.core import git
from git_booster.ai import client as ai, prompts
from git_booster.skills import run_trigger

console = Console()


def _edit_in_editor(message: str) -> str:
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
        f.write(message)
        tmp_path = f.name
    subprocess.run([editor, tmp_path])
    with open(tmp_path) as f:
        edited = f.read().strip()
    os.unlink(tmp_path)
    return edited


def _get_remotes(cwd: str | None) -> list[str]:
    try:
        result = git.run(["remote"], cwd=cwd)
        return [r.strip() for r in result.splitlines() if r.strip()]
    except Exception:
        return []


def run(path: str | None = None, no_confirm: bool = False) -> None:
    cwd = path or os.getcwd()

    diff = git.staged_diff(cwd)
    if not diff:
        console.print("[yellow]No staged changes. Run `gai add` first.[/yellow]")
        return

    raw_status = git.status(cwd)

    run_trigger("pre-commit", cwd=cwd)

    with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
        system, user = prompts.commit_prompt(diff, raw_status)
        message = ai.ask(f"{system}\n\n{user}", cwd=cwd, max_tokens=256)

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
            console.print(
                "[dim]Describe how you want the commit "
                "(e.g. 'focus on the config command', 'use fix type', 'mention ollama migration')[/dim]"
            )
            style_hint = Prompt.ask("[cyan]How should this commit be described?[/cyan]")
            with console.status("[bold yellow]A.I is processing...[/bold yellow]"):
                regen_system, regen_user = prompts.commit_prompt(diff, raw_status, style_hint=style_hint)
                message = ai.ask(f"{regen_system}\n\n{regen_user}", cwd=cwd, max_tokens=128)
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

        else:
            final_message = message
            break

    output = git.commit(final_message, cwd)
    console.print(f"[green]{output}[/green]")

    run_trigger("post-commit", cwd=cwd)

    remotes = _get_remotes(cwd)
    if not remotes:
        return

    if not Confirm.ask("[bold]Push to remote?[/bold]", default=False):
        return

    from git_booster.commands.resolve import attempt_push
    attempt_push(cwd)