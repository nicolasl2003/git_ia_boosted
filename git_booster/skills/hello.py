"""
Skill: hello — minimal working example skill.
Usage: gai skill hello
       gai skill hello <name>

This skill serves as a template and smoke-test.
Copy this file to create your own skill.
"""

from rich.console import Console
from rich.panel import Panel

NAME        = "hello"
DESCRIPTION = "Hello world — example skill and template for custom skills"

console = Console()


def run(args: list[str], path: str | None = None) -> None:
    name = args[0] if args else "world"
    console.print(Panel(
        f"[bold green]Hello, {name}![/bold green]\n\n"
        "[dim]This is the 'hello' skill — a working example.\n"
        f"Skill path: {__file__}[/dim]",
        title="gai skill hello",
        border_style="green",
    ))
