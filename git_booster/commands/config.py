"""
`gai config` — interactive terminal configuration (provider, model, Ollama setup).
Writes settings to ~/.config/git-booster/config.env
"""

import os
import subprocess
import urllib.request
import urllib.error
import json
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.rule import Rule

console = Console()

CONFIG_DIR  = Path.home() / ".config" / "git-booster"
CONFIG_FILE = CONFIG_DIR / "config.env"

PROVIDERS = {
    "1": ("ollama",    "Local Ollama (no API key, recommended)"),
    "2": ("anthropic", "Anthropic Claude (API key required)"),
    "3": ("openai",    "OpenAI (API key required)"),
}

OLLAMA_MODELS = {
    "1": ("qwen2.5-coder:3b",  "Best for code — GTX 1050 Ti (4GB) ~2GB VRAM"),
    "2": ("qwen2.5-coder:1.5b","Lightest — GTX 1050 2GB / CPU only"),
    "3": ("llama3.2:3b",       "General purpose — 4GB VRAM"),
    "4": ("mistral:7b",        "Powerful — needs 8GB+ VRAM"),
}


def _read_config() -> dict:
    """Read current config from file."""
    cfg = {}
    if CONFIG_FILE.exists():
        for line in CONFIG_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip()
    return cfg


def _write_config(cfg: dict) -> None:
    """Write config dict to file."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    lines = ["# git-booster configuration — auto-generated", ""]
    for k, v in cfg.items():
        lines.append(f"{k}={v}")
    CONFIG_FILE.write_text("\n".join(lines) + "\n")


def _show_current(cfg: dict) -> None:
    """Display current configuration."""
    t = Table(show_header=False, box=None, padding=(0, 2))
    t.add_column(style="cyan")
    t.add_column(style="white")
    t.add_row("Provider",    cfg.get("GAI_PROVIDER", "ollama"))
    t.add_row("Model",       cfg.get("GAI_MODEL",    "llama3.2"))
    t.add_row("Ollama host", cfg.get("OLLAMA_HOST",  "http://localhost:11434"))
    api_key = cfg.get("ANTHROPIC_API_KEY") or cfg.get("OPENAI_API_KEY")
    if api_key:
        t.add_row("API key", api_key[:8] + "..." + api_key[-4:])
    console.print(Panel(t, title="Current configuration", border_style="cyan"))


def _ollama_running(host: str) -> bool:
    try:
        urllib.request.urlopen(f"{host}/api/tags", timeout=3)
        return True
    except Exception:
        return False


def _ollama_installed_models(host: str) -> list[str]:
    try:
        with urllib.request.urlopen(f"{host}/api/tags", timeout=5) as r:
            data = json.loads(r.read())
            return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def _pull_ollama_model(model: str) -> None:
    console.print(f"[bold cyan]Pulling {model}...[/bold cyan] (this may take a few minutes)")
    result = subprocess.run(["ollama", "pull", model])
    if result.returncode == 0:
        console.print(f"[green]{model} ready.[/green]")
    else:
        console.print(f"[red]Failed to pull {model}.[/red]")


def _configure_ollama(cfg: dict) -> dict | None:
    """Interactive Ollama configuration. Returns None if user quits."""
    console.print(Rule("[bold]Ollama configuration[/bold]"))

    # Host
    current_host = cfg.get("OLLAMA_HOST", "http://localhost:11434")
    host = Prompt.ask("Ollama host (q to cancel)", default=current_host)
    if host.lower() == "q":
        return None
    cfg["OLLAMA_HOST"] = host

    # Check if running
    if _ollama_running(host):
        console.print(f"[green]Ollama is reachable at {host}[/green]")
        installed = _ollama_installed_models(host)
        if installed:
            console.print("[dim]Installed models: " + ", ".join(installed) + "[/dim]")
    else:
        console.print(f"[yellow]Ollama not reachable at {host}[/yellow]")
        if Confirm.ask("Start Ollama now?", default=True):
            subprocess.Popen(["ollama", "serve"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            console.print("[dim]Ollama starting... wait a moment then retry.[/dim]")

    # Model selection
    console.print()
    console.print("[bold]Select a model:[/bold]")
    for k, (name, desc) in OLLAMA_MODELS.items():
        console.print(f"  [cyan]{k}.[/cyan] {name:<25} {desc}")
    console.print(f"  [cyan]5.[/cyan] Enter custom model name")
    console.print(f"  [cyan]q.[/cyan] Cancel")

    pick = Prompt.ask("Model", choices=["1","2","3","4","5","q","Q"], default="1")
    if pick.lower() == "q":
        return None
    if pick == "5":
        model = Prompt.ask("Custom model name (e.g. qwen2.5-coder:7b)")
        if not model.strip():
            return None
    else:
        model, _ = OLLAMA_MODELS[pick]

    cfg["GAI_MODEL"]    = model
    cfg["GAI_PROVIDER"] = "ollama"

    # Pull if not installed
    installed = _ollama_installed_models(host)
    if model not in installed:
        if Confirm.ask(f"[bold]{model}[/bold] not found locally. Pull it now?", default=True):
            _pull_ollama_model(model)
    else:
        console.print(f"[green]{model} already installed.[/green]")

    return cfg


def _configure_anthropic(cfg: dict) -> dict | None:
    console.print(Rule("[bold]Anthropic configuration[/bold]"))
    key = Prompt.ask("Anthropic API key (sk-ant-..., q to cancel)", password=False)
    if key.lower() == "q":
        return None
    model = Prompt.ask("Model", default="claude-3-5-haiku-20241022")
    cfg["ANTHROPIC_API_KEY"] = key
    cfg["GAI_MODEL"]         = model
    cfg["GAI_PROVIDER"]      = "anthropic"
    return cfg


def _configure_openai(cfg: dict) -> dict | None:
    console.print(Rule("[bold]OpenAI / OpenRouter configuration[/bold]"))
    key = Prompt.ask("API key (sk-..., q to cancel)", password=False)
    if key.lower() == "q":
        return None
    base_url = Prompt.ask(
        "Base URL (Enter = OpenAI, or paste OpenRouter URL)",
        default="https://api.openai.com/v1",
    )
    model = Prompt.ask("Model", default="gpt-4o-mini")
    cfg["OPENAI_API_KEY"]  = key
    cfg["OPENAI_BASE_URL"] = base_url
    cfg["GAI_MODEL"]       = model
    cfg["GAI_PROVIDER"]    = "openai"
    return cfg


def run() -> None:
    console.print(Rule("[bold cyan]git-booster — configuration[/bold cyan]"))

    cfg = _read_config()
    _show_current(cfg)
    console.print()

    # Show active provider/model
    active_provider = cfg.get("GAI_PROVIDER", "ollama")
    active_model    = cfg.get("GAI_MODEL", "llama3.2")
    console.print(
        f"[dim]Active: [cyan]{active_provider}[/cyan] / [cyan]{active_model}[/cyan][/dim]\n"
    )

    # Provider selection
    console.print("[bold]Select AI provider:[/bold]")
    for k, (name, desc) in PROVIDERS.items():
        marker = " [green](active)[/green]" if name == active_provider else ""
        console.print(f"  [cyan]{k}.[/cyan] {name:<12} {desc}{marker}")
    console.print("  [cyan]q.[/cyan] quit        Exit without changes")

    pick = Prompt.ask("Provider", choices=["1", "2", "3", "q", "Q"], default="1")

    if pick.lower() == "q":
        console.print("[yellow]Configuration unchanged. Exiting.[/yellow]")
        return

    provider_name = PROVIDERS[pick][0]

    if provider_name == "ollama":
        result = _configure_ollama(cfg)
    elif provider_name == "anthropic":
        result = _configure_anthropic(cfg)
    elif provider_name == "openai":
        result = _configure_openai(cfg)
    else:
        result = None

    if result is None:
        console.print("[yellow]Configuration unchanged. Exiting.[/yellow]")
        return

    cfg = result
    # Save
    _write_config(cfg)
    console.print()
    console.print(f"[green]Configuration saved to {CONFIG_FILE}[/green]")
    console.print(
        f"[dim]To apply permanently, add to your ~/.zshrc:\n"
        f"  source {CONFIG_FILE}[/dim]"
    )
    _show_current(cfg)
