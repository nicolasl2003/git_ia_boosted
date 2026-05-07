"""
Ollama client — calls the local Ollama HTTP API.
No API key required. Make sure Ollama is running: `ollama serve`

Configuration (environment variables):
  OLLAMA_HOST   Ollama base URL  (default: http://localhost:11434)
  GAI_MODEL     Model to use     (default: llama3.2)
"""

import os
import json
import urllib.request
import urllib.error
from typing import Optional

DEFAULT_MODEL = "llama3.2"
DEFAULT_HOST  = "http://localhost:11434"
MAX_TOKENS    = 4096


def _get_host() -> str:
    return os.environ.get("OLLAMA_HOST", DEFAULT_HOST).rstrip("/")


def _get_model() -> str:
    return os.environ.get("GAI_MODEL", DEFAULT_MODEL)


def ask(
    system: str,
    user: str,
    model: Optional[str] = None,
    max_tokens: int = MAX_TOKENS,
) -> str:
    """Send a message to Ollama and return the text response."""
    host         = _get_host()
    chosen_model = model or _get_model()

    payload = json.dumps({
        "model": chosen_model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
        "stream": False,
        "options": {
            "num_predict": max_tokens,
        },
    }).encode("utf-8")

    req = urllib.request.Request(
        f"{host}/api/chat",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["message"]["content"].strip()
    except urllib.error.URLError as e:
        raise RuntimeError(
            f"Cannot reach Ollama at {host}.\n"
            "Make sure Ollama is running:  ollama serve\n"
            f"Details: {e}"
        )
    except KeyError:
        raise RuntimeError(f"Unexpected response from Ollama: {data}")
