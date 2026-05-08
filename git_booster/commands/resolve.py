"""
`gai resolve` — single-pass, fully automatic conflict & push-error resolution.

Workflow
────────
1. Guard: stash uncommitted changes if any (restored at the end)
2. Conflict scan: resolve all conflict files in one AI pass (no loop)
3. If rebasing: git rebase --continue (auto, retrying if needed, max 3 steps)
4. If no conflicts: attempt push with full error recovery
5. Push error dispatch:
     fetch_first / rejected → pull (auto strategy) → re-push
     no_upstream            → set-upstream + push
     refspec                → list remote branches, pick or create
     auth / no_remote       → human-readable instructions
     unknown                → raw error + AI explanation

Anti-loop guard
───────────────
_pull_with_guard() tracks pull attempts per session (max MAX_PULL_ATTEMPTS).
If we keep hitting conflicts after pulls, we abort and leave clear instructions.
"""

import os

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.rule import Rule
from rich.table import Table

from git_booster.core import git
from git_booster.ai import client as ai, prompts

console = Console()

MAX_PULL_ATTEMPTS = 3   # anti-loop: abort after this many pull retries
_pull_attempts   = 0   # module-level counter, reset at run() entry


# ─────────────────────────────────────────────────────────────────────────────
# Stash guard — save/restore uncommitted work
# ─────────────────────────────────────────────────────────────────────────────

class _StashGuard:
    """Context manager: stash before a pull, pop after."""

    def __init__(self, cwd: str):
        self.cwd   = cwd
        self.ref   = None
        self.active = False

    def save(self) -> bool:
        """Stash if there are uncommitted changes. Returns True if stashed."""
        if not git.has_uncommitted_changes(self.cwd):
            return False
        ok, ref = git.stash_push(path=self.cwd)
        if ok:
            self.ref    = ref
            self.active = True
            console.print(f"[dim]Uncommitted changes stashed → {ref}[/dim]")
        else:
            console.print(f"[yellow]Could not stash changes: {ref}[/yellow]")
        return ok

    def restore(self) -> None:
        """Pop stash if we saved one."""
        if not self.active:
            return
        ok, out = git.stash_pop(self.cwd)
        if ok:
            console.print("[dim]Stash restored.[/dim]")
        else:
            console.print(
                f"[yellow]Could not restore stash ({self.ref}).[/yellow]\n"
                f"[dim]Run manually:  git stash pop[/dim]"
            )
        self.active = False


# ─────────────────────────────────────────────────────────────────────────────
# AI conflict resolver — single pass
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_conflict_files(conflict_files: list[str], repo_root: str, cwd: str) -> int:
    """Resolve all conflicted files in a single AI pass. Returns count resolved."""
    resolved_count = 0
    for filepath in conflict_files:
        console.rule(f"[bold]{filepath}[/bold]")
        content = git.read_conflict_file(filepath, repo_root)
        blocks  = sum(1 for l in content.splitlines() if l.startswith("<<<<<<<"))
        console.print(f"[dim]{blocks} conflict block(s)[/dim]")

        if not Confirm.ask(f"Let AI resolve [bold]{filepath}[/bold]?", default=True):
            console.print(f"[yellow]Skipped.[/yellow]")
            continue

        with console.status(f"[bold yellow]AI resolving {filepath}...[/bold yellow]"):
            system, user = prompts.conflict_prompt(filepath, content[:6000])
            resolved = ai.ask(system, user, max_tokens=4096)

        # Strip accidental markdown fences from model output
        lines = resolved.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        resolved = "\n".join(lines)

        preview = "\n".join(resolved.splitlines()[:25])
        if len(resolved.splitlines()) > 25:
            preview += "\n[dim]...[/dim]"
        console.print(Panel(preview, title=f"Resolved: {filepath}", border_style="green"))

        if Confirm.ask("Apply?", default=True):
            git.write_resolved_file(filepath, resolved, repo_root)
            git.mark_resolved(filepath, cwd)
            console.print(f"[green]✓ {filepath} staged.[/green]")
            resolved_count += 1
        else:
            console.print(f"[yellow]Skipped.[/yellow]")

    return resolved_count


# ─────────────────────────────────────────────────────────────────────────────
# Rebase continuation
# ─────────────────────────────────────────────────────────────────────────────

def _continue_rebase(cwd: str, repo_root: str) -> bool:
    """After resolving conflicts in a rebase, continue it (up to 3 steps)."""
    for step in range(1, 4):
        if not git.is_rebasing(cwd):
            return True  # rebase finished
        if git.has_merge_conflicts(cwd):
            # More conflicts appeared in the next patch
            console.print(f"[yellow]New conflicts in rebase step {step}.[/yellow]")
            files = git.get_conflict_files(cwd)
            resolved = _resolve_conflict_files(files, repo_root, cwd)
            if resolved < len(files):
                console.print("[red]Could not resolve all conflicts. Aborting rebase.[/red]")
                git.abort_rebase(cwd)
                return False
        ok, out = git.rebase_continue(cwd)
        if not ok:
            if "nothing to commit" in out.lower():
                ok2, _ = git.rebase_skip(cwd)
                if ok2:
                    continue
            console.print(f"[red]rebase --continue failed:[/red] {out}")
            if Confirm.ask("Abort rebase?", default=True):
                git.abort_rebase(cwd)
            return False
    # Still rebasing after 3 steps
    if git.is_rebasing(cwd):
        console.print("[yellow]Rebase has many steps — run git rebase --continue manually.[/yellow]")
        return False
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Strategy auto-detection
# ─────────────────────────────────────────────────────────────────────────────

def _detect_best_strategy(cwd: str, remote: str, branch: str) -> tuple[str, str]:
    """Return (strategy, reason) — 'rebase' or 'merge'."""
    if not git.has_merge_commits(cwd, n=20):
        return "rebase", "linear history"
    if git.count_local_commits(branch, remote, cwd) <= 1:
        return "rebase", "single local commit"
    return "merge", "non-linear history"


# ─────────────────────────────────────────────────────────────────────────────
# Pull with anti-loop guard
# ─────────────────────────────────────────────────────────────────────────────

def _pull_with_guard(cwd: str, remote: str, branch: str, auto: bool = False) -> bool:
    """Pull, resolve any post-pull conflicts, return True on clean success.
    Aborts with an error message if MAX_PULL_ATTEMPTS exceeded."""
    global _pull_attempts
    _pull_attempts += 1

    if _pull_attempts > MAX_PULL_ATTEMPTS:
        console.print(
            f"[bold red]Infinite-loop guard:[/bold red] {MAX_PULL_ATTEMPTS} pull attempts "
            "without clean result. Stopping.\n"
            "[dim]Fix conflicts manually, then: git rebase --continue / git commit[/dim]"
        )
        return False

    strategy, reason = _detect_best_strategy(cwd, remote, branch)

    if auto:
        use_rebase = (strategy == "rebase")
        console.print(
            f"[bold cyan]→ git pull --{'rebase' if use_rebase else 'merge'} "
            f"{remote} {branch}[/bold cyan]  [dim]({reason})[/dim]"
        )
    else:
        other = "merge" if strategy == "rebase" else "rebase"
        console.print(
            f"\n[bold]Recommended:[/bold] [cyan]{strategy}[/cyan]  [dim]({reason})[/dim]\n"
            f"  [cyan]1.[/cyan] {strategy:<8} [dim](recommended)[/dim]\n"
            f"  [cyan]2.[/cyan] {other}\n"
            f"  [cyan]q.[/cyan] abort"
        )
        choice = Prompt.ask("Strategy", choices=["1", "2", "q", "Q"], default="1")
        if choice.lower() == "q":
            console.print("[yellow]Pull aborted.[/yellow]")
            return False
        use_rebase = (
            (choice == "1" and strategy == "rebase") or
            (choice == "2" and strategy == "merge")
        )

    stash = _StashGuard(cwd)
    stash.save()

    try:
        label = "rebase" if use_rebase else "merge"
        ok, out = git.pull(remote, branch, rebase=use_rebase, path=cwd)
        if out:
            console.print(f"[dim]{out[:400]}[/dim]")

        if ok:
            console.print("[green]Pull succeeded.[/green]")
            if git.has_merge_conflicts(cwd):
                console.print("[bold red]Pull introduced conflicts.[/bold red]")
                return _resolve_after_pull(cwd, label)
            return True
        else:
            if git.has_merge_conflicts(cwd):
                console.print("[bold red]Conflicts after pull.[/bold red]")
                return _resolve_after_pull(cwd, label)
            console.print(f"[red]Pull failed.[/red]")
            _offer_abort(cwd, label)
            return False
    finally:
        stash.restore()


def _resolve_after_pull(cwd: str, strategy: str) -> bool:
    """Resolve conflicts left by a pull, then finalise the operation."""
    repo_root      = git.get_repo_root(cwd)
    conflict_files = git.get_conflict_files(cwd)

    console.print(f"[bold red]{len(conflict_files)} conflict(s):[/bold red]")
    for f in conflict_files:
        console.print(f"  [yellow]• {f}[/yellow]")
    console.print()

    resolved = _resolve_conflict_files(conflict_files, repo_root, cwd)

    if resolved < len(conflict_files):
        remaining = len(conflict_files) - resolved
        console.print(f"[yellow]{remaining} file(s) not resolved — fix manually.[/yellow]")
        _offer_abort(cwd, strategy)
        return False

    console.print(f"[bold green]All {resolved} conflict(s) resolved.[/bold green]")

    if strategy == "rebase" and git.is_rebasing(cwd):
        return _continue_rebase(cwd, repo_root)

    return True


def _offer_abort(cwd: str, strategy: str) -> None:
    op = "rebase" if strategy == "rebase" else "merge"
    in_progress = git.is_rebasing(cwd) if op == "rebase" else git.is_merging(cwd)
    if not in_progress:
        return
    if Confirm.ask(f"Abort the {op} and restore previous state?", default=False):
        ok, msg = git.abort_rebase(cwd) if op == "rebase" else git.abort_merge(cwd)
        console.print(
            f"[green]{op.capitalize()} aborted.[/green]" if ok
            else f"[red]Could not abort {op}:[/red] {msg}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Push error handlers
# ─────────────────────────────────────────────────────────────────────────────

def _handle_fetch_first(cwd: str, remote: str, branch: str, err: str) -> bool:
    console.print(
        "[bold yellow]Push rejected:[/bold yellow] remote has commits you don't have.\n"
        "Pulling and integrating remote changes…"
    )
    if not Confirm.ask("Pull now?", default=True):
        return False
    if not _pull_with_guard(cwd, remote, branch, auto=False):
        return False
    console.print("[bold cyan]→ Retrying push…[/bold cyan]")
    ok, out = git.push(remote, branch, path=cwd)
    if ok:
        console.print("[bold green]✓ Push succeeded.[/bold green]")
        return True
    return _handle_push_error(cwd, remote, branch, out, retry=False)


def _handle_no_upstream(cwd: str, remote: str, branch: str, err: str) -> bool:
    console.print(
        f"[bold yellow]No upstream:[/bold yellow] branch [cyan]{branch}[/cyan] "
        f"is not tracked on [cyan]{remote}[/cyan]."
    )
    if not Confirm.ask(f"Set upstream → {remote}/{branch} and push?", default=True):
        return False
    console.print(f"[bold cyan]→ git push --set-upstream {remote} {branch}[/bold cyan]")
    ok, out = git.set_upstream(remote, branch, path=cwd)
    if ok:
        console.print("[bold green]✓ Push succeeded.[/bold green]")
        return True
    console.print(f"[red]Failed:[/red] {out}")
    return False


def _handle_refspec(cwd: str, remote: str, branch: str, err: str) -> bool:
    console.print(
        f"[bold yellow]Bad refspec:[/bold yellow] [cyan]{branch}[/cyan] "
        "has no matching ref on the remote."
    )
    remote_branches = git.list_remote_branches(remote, cwd)
    if remote_branches:
        t = Table(show_header=False, box=None, padding=(0, 1))
        t.add_column("#", style="cyan", width=4)
        t.add_column()
        for i, b in enumerate(remote_branches, 1):
            t.add_row(str(i), b)
        console.print(t)
        choices = [str(i) for i in range(1, len(remote_branches) + 1)] + ["n", "N", "q", "Q"]
        console.print(f"  [cyan]n.[/cyan] Create new branch {branch} on remote   [cyan]q.[/cyan] Abort")
        pick = Prompt.ask("Push to", choices=choices, default="n")
    else:
        pick = "n"

    if pick.lower() == "q":
        return False
    if pick.lower() == "n":
        ok, out = git.set_upstream(remote, branch, path=cwd)
    else:
        target = remote_branches[int(pick) - 1]
        if not Confirm.ask(f"Push {branch} → {remote}/{target}?", default=True):
            return False
        result = git._run(["git", "push", remote, f"{branch}:{target}"], cwd=cwd, check=False)
        ok  = result.returncode == 0
        out = (result.stdout + result.stderr).strip()

    if ok:
        console.print("[bold green]✓ Push succeeded.[/bold green]")
        return True
    console.print(f"[red]Failed:[/red] {out}")
    return False


def _handle_auth(cwd: str, remote: str, branch: str, err: str) -> bool:
    r = git._run(["git", "remote", "get-url", remote], cwd=cwd, check=False)
    url = r.stdout.strip() if r.returncode == 0 else "unknown"
    console.print(Panel(
        f"[bold red]Authentication failed[/bold red]\n\n"
        f"Remote: [cyan]{remote}[/cyan] → {url}\n\n"
        "Fixes:\n"
        "  SSH  : ssh-add ~/.ssh/id_rsa\n"
        "  HTTPS: use a personal access token (not your password)\n"
        f"\n[dim]{err[:250]}[/dim]",
        title="Push — Auth error", border_style="red",
    ))
    return False


def _handle_no_remote(cwd: str, remote: str, branch: str, err: str) -> bool:
    console.print(Panel(
        f"[bold red]Remote unreachable[/bold red]\n\n"
        f"Remote: [cyan]{remote}[/cyan]\n\n"
        "Fixes:\n"
        "  git remote -v              (check URL)\n"
        "  git remote add origin URL  (add missing remote)\n"
        f"\n[dim]{err[:250]}[/dim]",
        title="Push — Remote error", border_style="red",
    ))
    return False


def _handle_unknown(cwd: str, remote: str, branch: str, err: str) -> bool:
    console.print(Panel(err[:500], title="[red]Push error[/red]", border_style="red"))
    if not Confirm.ask("Ask AI to analyse?", default=True):
        return False
    with console.status("[bold yellow]AI analysing…[/bold yellow]"):
        explanation = ai.ask(
            "You are a git expert. In 3-5 lines explain the error and give exact fix commands. Plain text only.",
            f"Remote: {remote}\nBranch: {branch}\n\nError:\n{err[:1200]}",
            max_tokens=250,
        )
    console.print(Panel(explanation, title="AI analysis", border_style="cyan"))
    return False


# ─────────────────────────────────────────────────────────────────────────────
# Push error dispatcher
# ─────────────────────────────────────────────────────────────────────────────

_HANDLERS = {
    git.PUSH_ERR_FETCH_FIRST: _handle_fetch_first,
    git.PUSH_ERR_REJECTED:    _handle_fetch_first,
    git.PUSH_ERR_NO_UPSTREAM: _handle_no_upstream,
    git.PUSH_ERR_REFSPEC:     _handle_refspec,
    git.PUSH_ERR_AUTH:        _handle_auth,
    git.PUSH_ERR_NO_REMOTE:   _handle_no_remote,
    git.PUSH_ERR_UNKNOWN:     _handle_unknown,
}

_ERR_LABELS = {
    git.PUSH_ERR_FETCH_FIRST: "remote ahead",
    git.PUSH_ERR_REJECTED:    "non-fast-forward",
    git.PUSH_ERR_NO_UPSTREAM: "no upstream",
    git.PUSH_ERR_REFSPEC:     "bad refspec",
    git.PUSH_ERR_AUTH:        "auth failure",
    git.PUSH_ERR_NO_REMOTE:   "remote not found",
    git.PUSH_ERR_UNKNOWN:     "unknown",
}


def _handle_push_error(cwd: str, remote: str, branch: str, err: str, retry: bool = True) -> bool:
    etype = git.parse_push_error(err)
    console.print(f"\n[bold red]Push failed[/bold red]  [dim]({_ERR_LABELS.get(etype, etype)})[/dim]")
    return _HANDLERS.get(etype, _handle_unknown)(cwd, remote, branch, err)


# ─────────────────────────────────────────────────────────────────────────────
# Public: attempt push with full error recovery
# ─────────────────────────────────────────────────────────────────────────────

def attempt_push(cwd: str) -> bool:
    """Push current branch. On failure, diagnose and auto-fix. Returns True on success."""
    remote = git.get_remote(cwd)
    if not remote:
        console.print("[yellow]No remote configured — skipping push.[/yellow]")
        return False
    branch = git.get_branch(cwd)
    console.print(f"[bold cyan]→ git push {remote} {branch}[/bold cyan]")
    ok, out = git.push(remote, branch, path=cwd)
    if ok:
        console.print("[bold green]✓ Push succeeded.[/bold green]")
        return True
    return _handle_push_error(cwd, remote, branch, out)


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def run(path: str | None = None) -> None:
    global _pull_attempts
    _pull_attempts = 0   # reset anti-loop counter on each run()

    cwd = path or os.getcwd()

    if not git.is_git_repo(cwd):
        console.print("[red]Not inside a git repository.[/red]")
        return

    repo_root = git.get_repo_root(cwd)
    remote    = git.get_remote(cwd)
    branch    = git.get_branch(cwd)

    # ── Case 1: in-progress rebase with unresolved conflicts ─────────────────
    if git.is_rebasing(cwd) and git.has_merge_conflicts(cwd):
        console.print(Rule("[bold red]Rebase conflicts[/bold red]"))
        files    = git.get_conflict_files(cwd)
        resolved = _resolve_conflict_files(files, repo_root, cwd)
        if resolved == len(files):
            console.print(f"[bold green]All {resolved} conflict(s) resolved.[/bold green]")
            if _continue_rebase(cwd, repo_root):
                console.print("[green]Rebase complete.[/green]")
                if remote and Confirm.ask("Push now?", default=True):
                    attempt_push(cwd)
        else:
            console.print(f"[yellow]{resolved}/{len(files)} resolved. Fix remaining manually.[/yellow]")
        return

    # ── Case 2: merge conflicts in working tree ───────────────────────────────
    if git.has_merge_conflicts(cwd):
        console.print(Rule("[bold red]Merge conflicts[/bold red]"))
        files = git.get_conflict_files(cwd)
        for f in files:
            console.print(f"  [yellow]• {f}[/yellow]")
        console.print()

        resolved = _resolve_conflict_files(files, repo_root, cwd)
        console.print()
        if resolved == len(files):
            console.print(f"[bold green]All {resolved} conflict(s) resolved.[/bold green]")
            console.print("Run [bold cyan]gai commit[/bold cyan] to finalise.")
        else:
            console.print(f"[yellow]{resolved}/{len(files)} resolved. Fix remaining manually.[/yellow]")
        return

    # ── Case 3: clean working tree → push ────────────────────────────────────
    if not remote:
        console.print("[green]Working tree clean, no remote configured.[/green]")
        return

    console.print(Rule(f"[bold]Push[/bold] — [cyan]{branch}[/cyan] → [cyan]{remote}[/cyan]"))
    attempt_push(cwd)
