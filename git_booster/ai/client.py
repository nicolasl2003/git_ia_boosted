"""
AI client — multi-provider with timeout + fallback.
Providers: ollama | anthropic | openai
"""

from __future__ import annotations

import os
import time

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
    system_or_prompt: str,
    user_prompt: str | None = None,
    cwd: str | None = None,
    timeout: int | None = None,
    max_tokens: int | None = None,
    model: str | None = None,
) -> str:
    """
    Send a prompt to the configured AI provider.
    Retries MAX_RETRIES times, then returns a safe fallback string.

    Usage:
        ask("prompt")                              # single string
        ask("system", "user")                      # system + user
        ask("prompt", cwd=cwd)                     # with context
        ask(system, user, max_tokens=256, cwd=cwd) # full
    """
    cfg      = _load_config()
    provider = cfg["provider"]
    timeout  = timeout or int(cfg.get("timeout", DEFAULT_TIMEOUT))

    if model:
        cfg["model"] = model

    if user_prompt:
        prompt = f"{system_or_prompt}\n\n{user_prompt}"
    else:
        prompt = system_or_prompt

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


def ask_with_history(messages: list[dict]) -> str:
    """
    Send a multi-turn conversation to the configured AI provider.
    messages: list of {"role": "system"|"user"|"assistant", "content": str}
    """
    cfg      = _load_config()
    provider = cfg["provider"]
    timeout  = int(cfg.get("timeout", DEFAULT_TIMEOUT))

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 2):
        try:
            if provider == "ollama":
                return _ollama_chat(messages, cfg, timeout)
            elif provider == "anthropic":
                return _anthropic_chat(messages, cfg, timeout)
            elif provider == "openai":
                return _openai_chat(messages, cfg, timeout)
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

    console.print("[red]✗ AI unavailable after all retries.[/red]")
    return "# AI unavailable"

# ---------------------------------------------------------------------------
# provider implementations — single prompt
# ---------------------------------------------------------------------------

def _ask_ollama(prompt: str, cfg: dict, timeout: int) -> str:
    import httpx

    host  = cfg.get("ollama_host", "http://localhost:11434")
    model = cfg.get("model", "llama3.2")

    try:
        resp = httpx.post(
            f"{host}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["response"].strip()

    except httpx.TimeoutException as e:
        raise _TimeoutError(f"Ollama timeout after {timeout}s") from e

    except httpx.ConnectError as e:
        raise _ProviderUnavailableError(
            f"Cannot reach Ollama at {host}. Is it running? Try: ollama serve"
        ) from e

    except httpx.HTTPStatusError as e:
        raise _ProviderUnavailableError(
            f"Ollama HTTP {e.response.status_code}: {e.response.text[:200]}"
        ) from e


def _ask_anthropic(prompt: str, cfg: dict, timeout: int) -> str:
    try:
        import anthropic
    except ImportError:
        raise _ProviderUnavailableError(
            "anthropic package not installed. Run: pip install anthropic"
        )

    api_key = cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise _ProviderUnavailableError("ANTHROPIC_API_KEY is not set.")

    model = cfg.get("model", "claude-3-haiku-20240307")

    try:
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()

    except anthropic.APITimeoutError as e:
        raise _TimeoutError(f"Anthropic timeout after {timeout}s") from e

    except anthropic.APIConnectionError as e:
        raise _ProviderUnavailableError(f"Anthropic connection error: {e}") from e

    except anthropic.AuthenticationError as e:
        raise _ProviderUnavailableError("Anthropic: invalid API key.") from e


def _ask_openai(prompt: str, cfg: dict, timeout: int) -> str:
    try:
        import openai
    except ImportError:
        raise _ProviderUnavailableError(
            "openai package not installed. Run: pip install openai"
        )

    api_key  = cfg.get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")
    base_url = cfg.get("openai_base_url") or os.environ.get(
        "OPENAI_BASE_URL", "https://api.openai.com/v1"
    )
    model = cfg.get("model", "gpt-4o-mini")

    if not api_key:
        raise _ProviderUnavailableError("OPENAI_API_KEY is not set.")

    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.choices[0].message.content.strip()

    except openai.APITimeoutError as e:
        raise _TimeoutError(f"OpenAI timeout after {timeout}s") from e

    except openai.APIConnectionError as e:
        raise _ProviderUnavailableError(f"OpenAI connection error: {e}") from e

    except openai.AuthenticationError:
        raise _ProviderUnavailableError("OpenAI: invalid API key.") from None

# ---------------------------------------------------------------------------
# provider implementations — multi-turn chat
# ---------------------------------------------------------------------------

def _ollama_chat(messages: list[dict], cfg: dict, timeout: int) -> str:
    import httpx

    host  = cfg.get("ollama_host", "http://localhost:11434")
    model = cfg.get("model", "llama3.2")

    try:
        resp = httpx.post(
            f"{host}/api/chat",
            json={"model": model, "messages": messages, "stream": False},
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()

    except httpx.TimeoutException as e:
        raise _TimeoutError(f"Ollama timeout after {timeout}s") from e

    except httpx.ConnectError as e:
        raise _ProviderUnavailableError(
            f"Cannot reach Ollama at {host}. Is it running? Try: ollama serve"
        ) from e

    except httpx.HTTPStatusError as e:
        raise _ProviderUnavailableError(
            f"Ollama HTTP {e.response.status_code}: {e.response.text[:200]}"
        ) from e


def _anthropic_chat(messages: list[dict], cfg: dict, timeout: int) -> str:
    try:
        import anthropic
    except ImportError:
        raise _ProviderUnavailableError(
            "anthropic package not installed. Run: pip install anthropic"
        )

    api_key = cfg.get("anthropic_api_key") or os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise _ProviderUnavailableError("ANTHROPIC_API_KEY is not set.")

    model = cfg.get("model", "claude-3-haiku-20240307")

    # Anthropic sépare system des messages
    system = ""
    chat_messages = []
    for m in messages:
        if m["role"] == "system":
            system = m["content"]
        else:
            chat_messages.append({"role": m["role"], "content": m["content"]})

    try:
        client = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system,
            messages=chat_messages,
        )
        return response.content[0].text.strip()

    except anthropic.APITimeoutError as e:
        raise _TimeoutError(f"Anthropic timeout after {timeout}s") from e

    except anthropic.APIConnectionError as e:
        raise _ProviderUnavailableError(f"Anthropic connection error: {e}") from e

    except anthropic.AuthenticationError as e:
        raise _ProviderUnavailableError("Anthropic: invalid API key.") from e


def _openai_chat(messages: list[dict], cfg: dict, timeout: int) -> str:
    try:
        import openai
    except ImportError:
        raise _ProviderUnavailableError(
            "openai package not installed. Run: pip install openai"
        )

    api_key  = cfg.get("openai_api_key") or os.environ.get("OPENAI_API_KEY", "")
    base_url = cfg.get("openai_base_url") or os.environ.get(
        "OPENAI_BASE_URL", "https://api.openai.com/v1"
    )
    model = cfg.get("model", "gpt-4o-mini")

    if not api_key:
        raise _ProviderUnavailableError("OPENAI_API_KEY is not set.")

    try:
        client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=4096,
        )
        return resp.choices[0].message.content.strip()

    except openai.APITimeoutError as e:
        raise _TimeoutError(f"OpenAI timeout after {timeout}s") from e

    except openai.APIConnectionError as e:
        raise _ProviderUnavailableError(f"OpenAI connection error: {e}") from e

    except openai.AuthenticationError:
        raise _ProviderUnavailableError("OpenAI: invalid API key.") from None

# ---------------------------------------------------------------------------
# fallback
# ---------------------------------------------------------------------------

def _fallback(prompt: str, error: Exception | None) -> str:
    p = prompt.lower()

    if "commit" in p:
        return "chore: update files"

    if "gitignore" in p:
        return ""

    if "conflict" in p or "merge" in p:
        return (
            "# AI unavailable — resolve conflicts manually.\n"
            "# Look for <<<<<<< / ======= / >>>>>>> markers."
        )

    if error:
        return f"# AI error: {error}"

    return "# AI unavailable"

# ---------------------------------------------------------------------------
# project context (.git-booster.yml)
# ---------------------------------------------------------------------------

def _load_project_context(cwd: str) -> str:
    import pathlib

    cfg_file = pathlib.Path(cwd) / ".git-booster.yml"
    if not cfg_file.exists():
        return ""

    try:
        import yaml
        data = yaml.safe_load(cfg_file.read_text())
        return data.get("ai_context", "") if isinstance(data, dict) else ""
    except Exception:
        return ""

# ---------------------------------------------------------------------------
# config loader
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
            k = k.strip().upper()
            v = v.strip()
            if k == "GAI_PROVIDER":
                cfg["provider"] = v
            elif k == "GAI_MODEL":
                cfg["model"] = v
            elif k == "OLLAMA_HOST":
                cfg["ollama_host"] = v
            elif k == "ANTHROPIC_API_KEY":
                cfg["anthropic_api_key"] = v
            elif k == "OPENAI_API_KEY":
                cfg["openai_api_key"] = v
            elif k == "OPENAI_BASE_URL":
                cfg["openai_base_url"] = v
            elif k == "GAI_TIMEOUT":
                cfg["timeout"] = v

    overrides = {
        "GAI_PROVIDER":      "provider",
        "GAI_MODEL":         "model",
        "OLLAMA_HOST":       "ollama_host",
        "ANTHROPIC_API_KEY": "anthropic_api_key",
        "OPENAI_API_KEY":    "openai_api_key",
        "OPENAI_BASE_URL":   "openai_base_url",
        "GAI_TIMEOUT":       "timeout",
    }
    for env_key, cfg_key in overrides.items():
        val = os.environ.get(env_key)
        if val:
            cfg[cfg_key] = val

    cfg.setdefault("provider", "ollama")
    cfg.setdefault("model",    "llama3.2")

    return cfg

# ---------------------------------------------------------------------------
# custom exceptions
# ---------------------------------------------------------------------------

class _TimeoutError(Exception):
    pass

class _ProviderUnavailableError(Exception):
    pass
