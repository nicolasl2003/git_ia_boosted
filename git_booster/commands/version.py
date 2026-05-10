from rich.console import Console
from rich.text import Text
from rich.panel import Panel
from rich import box

console = Console()

VERSION = "0.1.0"
AUTHOR  = "nicolasl2003 | login42: nilinott"
GITHUB  = "https://github.com/nicolasl2003/git_ia_boosted"

def show_version():
    title = Text()
    title.append("⚡ gai", style="bold cyan")
    title.append("-", style="dim white")
    title.append("booster", style="bold magenta")

    content = Text(justify="center")
    content.append("\nversion ", style="dim white")
    content.append(f"v{VERSION}", style="bold green")
    content.append("\n\n")
    content.append("Local AI-powered Git", style="italic white")
    content.append(" — ", style="dim white")
    content.append("100% private", style="bold cyan")
    content.append(", ", style="dim white")
    content.append("0% cloud", style="bold magenta")
    content.append("\n\n")
    content.append("Provider  ", style="dim white")
    content.append("ollama", style="bold yellow")
    content.append("  │  ", style="dim white")
    content.append("Model  ", style="dim white")
    content.append("llama3.2", style="bold yellow")
    content.append("\n\n")
    content.append("─" * 36, style="dim cyan")
    content.append("\n")
    content.append("Author  ", style="dim white")
    content.append(AUTHOR, style="bold magenta")
    content.append("\n")
    content.append("GitHub  ", style="dim white")
    content.append(GITHUB, style="bold cyan underline")
    content.append("\n")

    panel = Panel(
        content,
        title=title,
        border_style="cyan",
        box=box.DOUBLE_EDGE,
        padding=(0, 4),
        expand=False,
    )

    console.print()
    console.print(panel, justify="center")
    console.print()
