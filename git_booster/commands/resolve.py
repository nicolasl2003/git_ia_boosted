"""
`gai resolve` — full conflict resolution workflow:
  1. Detect existing merge conflicts → AI resolution
  2. If clean: fetch remote → detect if push would be rejected
  3. Propose pull (merge or rebase) → handle post-pull conflicts
"""

import os

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule

from git_booster.core import git
from git_booster.ai import client as ai, prompts

console = Console()


# ── AI conflict resolver ──────────────────────────────────────────────────────

def _resolve_conflict_files(conflict_files: list[str], repo_root: str, cwd: str) -> int:
    """Interactive AI resolution for a list of conflicted files. Returns resolved count."""
    resolved_count = 0
    for filepath in conflict_files:
        console.rule(f"[bold]{filepath}[/bold]")
        content = git.read_conflict_file(filepath, repo_root)

        blocks = sum(
            1 for line in content.splitlines()
            if line.startswith("<<<<<<<")
        )
        console.print(f"[dim]{blocks} conflict block(s)[/dim]")

        if not Confirm.ask(f"Let A.I resolve [bold]{filepath}[/bold]?", default=True):
            console.print(f"[yellow]Skipped {filepath}[/yellow]")
            continue

        with console.status(f"[bold yellow]A.I is processing {filepath}...[/bold yellow]"):
            system, user = prompts.conflict_prompt(filepath, content[:6000])
            resolved = ai.ask(system, user, max_tokens=4096)

        # Preview (first 30 lines)
        preview = "\n".join(resolved.splitlines()[:30])
        if len(resolved.splitlines()) > 30:
            preview += "\n[dim]... (truncated)[/dim]"
        console.print(Panel(preview, title=f"Resolved: {filepath}", border_style="green"))

        if Confirm.ask("Apply this resolution?", default=True):
            git.write_resolved_file(filepath, resolved, repo_root)
            git.mark_resolved(filepath, cwd)
            console.print(f"[green]{filepath} resolved and staged.[/green]")
            resolved_count += 1
        else:
            console.print(f"[yellow]{filepath} not modified.[/yellow]")

    return resolved_count


# ── Push-rejection detection ──────────────────────────────────────────────────

def _handle_push_rejection(cwd: str, branch: str, remote: str) -> None:
    """Fetch remote, check if behind, propose pull strategy."""
    console.print(f"\n[bold cyan]Checking remote {remote}/{branch}...[/bold cyan]")

    ok, err = git.fetch(remote, cwd)
    if not ok:
        console.print(f"[yellow]Could not fetch from {remote}:[/yellow] {err}")
        console.print("[dim]Check your network or remote configuration.[/dim]")
        return

    behind = git.is_behind_remote(branch, remote, cwd)
    ahead  = git.is_ahead_of_remote(branch, remote, cwd)

    if not behind:
        if ahead:
            console.print(f"[green]Remote is up to date. Your push should succeed.[/green]")
        else:
            console.print(f"[green]Branch is in sync with {remote}/{branch}.[/green]")
        return

    console.print(
        f"[bold yellow]Your branch is behind {remote}/{branch}.[/bold yellow]\n"
        f"A push would be rejected — you need to integrate remote changes first."
    )
    console.print()
    console.print("[bold]How do you want to integrate remote changes?[/bold]")
    console.print("  [cyan]1.[/cyan] merge   — git pull (creates a merge commit)")
    console.print("  [cyan]2.[/cyan] rebase  — git pull --rebase (cleaner linear history)")
    console.print("  [cyan]3.[/cyan] abort   — do nothing")

    choice = Prompt.ask("Strategy", choices=["1", "2", "3"], default="2")
    if choice == "3":
        console.print("[yellow]Aborted. Run gai resolve again after manual pull.[/yellow]")
        return

    use_rebase = (choice == "2")
    strategy = "rebase" if use_rebase else "merge"
    console.print(f"\n[bold cyan]Running git pull --{strategy}...[/bold cyan]")

    ok, out = git.pull(remote, branch, rebase=use_rebase, path=cwd)
    console.print(out)

    if ok:
        console.print(f"[green]Pull ({strategy}) succeeded.[/green]")
        # Check if pull introduced conflicts
        if git.has_merge_conflicts(cwd):
            console.print("[bold red]Pull introduced merge conflicts.[/bold red]")
            _resolve_post_pull(cwd, strategy)
        else:
            console.print("[green]No conflicts. You can now push.[/green]")
    else:
        # Pull failed — likely conflicts
        if git.has_merge_conflicts(cwd):
            console.print("[bold red]Conflicts after pull. Launching AI resolution...[/bold red]")
            _resolve_post_pull(cwd, strategy)
        else:
            console.print(f"[red]Pull failed.[/red] {out}")
            _offer_abort(cwd, strategy)


def _resolve_post_pull(cwd: str, strategy: str) -> None:
    """After a pull introduces conflicts, resolve them interactively."""
    repo_root = git.get_repo_root(cwd)
    conflict_files = git.get_conflict_files(cwd)

    console.print(
        f"[bold red]{len(conflict_files)} file(s) with conflicts:[/bold red]"
    )
    for f in conflict_files:
        console.print(f"  [yellow]• {f}[/yellow]")
    console.print()

    resolved = _resolve_conflict_files(conflict_files, repo_root, cwd)

    console.print()
    if resolved == len(conflict_files):
        console.print(f"[bold green]All {resolved} conflict(s) resolved.[/bold green]")
        if strategy == "rebase":
            console.print(
                "Run [bold cyan]git rebase --continue[/bold cyan] then [bold cyan]gai commit[/bold cyan]."
            )
        else:
            console.print("Run [bold cyan]gai commit[/bold cyan] to finalise the merge.")
    elif resolved > 0:
        console.print(
            f"[yellow]{resolved}/{len(conflict_files)} resolved. "
            f"Fix remaining conflicts manually then run gai commit.[/yellow]"
        )
    else:
        console.print("[yellow]No files modified.[/yellow]")
        _offer_abort(cwd, strategy)


def _offer_abort(cwd: str, strategy: str) -> None:
    """Offer to abort an in-progress merge or rebase."""
    op = "rebase" if strategy == "rebase" else "merge"
    in_progress = git.is_rebasing(cwd) if strategy == "rebase" else git.is_merging(cwd)
    if not in_progress:
        return
    if Confirm.ask(f"Abort the {op} and go back to previous state?", default=False):
        if strategy == "rebase":
            ok, msg = git.abort_rebase(cwd)
        else:
            ok, msg = git.abort_merge(cwd)
        if ok:
            console.print(f"[green]{op.capitalize()} aborted. Working tree restored.[/green]")
        else:
            console.print(f"[red]Could not abort {op}:[/red] {msg}")


# ── Main entry point ──────────────────────────────────────────────────────────

def run(path: str | None = None) -> None:
    cwd = path or os.getcwd()

    if not git.is_git_repo(cwd):
        console.print("[red]Not inside a git repository.[/red]")
        return

    # ── Case 1: existing merge conflicts in working tree ─────────────────────
    if git.has_merge_conflicts(cwd):
        repo_root = git.get_repo_root(cwd)
        conflict_files = git.get_conflict_files(cwd)

        console.print(Rule("[bold red]Merge conflicts detected[/bold red]"))
        for f in conflict_files:
            console.print(f"  [yellow]• {f}[/yellow]")
        console.print()

        resolved = _resolve_conflict_files(conflict_files, repo_root, cwd)

        console.print()
        if resolved > 0:
            console.print(
                f"[bold green]{resolved}/{len(conflict_files)} conflict(s) resolved.[/bold green]"
            )
            console.print("Run [bold cyan]gai commit[/bold cyan] to finalise the merge.")
        else:
            console.print("[yellow]No files were modified.[/yellow]")
        return

    # ── Case 2: no local conflicts → check if push would be rejected ─────────
    branch = git.get_branch(cwd)
    remote = git.get_remote(cwd)

    if not remote:
        console.print("[green]No merge conflicts detected.[/green]")
        console.print("[dim]No remote configured — nothing to check.[/dim]")
        return

    _handle_push_rejection(cwd, branch, remote)
