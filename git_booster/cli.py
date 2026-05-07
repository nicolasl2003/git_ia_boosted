"""
git-booster CLI entry point.
Usage: gb <command> [options]
"""

import click
from rich.console import Console

console = Console()


@click.group()
@click.version_option(package_name="git-booster")
def main():
    """git-booster — AI-powered Git wrapper using Ollama (local LLM)."""
    pass


# ---------------------------------------------------------------------------
# gb add
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
# gb status
# ---------------------------------------------------------------------------

@main.command("status")
@click.option("--path", "-p", default=None, help="Repository path (default: cwd)")
def cmd_status(path):
    """Show git status with an AI-generated summary."""
    from git_booster.commands import status
    try:
        status.run(path)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# gb commit
# ---------------------------------------------------------------------------

@main.command("commit")
@click.option("--path", "-p", default=None, help="Repository path (default: cwd)")
@click.option("--yes", "-y", is_flag=True, default=False, help="Commit without confirmation prompt")
def cmd_commit(path, yes):
    """Generate a commit message from staged diff and commit."""
    from git_booster.commands import commit
    try:
        commit.run(path, no_confirm=yes)
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# gb resolve
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
# gb review
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


if __name__ == "__main__":
    main()
