"""
Multi-provider AI client for git-booster.

Priority: env vars > ~/.config/git-booster/config.env > defaults

Providers:  ollama (default) | anthropic | openai
Config:     run `gai config` to set provider/model/keys
"""

import os
import sys
import json
import time
import shutil
import platform
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional

# ── Config ────────────────────────────────────────────────────────────────────

_CONFIG_FILE = Path.home() / ".config" / "git-booster" / "config.env"
MAX_TOKENS   = 4096

def _load_config() -> dict[str, str]:
    """Load config.env then overlay env vars (env vars always win)."""
    cfg: dict[str, str] = {}
    if _CONFIG_FILE.exists():
        for line in _CONFIG_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                cfg[k.strip()] = v.strip()
    for key in ("GAI_PROVIDER", "GAI_MODEL", "OLLAMA_HOST",
                "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENAI_BASE_URL"):
        if key in os.environ:
            cfg[key] = os.environ[key]
    return cfg

<<<<<<< Updated upstream
def _cfg(key: str, default: str = "") -> str:
    return _load_config().get(key, default)

def _default_model(provider: str) -> str:
    return {
        "ollama":    "llama3.2",
        "anthropic": "claude-3-5-haiku-20241022",
        "openai":    "gpt-4o-mini",
    }.get(provider, "llama3.2")

# ── Ollama auto-start ─────────────────────────────────────────────────────────

def _get_ollama_path() -> Optional[str]:
    """Find ollama binary depending on the OS."""
    system = platform.system()

    if system == "Darwin":
        candidates = [
            "/opt/homebrew/bin/ollama",
            "/usr/local/bin/ollama",
            shutil.which("ollama"),
        ]
    elif system == "Linux":
        candidates = [
            "/usr/bin/ollama",
            "/usr/local/bin/ollama",
            shutil.which("ollama"),
        ]
    else:
        candidates = [shutil.which("ollama")]

    for path in candidates:
        if path and Path(path).exists():
            return path
    return None

def _ollama_is_running(host: str) -> bool:
=======
from rich.console import Console

console = Console()

# ---------------------------------------------------------------------------
# defaults
# ---------------------------------------------------------------------------

DEFAULT_TIMEOUT = 60
MAX_RETRIES     = 2
RETRY_DELAY     = 2

# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def ask(
    prompt: str,
    cwd: str | None = None,
    timeout: int | None = None,
    max_tokens: int | None = None,
    system: str | None = None,
    model: str | None = None,
) -> str:
    """
    Send a prompt to the configured AI provider.
    Retries MAX_RETRIES times, then returns a safe fallback string.
    """
    cfg      = _load_config()
    provider = cfg["provider"]
    timeout  = timeout or int(cfg.get("timeout", DEFAULT_TIMEOUT))

    if model:
        cfg["model"] = model

    if system:
        prompt = f"{system}\n\n{prompt}"

    if cwd:
        ctx = _load_project_context(cwd)
        if ctx:
            prompt = f"{ctx}\n\n{prompt}"

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            if provider == "ollama":
                return _ask_ollama(prompt, cfg, timeout)
            elif provider == "anthropic":
                return _ask_anthropic(prompt, cfg, timeout)
            elif provider == "openai":
                return _ask_openai(prompt, cfg, timeout)
            else:
                raise ValueError(f"Unknown provider: {provider!r}")

        except _TimeoutError as e:
            last_error = e
            console.print(f"[yellow]⚠ AI timeout (attempt {attempt}/{MAX_RETRIES + 1})[/yellow]")

        except _ProviderUnavailableError as e:
            last_error = e
            console.print(f"[yellow]⚠ Provider unavailable (attempt {attempt}/{MAX_RETRIES + 1}): {e}[/yellow]")

        except Exception as e:
            last_error = e
            console.print(f"[yellow]⚠ AI error (attempt {attempt}/{MAX_RETRIES + 1}): {e}[/yellow]")

        if attempt <= MAX_RETRIES:
            time.sleep(RETRY_DELAY)

    console.print("[red]✗ AI unavailable after all retries.[/red] Using fallback response.")
    return _fallback(prompt, last_error)

# ---------------------------------------------------------------------------
# provider implementations
# ---------------------------------------------------------------------------

def _ask_ollama(prompt: str, cfg: dict, timeout: int) -> str:
    import httpx

    host  = cfg.get("ollama_host", "http://localhost:11434")
    model = cfg.get("model", "llama3.2")

>>>>>>> Stashed changes
    try:
        urllib.request.urlopen(f"{host}", timeout=2)
        return True
    except Exception:
        return False

def _start_ollama_if_needed() -> None:
    """Start Ollama in the background if it is not already running."""
    host = _cfg("OLLAMA_HOST", "http://localhost:11434").rstrip("/")

    if _ollama_is_running(host):
        return

    ollama_path = _get_ollama_path()

    if not ollama_path:
        system = platform.system()
        hint = (
            "brew install ollama"
            if system == "Darwin"
            else "curl -fsSL https://ollama.com/install.sh | sh"
        )
<<<<<<< Updated upstream
        raise RuntimeError(
            f"Cannot reach Ollama at {host} and ollama binary not found.\n"
            f"Install it with:  {hint}"
        )
=======

    api_key = cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise _ProviderUnavailableError("ANTHROPIC_API_KEY not set")

    model = cfg.get("model", "claude-3-haiku-20240307")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        )
        return response.content[0].text.strip()
>>>>>>> Stashed changes

    print("🚀 Starting Ollama in the background...")
    subprocess.Popen(
        [ollama_path, "serve"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    for _ in range(10):
        time.sleep(1)
        if _ollama_is_running(host):
            print("✓ Ollama ready.")
            return

    print("⚠️  Ollama is slow to start, continuing anyway...")

# ── pre-ai context injection ──────────────────────────────────────────────────

def _collect_pre_ai_context(cwd: Optional[str] = None) -> str:
    """
    Run all skills with trigger=pre-ai and collect their context output.
    Returns a string to append to the system prompt (empty if none).
    """
    try:
        from git_booster.skills import get_skills
    except ImportError:
        return ""

    parts = []
    for skill in get_skills():
        if skill.get("trigger") != "pre-ai":
            continue
        try:
            if skill["_type"] == "python" and callable(skill.get("context")):
                result = skill["context"](path=cwd)
                if result and result.strip():
                    parts.append(result.strip())
            elif skill["_type"] == "yaml" and skill.get("context_cmd"):
                import subprocess as sp
                result = sp.check_output(
                    skill["context_cmd"],
                    shell=True,
                    cwd=cwd,
                    text=True,
                    stderr=sp.DEVNULL,
                )
                if result and result.strip():
                    parts.append(result.strip())
        except Exception as e:
            print(f"⚠️  pre-ai skill '{skill.get('name')}' failed: {e}")

    return "\n\n".join(parts)

# ── Ollama ────────────────────────────────────────────────────────────────────

def _ask_ollama(system: str, user: str, model: str, max_tokens: int) -> str:
    _start_ollama_if_needed()

    host = _cfg("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    payload = json.dumps({
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "stream": False,
        "options": {"num_predict": max_tokens},
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{host}/api/chat", data=payload,
        headers={"Content-Type": "application/json"}, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["message"]["content"].strip()
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Cannot reach Ollama at {host}.\n"
            "Start it with:  ollama serve\n"
            f"Details: {e}"
        )
    except KeyError:
        raise RuntimeError(f"Unexpected Ollama response: {data}")

# ── Anthropic ─────────────────────────────────────────────────────────────────

def _ask_anthropic(system: str, user: str, model: str, max_tokens: int) -> str:
    api_key = _cfg("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set. Run: gai config")
    payload = json.dumps({
        "model": model, "max_tokens": max_tokens,
        "system": system,
        "messages": [{"role": "user", "content": user}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        }, method="POST",
    )
    try:
<<<<<<< Updated upstream
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["content"][0]["text"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Anthropic error {e.code}: {body}")
    except KeyError:
        raise RuntimeError(f"Unexpected Anthropic response: {data}")

# ── OpenAI-compatible ─────────────────────────────────────────────────────────

def _ask_openai(system: str, user: str, model: str, max_tokens: int) -> str:
    api_key  = _cfg("OPENAI_API_KEY")
    base_url = _cfg("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set. Run: gai config")
    payload = json.dumps({
        "model": model, "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url}/chat/completions", data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }, method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"].strip()
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI error {e.code}: {body}")
    except KeyError:
        raise RuntimeError(f"Unexpected OpenAI response: {data}")
=======
        import yaml
        data = yaml.safe_load(cfg_file.read_text())
        return data.get("ai_context", "") if isinstance(data, dict) else ""
    except Exception:
        return ""

# ---------------------------------------------------------------------------
# config loader  ← FIX: clés stockées en UPPER pour matcher GAI_MODEL etc.
# ---------------------------------------------------------------------------

def _load_config() -> dict:
    import pathlib

    cfg: dict = {}

    env_file = pathlib.Path.home() / ".config" / "git-booster" / "config.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            cfg[k.strip().upper()] = v.strip()   # ← UPPER ici (fix)

    # env vars always win
    for key in (
        "GAI_PROVIDER", "GAI_MODEL", "OLLAMA_HOST",
        "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENAI_BASE_URL",
        "GAI_TIMEOUT",
    ):
        val = os.environ.get(key)
        if val:
            cfg[key] = val

    # normalise vers les clés courtes utilisées par les providers
    cfg["provider"]    = cfg.get("GAI_PROVIDER", "ollama")
    cfg["model"]       = cfg.get("GAI_MODEL",    "llama3.2")
    cfg["ollama_host"] = cfg.get("OLLAMA_HOST",  "http://localhost:11434")

    if "ANTHROPIC_API_KEY" in cfg:
        cfg["anthropic_api_key"] = cfg["ANTHROPIC_API_KEY"]
    if "OPENAI_API_KEY" in cfg:
        cfg["openai_api_key"] = cfg["OPENAI_API_KEY"]
    if "OPENAI_BASE_URL" in cfg:
        cfg["openai_base_url"] = cfg["OPENAI_BASE_URL"]
    if "GAI_TIMEOUT" in cfg:
        cfg["timeout"] = cfg["GAI_TIMEOUT"]
>>>>>>> Stashed changes

# ── Public API ────────────────────────────────────────────────────────────────

def ask(
    system: str,
    user: str,
    model: Optional[str] = None,
    max_tokens: int = MAX_TOKENS,
    cwd: Optional[str] = None,
) -> str:
    """Send a prompt to the configured AI provider and return the response."""
    cfg      = _load_config()
    provider = cfg.get("GAI_PROVIDER", "ollama").lower()
    chosen   = model or cfg.get("GAI_MODEL") or _default_model(provider)

    # Inject pre-ai context from skills into the system prompt
    extra_context = _collect_pre_ai_context(cwd=cwd)
    if extra_context:
        system = system + "\n\n# Project Context\n" + extra_context

    if provider == "ollama":
        return _ask_ollama(system, user, chosen, max_tokens)
    elif provider == "anthropic":
        return _ask_anthropic(system, user, chosen, max_tokens)
    elif provider == "openai":
        return _ask_openai(system, user, chosen, max_tokens)
    else:
        raise RuntimeError(
            f"Unknown provider '{provider}'. Valid: ollama, anthropic, openai.\n"
            "Run: gai config"
        )

def current_provider() -> str:
    return _cfg("GAI_PROVIDER", "ollama")

def current_model() -> str:
    return _cfg("GAI_MODEL") or _default_model(current_provider())
