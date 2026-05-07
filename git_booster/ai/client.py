"""
Anthropic Claude client — single place for all LLM calls.
"""

import os
from typing import Optional
import anthropic


_client: Optional[anthropic.Anthropic] = None

DEFAULT_MODEL = "claude-3-5-haiku-20241022"   # fast + cheap; override via env
MAX_TOKENS = 4096


def get_client() -> anthropic.Anthropic:
    """Return (or lazily create) the shared Anthropic client."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY environment variable is not set.\n"
                "Export it before using git-booster:\n"
                "  export ANTHROPIC_API_KEY=sk-ant-..."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def ask(
    system: str,
    user: str,
    model: Optional[str] = None,
    max_tokens: int = MAX_TOKENS,
) -> str:
    """Send a message to Claude and return the text response."""
    client = get_client()
    chosen_model = model or os.environ.get("GIT_BOOSTER_MODEL", DEFAULT_MODEL)
    message = client.messages.create(
        model=chosen_model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return message.content[0].text.strip()
