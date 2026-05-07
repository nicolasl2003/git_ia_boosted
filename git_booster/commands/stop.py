"""
`gai stop` — stop the Ollama background server and free resources.
"""

import subprocess
from rich.console import Console

console = Console()


def run() -> None:
    # Try pkill first (works on Linux/macOS)
    result = subprocess.run(
        ["pkill", "-f", "ollama serve"],
        capture_output=True
    )
    if result.returncode == 0:
        console.print("[green]Ollama server stopped.[/green]")
        return

    # Fallback: killall
    result2 = subprocess.run(
        ["killall", "ollama"],
        capture_output=True
    )
    if result2.returncode == 0:
        console.print("[green]Ollama server stopped.[/green]")
    else:
        console.print("[yellow]Ollama server was not running.[/yellow]")
