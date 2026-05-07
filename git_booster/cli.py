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
@click.option("--path", "-p", default=None, help="Repository path (default: cwd)")
def cmd_add(path):
    """Stage all changes (git add .) and generate/update .gitignore via AI."""
    from git_booster.commands import add
    try:
        add.run(path)
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
def cmd_review(path):
    """AI code review of staged (or unstaged) changes."""
    from git_booster.commands import review
    try:
        review.run(path)
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
# gai skills
# ---------------------------------------------------------------------------

@main.command("skills")
def cmd_skills_list():
    """List available AI skills."""
    from git_booster.skills import list_skills
    skills = list_skills()
    if not skills:
        console.print("[yellow]No skills installed.[/yellow]")
        return
    t = Table(show_header=True, header_style="bold cyan")
    t.add_column("Skill")
    t.add_column("Description")
    for name, mod in sorted(skills.items()):
        t.add_row(name, getattr(mod, "DESCRIPTION", "—"))
    console.print(t)


# ---------------------------------------------------------------------------
# gai skill <name> [args...]
# ---------------------------------------------------------------------------

@main.command("skill")
@click.argument("name")
@click.argument("args", nargs=-1)
@click.option("--path", "-p", default=None, help="Repository path (default: cwd)")
def cmd_skill_run(name, args, path):
    """Run an AI skill by name. Example: gai skill explain main.py"""
    from git_booster.skills import get_skill
    skill = get_skill(name)
    if skill is None:
        console.print(f"[red]Unknown skill:[/red] {name}  (run [bold]gai skills[/bold] to list available)")
        raise SystemExit(1)
    try:
        skill.run(list(args), path=path)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
