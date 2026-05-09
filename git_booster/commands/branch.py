"""
`gai branch` — Smart branch management with AI-generated names.
"""

import subprocess
import re
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

console = Console()

BRANCH_TYPES = ["feat", "fix", "hotfix", "refactor", "chore", "docs", "test", "release"]

def _run(cmd: list[str], cwd: str | None = None) -> tuple[int, str, str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()

def _project_dir() -> str:
    code, out, _ = _run(["git", "rev-parse", "--show-toplevel"])
    return out if code == 0 else "."

def _current_branch(cwd: str) -> str:
    _, out, _ = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd)
    return out or "main"

def _has_remote(cwd: str) -> bool:
    _, out, _ = _run(["git", "remote"], cwd)
    return bool(out.strip())

def _has_uncommitted(cwd: str) -> bool:
    _, out, _ = _run(["git", "status", "--porcelain"], cwd)
    return bool(out.strip())

def _stash(cwd: str) -> bool:
    code, _, _ = _run(["git", "stash", "push", "-m", "gai-branch-auto-stash"], cwd)
    return code == 0

def _stash_pop(cwd: str) -> bool:
    code, _, _ = _run(["git", "stash", "pop"], cwd)
    return code == 0

def _all_branches(cwd: str) -> list[dict]:
    _, out, _ = _run([
        "git", "branch", "-a", "--format",
        "%(refname:short)|%(committerdate:short)|%(authorname)|%(HEAD)"
    ], cwd)
    branches = []
    seen = set()
    for line in out.splitlines():
        parts = line.split("|")
        if len(parts) < 4:
            continue
        name, date, author, head = parts[0], parts[1], parts[2], parts[3]
        is_remote = name.startswith("remotes/")
        clean_name = name.replace("remotes/", "").strip()
        if "HEAD" in clean_name:
            continue
        if clean_name in seen:
            continue
        seen.add(clean_name)
        branches.append({
            "name": clean_name,
            "remote": is_remote,
            "date": date,
            "author": author,
            "current": head == "*",
        })
    return branches

def _merged_branches(cwd: str) -> list[str]:
    _, out, _ = _run(["git", "branch", "--merged"], cwd)
    result = []
    for line in out.splitlines():
        name = line.strip().lstrip("* ")
        if name and name not in ("main", "master", "dev", "develop"):
            result.append(name)
    return result

def _slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[àáâã]", "a", text)
    text = re.sub(r"[éèêë]", "e", text)
    text = re.sub(r"[îï]", "i", text)
    text = re.sub(r"[ôö]", "o", text)
    text = re.sub(r"[ùûü]", "u", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s_]+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:50]

def _ai_branch_name(description: str, branch_type: str, ticket: str | None) -> str:
    try:
        from git_booster.ai.client import ask
        system = (
            "You are a git branch naming assistant. "
            "Return ONLY the branch name, nothing else. No explanation, no backticks."
        )
        user = (
            f"Generate a git branch name for: '{description}'\n"
            f"Type prefix: {branch_type}\n"
            f"Rules:\n"
            f"- lowercase, hyphens only\n"
            f"- max 5 words after prefix\n"
            f"- no special characters\n"
            f"- format: {branch_type}/<short-name>\n"
        )
        name = ask(system=system, user=user).strip().strip("`").split("\n")[0]
        name = re.sub(r"[^a-z0-9/_-]", "", name.lower())
        if not name.startswith(branch_type + "/"):
            slug = _slugify(description)
            name = f"{branch_type}/{slug}"
    except Exception as e:
        console.print(f"[yellow]⚠ AI unavailable ({e}), using slug.[/yellow]")
        slug = _slugify(description)
        name = f"{branch_type}/{slug}"

    if ticket:
        parts = name.split("/", 1)
        if len(parts) == 2:
            name = f"{parts[0]}/{ticket}-{parts[1]}"
        else:
            name = f"{name}-{ticket}"

    return name

def _check_branch_conflict(branch_name: str, cwd: str) -> str | None:
    """
    Returns a safe branch name, resolving conflicts where a prefix
    matches an existing branch (e.g. 'fix' exists, can't create 'fix/foo').
    """
    _, out, _ = _run(["git", "branch"], cwd)
    existing = [l.strip().lstrip("* ") for l in out.splitlines() if l.strip()]

    prefix = branch_name.split("/")[0] if "/" in branch_name else None
    if prefix and prefix in existing:
        console.print(
            f"[yellow]⚠ A branch named '[bold]{prefix}[/bold]' already exists.[/yellow]\n"
            f"[dim]Git cannot create '{branch_name}' because '{prefix}' is already a branch ref.[/dim]"
        )
        suffix = branch_name.split("/", 1)[-1]
        fallback = f"{prefix}-{suffix}"
        branch_name = Prompt.ask("Enter a different branch name", default=fallback)

    return branch_name

def _cmd_create(cwd: str) -> None:
    console.print(Panel("[bold cyan]Create a new branch[/bold cyan]", expand=False))

    branch_type = Prompt.ask(
        "Branch type",
        choices=BRANCH_TYPES,
        default="feat",
    )

    ticket = Prompt.ask("Ticket / issue number [optional]", default="")
    ticket = ticket.strip() or None

    description = Prompt.ask("Describe your feature/fix")

    console.print("[dim]A.I is generating branch name...[/dim]")
    branch_name = _ai_branch_name(description, branch_type, ticket)

    # Fix: detect prefix conflict before proposing the name
    branch_name = _check_branch_conflict(branch_name, cwd)

    console.print(f"\n[bold]Suggested branch name:[/bold] [green]{branch_name}[/green]")
    confirmed = Prompt.ask("Use this name?", choices=["yes", "edit", "abort"], default="yes")

    if confirmed == "abort":
        console.print("[yellow]Aborted.[/yellow]")
        return
    if confirmed == "edit":
        branch_name = Prompt.ask("Enter branch name", default=branch_name)
        # Re-check after manual edit
        branch_name = _check_branch_conflict(branch_name, cwd)

    stashed = False
    if _has_uncommitted(cwd):
        console.print("[yellow]⚠ Uncommitted changes detected.[/yellow]")
        if Confirm.ask("Stash changes before creating branch?", default=True):
            if _stash(cwd):
                console.print("[green]✓ Changes stashed.[/green]")
                stashed = True

    code, _, err = _run(["git", "checkout", "-b", branch_name], cwd)
    if code == 0:
        console.print(f"[green]✓ Branch created and switched to: {branch_name}[/green]")
        if _has_remote(cwd):
            if Confirm.ask("Push branch to remote?", default=True):
                _run(["git", "push", "--set-upstream", "origin", branch_name], cwd)
                console.print(f"[green]✓ Pushed to origin/{branch_name}[/green]")
    else:
        console.print(f"[red]Failed to create branch: {err}[/red]")

    if stashed:
        if _stash_pop(cwd):
            console.print("[green]✓ Stash restored.[/green]")
        else:
            console.print("[yellow]⚠ Run: git stash pop[/yellow]")

def _cmd_list(cwd: str) -> None:
    console.print(Panel("[bold cyan]All branches[/bold cyan]", expand=False))
    branches = _all_branches(cwd)
    current = _current_branch(cwd)

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("", width=2)
    table.add_column("Branch")
    table.add_column("Date")
    table.add_column("Author")
    table.add_column("Remote")

    for b in branches:
        marker = "[green]●[/green]" if b["name"] == current else ""
        remote_tag = "[dim]remote[/dim]" if b["remote"] else ""
        table.add_row(marker, b["name"], b["date"], b["author"], remote_tag)

    console.print(table)

def _cmd_switch(cwd: str) -> None:
    console.print(Panel("[bold cyan]Switch branch[/bold cyan]", expand=False))
    branches = _all_branches(cwd)
    current = _current_branch(cwd)
    stashed = False

    if _has_uncommitted(cwd):
        console.print("[yellow]⚠ Uncommitted changes detected.[/yellow]")
        if Confirm.ask("Stash changes before switching?", default=True):
            if _stash(cwd):
                console.print("[green]✓ Changes stashed.[/green]")
                stashed = True

    console.print()
    for i, b in enumerate(branches, 1):
        marker = "[green]●[/green]" if b["name"] == current else " "
        console.print(f"  {marker} [cyan]{i}.[/cyan] {b['name']}  [dim]{b['date']}[/dim]")

    choice = Prompt.ask("\nBranch number or name")
    target = None

    if choice.isdigit() and 1 <= int(choice) <= len(branches):
        target = branches[int(choice) - 1]["name"]
    else:
        target = choice.strip()

    if target == current:
        console.print(f"[yellow]Already on '{target}'.[/yellow]")
        if stashed:
            _stash_pop(cwd)
        return

    code, _, err = _run(["git", "checkout", target], cwd)
    if code == 0:
        console.print(f"[green]✓ Switched to '{target}'.[/green]")
    else:
        console.print(f"[red]Failed: {err}[/red]")

    if stashed:
        if _stash_pop(cwd):
            console.print("[green]✓ Stash restored.[/green]")
        else:
            console.print("[yellow]⚠ Run: git stash pop[/yellow]")

def _cmd_clean(cwd: str) -> None:
    console.print(Panel("[bold cyan]Clean merged branches[/bold cyan]", expand=False))

    merged = _merged_branches(cwd)
    if not merged:
        console.print("[green]No merged branches to clean.[/green]")
        return

    console.print("[dim]Merged branches:[/dim]")
    for b in merged:
        console.print(f"  [yellow]•[/yellow] {b}")

    console.print()
    delete_local = Confirm.ask("Delete local merged branches?", default=True)
    delete_remote = False
    if _has_remote(cwd):
        delete_remote = Confirm.ask("Delete remote merged branches too?", default=False)

    deleted = 0
    for branch in merged:
        if delete_local:
            code, _, err = _run(["git", "branch", "-d", branch], cwd)
            if code == 0:
                console.print(f"[green]✓ Deleted local:[/green] {branch}")
                deleted += 1
            else:
                console.print(f"[yellow]  Could not delete {branch}: {err}[/yellow]")

        if delete_remote:
            code, _, err = _run(
                ["git", "push", "origin", "--delete", branch], cwd
            )
            if code == 0:
                console.print(f"[green]✓ Deleted remote:[/green] origin/{branch}")
            else:
                console.print(f"[yellow]  Remote delete failed for {branch}[/yellow]")

    console.print(f"\n[bold green]Done — {deleted} branch(es) cleaned.[/bold green]")

def run_branch(args: list[str]) -> None:
    cwd = _project_dir()

    if not args:
        console.print(Panel("[bold cyan]gai branch[/bold cyan]", expand=False))
        console.print("  [cyan]1.[/cyan] Create a new branch")
        console.print("  [cyan]2.[/cyan] List all branches")
        console.print("  [cyan]3.[/cyan] Switch branch")
        console.print("  [cyan]4.[/cyan] Clean merged branches")
        choice = Prompt.ask("\nChoice", default="1")
        if choice == "1":
            _cmd_create(cwd)
        elif choice == "2":
            _cmd_list(cwd)
        elif choice == "3":
            _cmd_switch(cwd)
        elif choice == "4":
            _cmd_clean(cwd)
        return

    sub = args[0].lower()
    if sub in ("create", "new"):
        _cmd_create(cwd)
    elif sub in ("list", "ls"):
        _cmd_list(cwd)
    elif sub in ("switch", "checkout", "sw"):
        _cmd_switch(cwd)
    elif sub in ("clean", "prune"):
        _cmd_clean(cwd)
    else:
        console.print(f"[red]Unknown subcommand: {sub}[/red]")
        console.print("[dim]Usage: gai branch [create|list|switch|clean][/dim]")
