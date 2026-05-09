"""
git-booster CLI entry point.
Usage: gai <command> [options]
"""

import click
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option(package_name="git-booster")
def main():
    """git-booster — AI-powered Git wrapper using Ollama (local LLM)."""
    pass


# ---------------------------------------------------------------------------
# gai add
# ---------------------------------------------------------------------------

@main.command("add")
@click.argument("files", nargs=-1, required=False)
@click.option("--path", "-p", default=None, help="Repository path (default: cwd)")
def cmd_add(files, path):
    """Stage all changes (or specific files) and manage .gitignore via AI.

    Examples:
      gai add              # stage everything
      gai add file1.py     # stage specific file
      gai add src/ tests/  # stage directories
    """
    from git_booster.commands import add
    try:
        add.run(list(files) if files else None, path)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# gai status  (native, no AI)
# ---------------------------------------------------------------------------

@main.command("status")
@click.option("--path", "-p", default=None, help="Repository path (default: cwd)")
def cmd_status(path):
    """Show git status (native, instant — no AI)."""
    from git_booster.commands import status
    try:
        status.run(path)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# gai commit
# ---------------------------------------------------------------------------

@main.command("commit")
@click.option("--path", "-p", default=None, help="Repository path (default: cwd)")
@click.option("--yes", "-y", is_flag=True, default=False, help="Commit without confirmation prompt")
def cmd_commit(path, yes):
    """Generate a commit message from staged diff, validate, commit and push."""
    from git_booster.commands import commit
    try:
        commit.run(path, no_confirm=yes)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# gai resolve
# ---------------------------------------------------------------------------

@main.command("resolve")
@click.option("--path", "-p", default=None, help="Repository path (default: cwd)")
def cmd_resolve(path):
    """Detect and resolve merge conflicts using AI."""
    from git_booster.commands import resolve
    try:
        resolve.run(path)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# gai review
# ---------------------------------------------------------------------------

@main.command("review")
@click.option("--path", "-p", default=None, help="Repository path (default: cwd)")
@click.option("--commit", "-c", default=None, metavar="REF",
              help="Review a specific commit (e.g. HEAD~1, abc1234)")
def cmd_review(path, commit):
    """AI code review of staged changes, or a specific commit.

    \b
    Examples:
      gai review                # review staged changes
      gai review --commit HEAD~1
      gai review -c abc1234
    """
    from git_booster.commands import review
    try:
        review.run(path, commit_ref=commit)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)



# ---------------------------------------------------------------------------
# gai rm
# ---------------------------------------------------------------------------

@main.command("rm")
@click.argument("files", nargs=-1, required=True)
@click.option("--hard", is_flag=True, default=False, help="Untrack AND delete file from disk")
@click.option("--path", "-p", default=None, help="Repository path (default: cwd)")
def cmd_rm(files, hard, path):
    """Remove file(s) from git tracking. Use --hard to also delete from disk."""
    from git_booster.commands import rm
    try:
        rm.run(list(files), hard=hard, path=path)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# gai stop
# ---------------------------------------------------------------------------

@main.command("stop")
def cmd_stop():
    """Stop the Ollama background server and free resources."""
    from git_booster.commands import stop
    try:
        stop.run()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# gai config
# ---------------------------------------------------------------------------

@main.command("config")
def cmd_config():
    """Interactive configuration: AI provider, Ollama model, API keys."""
    from git_booster.commands import config
    try:
        config.run()
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# gai skills [list]
# ---------------------------------------------------------------------------

@main.command("skills")
@click.argument("subcommand", required=False, default="list")
@click.option("--trigger", "-t", default=None, help="Filter by trigger (manual, pre-commit, post-push…)")
def cmd_skills(subcommand, trigger):
    """List available skills.

    \b
    Usage:
      gai skills              # list all skills
      gai skills list         # same
      gai skills list -t pre-commit   # filter by trigger
    """
    if subcommand not in ("list",):
        console.print(f"[red]Unknown subcommand:[/red] {subcommand}  (available: list)")
        raise SystemExit(1)

    from git_booster.skills import all_skills
    skills = all_skills(trigger=trigger)

    if not skills:
        msg = f"No skills with trigger '{trigger}'." if trigger else "No skills installed."
        console.print(f"[yellow]{msg}[/yellow]")
        console.print(
            "[dim]Add skills in: ~/.config/git-booster/skills/\n"
            "Formats: .py or .yaml[/dim]"
        )
        return

    t = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    t.add_column("Name",    style="cyan")
    t.add_column("Trigger", style="dim")
    t.add_column("Source",  style="dim")
    t.add_column("Description")
    for skill in sorted(skills, key=lambda s: s["name"]):
        t.add_row(
            skill["name"],
            skill.get("trigger", "manual"),
            skill.get("_type", "—"),
            skill.get("description") or "—",
        )

    console.print(t)
    console.print(
        f"\n[dim]User skills dir: ~/.config/git-booster/skills/   "
        f"Formats: .py  .yaml[/dim]"
    )


# ---------------------------------------------------------------------------
# gai skill <name> [args...]
# ---------------------------------------------------------------------------

@main.command("skill")
@click.argument("name")
@click.argument("args", nargs=-1)
@click.option("--path", "-p", default=None, help="Repository path (default: cwd)")
def cmd_skill_run(name, args, path):
    """Run a skill by name.

    \b
    Examples:
      gai skill explain main.py
      gai skill hello
      gai skill deploy
    """
    from git_booster.skills import get_skill
    skill = get_skill(name)
    if skill is None:
        console.print(
            f"[red]Unknown skill:[/red] {name}\n"
            "Run [bold]gai skills[/bold] to see available skills."
        )
        raise SystemExit(1)
    try:
        skill.run(list(args), path=path)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)
    
# ---------------------------------------------------------------------------
# gai update
# ---------------------------------------------------------------------------

from git_booster.commands import update as update_cmd

@main.command()
def update():
    """Pull latest changes and reinstall git-booster."""
    update_cmd.run()

# ---------------------------------------------------------------------------
# gai branch
# ---------------------------------------------------------------------------

from git_booster.commands.branch import run_branch

@main.command("branch")
@click.argument("args", nargs=-1)
def branch_cmd(args):
    """Smart branch management."""
    run_branch(list(args))


if __name__ == "__main__":
    main()
