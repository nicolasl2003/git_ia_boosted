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
        if name and name not in ("main", "master", "develop"):
            result.append(name)
    return result

def _ai_branch_name(description: str, branch_type: str, ticket: str | None) -> str:
    try:
        from git_booster.ai.client import ask
        ticket_part = f"ticket: {ticket}" if ticket else "no ticket"
        prompt = (
            f"Generate a short git branch name.\n"
            f"Type: {branch_type}\n"
            f"Ticket: {ticket_part}\n"
            f"Description: {description}\n\n"
            f"Rules:\n"
            f"- Format: {branch_type}/{'<ticket>-' if ticket else ''}<short-slug>\n"
            f"- Use kebab-case\n"
            f"- Max 50 characters\n"
            f"- No special characters except hyphens and slashes\n"
            f"- Output ONLY the branch name, nothing else"
        )
        name = ask(prompt).strip().strip("`").strip()
        name = re.sub(r"[^a-zA-Z0-9/_-]", "-", name)
        name = re.sub(r"-+", "-", name).strip("-")
        return name
    except Exception:
        slug = re.sub(r"[^a-z0-9]+", "-", description.lower()).strip("-")[:40]
        prefix = f"{ticket}-" if ticket else ""
        return f"{branch_type}/{prefix}{slug}"

# ─── commands ─────────────────────────────────────────────────────────────────

def _cmd_help() -> None:
    console.print(Panel("[bold cyan]gai branch — help[/bold cyan]", expand=False))

    table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 2))
    table.add_column("Command", style="cyan", no_wrap=True)
    table.add_column("Aliases", style="dim")
    table.add_column("Description")

    table.add_row("gai branch", "", "Interactive menu")
    table.add_row("gai branch create", "new", "AI-generated branch name from your description")
    table.add_row("gai branch list", "ls", "List all local and remote branches")
    table.add_row("gai branch switch", "checkout, sw", "Interactive branch switcher")
    table.add_row("gai branch merge", "mg", "Merge a branch into another")
    table.add_row("gai branch rm <name>", "delete, remove", "Delete a branch locally (and optionally on remote)")
    table.add_row("gai branch clean", "prune", "Delete all merged branches")
    table.add_row("gai branch --help", "-h, help", "Show this help")

    console.print(table)

    console.print("\n[bold]Branch types available during create:[/bold]")
    console.print("  " + "  ".join(f"[cyan]{t}[/cyan]" for t in BRANCH_TYPES))

    console.print("\n[bold]Examples:[/bold]")
    console.print("  [dim]$[/dim] gai branch create")
    console.print("  [dim]$[/dim] gai branch switch")
    console.print("  [dim]$[/dim] gai branch merge")
    console.print("  [dim]$[/dim] gai branch rm fix/old-feature")
    console.print("  [dim]$[/dim] gai branch clean")

def _cmd_create(cwd: str) -> None:
    console.print(Panel("[bold cyan]Create a new branch[/bold cyan]", expand=False))

    console.print(f"Branch type [{'/'.join(BRANCH_TYPES)}]")
    branch_type = Prompt.ask("Type", default="feat")

    ticket = Prompt.ask("Ticket / issue number ", default="")
    if ticket.lower() in ("", "n", "none", "-"):
        ticket = None

    description = Prompt.ask("Describe your feature/fix")

    console.print("[dim]A.I is generating branch name...[/dim]")
    suggested = _ai_branch_name(description, branch_type, ticket)

    _, existing_raw, _ = _run(["git", "branch"], cwd)
    existing = [l.strip().lstrip("* ") for l in existing_raw.splitlines()]

    prefix = suggested.split("/")[0] if "/" in suggested else None
    if prefix and prefix in existing:
        console.print(f"[yellow]⚠ A branch named '{prefix}' already exists — cannot create '{suggested}'.[/yellow]")
        console.print("[dim]Git cannot create a branch whose prefix matches an existing branch name.[/dim]")
        suggested = Prompt.ask("Enter a different branch name", default=f"{branch_type}-{suggested.split('/', 1)[-1]}")

    console.print(f"\nSuggested branch name: [bold cyan]{suggested}[/bold cyan]")
    choice = Prompt.ask("Use this name?", choices=["yes", "edit", "abort"], default="yes")

    if choice == "abort":
        console.print("[yellow]Aborted.[/yellow]")
        return
    if choice == "edit":
        suggested = Prompt.ask("Branch name", default=suggested)

    stashed = False
    if _has_uncommitted(cwd):
        console.print("[yellow]⚠ Uncommitted changes detected.[/yellow]")
        if Confirm.ask("Stash changes before creating branch?", default=True):
            if _stash(cwd):
                console.print("[green]✓ Changes stashed.[/green]")
                stashed = True

    code, _, err = _run(["git", "checkout", "-b", suggested], cwd)
    if code == 0:
        console.print(f"[green]✓ Branch '{suggested}' created and checked out.[/green]")
    else:
        console.print(f"[red]Failed to create branch: {err}[/red]")

    if stashed:
        if _stash_pop(cwd):
            console.print("[green]✓ Stash restored.[/green]")
        else:
            console.print("[yellow]⚠ Run: git stash pop[/yellow]")

    if _has_remote(cwd) and code == 0:
        if Confirm.ask(f"Push '{suggested}' to remote?", default=True):
            code2, _, err2 = _run(["git", "push", "--set-upstream", "origin", suggested], cwd)
            if code2 == 0:
                console.print(f"[green]✓ Pushed to origin/{suggested}.[/green]")
            else:
                console.print(f"[yellow]Push failed: {err2}[/yellow]")

def _cmd_list(cwd: str) -> None:
    console.print(Panel("[bold cyan]Branches[/bold cyan]", expand=False))
    branches = _all_branches(cwd)

    table = Table(show_header=True, header_style="bold magenta", box=None, padding=(0, 2))
    table.add_column("", width=2)
    table.add_column("Branch", style="cyan")
    table.add_column("Last commit", style="dim")
    table.add_column("Author", style="dim")
    table.add_column("Remote", style="dim")

    for b in branches:
        marker = "[green]●[/green]" if b["current"] else " "
        remote_tag = "[blue]remote[/blue]" if b["remote"] else ""
        table.add_row(marker, b["name"], b["date"], b["author"], remote_tag)

    console.print(table)
    console.print(f"\n[dim]{len(branches)} branch(es) total[/dim]")

def _cmd_switch(cwd: str) -> None:
    console.print(Panel("[bold cyan]Switch branch[/bold cyan]", expand=False))
    branches = _all_branches(cwd)
    local = [b for b in branches if not b["remote"]]

    if not local:
        console.print("[yellow]No local branches found.[/yellow]")
        return

    for i, b in enumerate(local, 1):
        marker = "[green]●[/green]" if b["current"] else " "
        console.print(f"  {marker} [cyan]{i}.[/cyan] {b['name']}  [dim]{b['date']}[/dim]")

    choice = Prompt.ask("\nBranch number", default="1")
    try:
        idx = int(choice) - 1
        target = local[idx]["name"]
    except (ValueError, IndexError):
        console.print("[red]Invalid choice.[/red]")
        return

    if local[idx]["current"]:
        console.print(f"[yellow]Already on '{target}'.[/yellow]")
        return

    stashed = False
    if _has_uncommitted(cwd):
        console.print("[yellow]⚠ Uncommitted changes detected.[/yellow]")
        if Confirm.ask("Stash changes before switching?", default=True):
            if _stash(cwd):
                console.print("[green]✓ Changes stashed.[/green]")
                stashed = True

    code, _, err = _run(["git", "checkout", target], cwd)
    if code == 0:
        console.print(f"[green]✓ Switched to '{target}'.[/green]")
    else:
        console.print(f"[red]Failed to switch: {err}[/red]")

    if stashed:
        if _stash_pop(cwd):
            console.print("[green]✓ Stash restored.[/green]")
        else:
            console.print("[yellow]⚠ Run: git stash pop[/yellow]")

def _cmd_merge(cwd: str) -> None:
    """Merge a source branch into a target branch."""
    console.print(Panel("[bold cyan]Merge branches[/bold cyan]", expand=False))

    branches = _all_branches(cwd)
    local = [b for b in branches if not b["remote"]]
    current = _current_branch(cwd)

    if len(local) < 2:
        console.print("[yellow]You need at least 2 local branches to merge.[/yellow]")
        return

    # ── Pick source branch ────────────────────────────────────────────────
    console.print("\n[bold]Source branch[/bold] (branch to merge FROM):")
    for i, b in enumerate(local, 1):
        marker = "[green]●[/green]" if b["current"] else " "
        console.print(f"  {marker} [cyan]{i}.[/cyan] {b['name']}  [dim]{b['date']}[/dim]")

    src_choice = Prompt.ask("\nSource branch number", default="1")
    try:
        src = local[int(src_choice) - 1]["name"]
    except (ValueError, IndexError):
        console.print("[red]Invalid choice.[/red]")
        return

    # ── Pick target branch ────────────────────────────────────────────────
    console.print(f"\n[bold]Target branch[/bold] (branch to merge INTO) — current: [cyan]{current}[/cyan]:")
    targets = [b for b in local if b["name"] != src]
    for i, b in enumerate(targets, 1):
        marker = "[green]●[/green]" if b["current"] else " "
        console.print(f"  {marker} [cyan]{i}.[/cyan] {b['name']}  [dim]{b['date']}[/dim]")

    tgt_choice = Prompt.ask("\nTarget branch number", default="1")
    try:
        tgt = targets[int(tgt_choice) - 1]["name"]
    except (ValueError, IndexError):
        console.print("[red]Invalid choice.[/red]")
        return

    console.print(f"\n[yellow]Will merge[/yellow] [bold cyan]{src}[/bold cyan] [yellow]→[/yellow] [bold cyan]{tgt}[/bold cyan]")
    if not Confirm.ask("Proceed?", default=True):
        console.print("[yellow]Aborted.[/yellow]")
        return

    # ── Stash if needed ───────────────────────────────────────────────────
    stashed = False
    if _has_uncommitted(cwd):
        console.print("[yellow]⚠ Uncommitted changes detected.[/yellow]")
        if Confirm.ask("Stash changes before merging?", default=True):
            if _stash(cwd):
                console.print("[green]✓ Changes stashed.[/green]")
                stashed = True
        else:
            console.print("[yellow]Aborted — commit or stash your changes first.[/yellow]")
            return

    # ── Switch to target ──────────────────────────────────────────────────
    if current != tgt:
        code, _, err = _run(["git", "checkout", tgt], cwd)
        if code != 0:
            console.print(f"[red]Failed to switch to '{tgt}': {err}[/red]")
            if stashed:
                _stash_pop(cwd)
            return
        console.print(f"[green]✓ Switched to '{tgt}'.[/green]")

    # ── Merge ─────────────────────────────────────────────────────────────
    console.print(f"[dim]→ git merge {src}[/dim]")
    code, out, err = _run(["git", "merge", src], cwd)

    if code == 0:
        console.print(f"[green]✓ Merge successful.[/green]")
        if out:
            console.print(f"[dim]{out}[/dim]")
    else:
        console.print(f"[red]✗ Merge failed — conflicts detected.[/red]")
        console.print(f"[dim]{err}[/dim]")
        console.print("\n[yellow]Tip:[/yellow] run [bold]gai resolve[/bold] to let AI fix the conflicts.")
        if stashed:
            console.print("[yellow]⚠ Your stash is still saved — run: git stash pop[/yellow]")
        return

    # ── Restore stash ─────────────────────────────────────────────────────
    if stashed:
        if _stash_pop(cwd):
            console.print("[green]✓ Stash restored.[/green]")
        else:
            console.print("[yellow]⚠ Run: git stash pop[/yellow]")

    # ── Push ──────────────────────────────────────────────────────────────
    if _has_remote(cwd):
        if Confirm.ask(f"Push '{tgt}' to remote?", default=True):
            code2, _, err2 = _run(["git", "push", "origin", tgt], cwd)
            if code2 == 0:
                console.print(f"[green]✓ Pushed origin/{tgt}.[/green]")
            else:
                console.print(f"[yellow]Push failed: {err2}[/yellow]")
                console.print("[yellow]Tip:[/yellow] run [bold]gai resolve[/bold] to fix push errors.")

def _cmd_rm(cwd: str, args: list[str]) -> None:
    console.print(Panel("[bold cyan]Delete a branch[/bold cyan]", expand=False))

    if args:
        target = args[0]
    else:
        branches = _all_branches(cwd)
        local = [b for b in branches if not b["remote"]]

        deletable = [b for b in local if not b["current"]]
        if not deletable:
            console.print("[yellow]No branches available to delete (can't delete current branch).[/yellow]")
            return

        for i, b in enumerate(deletable, 1):
            console.print(f"  [cyan]{i}.[/cyan] {b['name']}  [dim]{b['date']}[/dim]")

        choice = Prompt.ask("\nBranch number to delete", default="1")
        try:
            idx = int(choice) - 1
            target = deletable[idx]["name"]
        except (ValueError, IndexError):
            console.print("[red]Invalid choice.[/red]")
            return

    current = _current_branch(cwd)
    if target == current:
        console.print(f"[red]✗ Cannot delete '{target}' — it is the current branch.[/red]")
        console.print("[dim]Switch to another branch first: gai branch switch[/dim]")
        return

    console.print(f"\n[yellow]Branch to delete:[/yellow] [bold]{target}[/bold]")
    if not Confirm.ask("Delete this branch locally?", default=False):
        console.print("[yellow]Aborted.[/yellow]")
        return

    code, _, err = _run(["git", "branch", "-d", target], cwd)
    if code != 0 and "not fully merged" in err:
        console.print(f"[yellow]⚠ Branch '{target}' is not fully merged.[/yellow]")
        if Confirm.ask("Force delete anyway?", default=False):
            code, _, err = _run(["git", "branch", "-D", target], cwd)
        else:
            console.print("[yellow]Aborted.[/yellow]")
            return

    if code == 0:
        console.print(f"[green]✓ Local branch '{target}' deleted.[/green]")
    else:
        console.print(f"[red]Failed to delete branch: {err}[/red]")
        return

    if _has_remote(cwd):
        _, remote_branches, _ = _run(["git", "branch", "-r"], cwd)
        on_remote = any(target in line for line in remote_branches.splitlines())
        if on_remote:
            if Confirm.ask(f"Also delete 'origin/{target}' on remote?", default=False):
                code2, _, err2 = _run(["git", "push", "origin", "--delete", target], cwd)
                if code2 == 0:
                    console.print(f"[green]✓ Remote branch 'origin/{target}' deleted.[/green]")
                else:
                    console.print(f"[yellow]Remote delete failed: {err2}[/yellow]")

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
            code, _, err = _run(["git", "push", "origin", "--delete", branch], cwd)
            if code == 0:
                console.print(f"[green]✓ Deleted remote:[/green] origin/{branch}")
            else:
                console.print(f"[yellow]  Remote delete failed for {branch}[/yellow]")

    console.print(f"\n[bold green]Done — {deleted} branch(es) cleaned.[/bold green]")

def run_branch(args: list[str]) -> None:
    cwd = _project_dir()

    if args and args[0] in ("--help", "-h", "help"):
        _cmd_help()
        return

    if not args:
        console.print(Panel("[bold cyan]gai branch[/bold cyan]", expand=False))
        console.print("  [cyan]1.[/cyan] Create a new branch")
        console.print("  [cyan]2.[/cyan] List all branches")
        console.print("  [cyan]3.[/cyan] Switch branch")
        console.print("  [cyan]4.[/cyan] Merge two branches")
        console.print("  [cyan]5.[/cyan] Delete a branch")
        console.print("  [cyan]6.[/cyan] Clean merged branches")
        choice = Prompt.ask("\nChoice", default="1")
        if choice == "1":
            _cmd_create(cwd)
        elif choice == "2":
            _cmd_list(cwd)
        elif choice == "3":
            _cmd_switch(cwd)
        elif choice == "4":
            _cmd_merge(cwd)
        elif choice == "5":
            _cmd_rm(cwd, [])
        elif choice == "6":
            _cmd_clean(cwd)
        return

    sub = args[0].lower()
    if sub in ("create", "new"):
        _cmd_create(cwd)
    elif sub in ("list", "ls"):
        _cmd_list(cwd)
    elif sub in ("switch", "checkout", "sw"):
        _cmd_switch(cwd)
    elif sub in ("merge", "mg"):
        _cmd_merge(cwd)
    elif sub in ("rm", "delete", "remove"):
        _cmd_rm(cwd, args[1:])
    elif sub in ("clean", "prune"):
        _cmd_clean(cwd)
    else:
        console.print(f"[red]Unknown subcommand: {sub}[/red]")
        console.print("[dim]Tip: run 'gai branch --help' to see all commands.[/dim]")
