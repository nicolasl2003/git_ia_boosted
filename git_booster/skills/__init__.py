"""
Skills system — modular AI capabilities for git-booster.

A skill is a Python module in this package that exposes:
  NAME        : str  — unique identifier (e.g. "commit", "review")
  DESCRIPTION : str  — one-line description shown in `gai skills`
  run(...)    : func — entry point called by the CLI

Skills are auto-discovered: drop a .py file here and it's available.
"""

import importlib
import pkgutil
from pathlib import Path
from typing import Any


def list_skills() -> dict[str, Any]:
    """Return {name: module} for all installed skills."""
    skills = {}
    pkg_dir = Path(__file__).parent
    for info in pkgutil.iter_modules([str(pkg_dir)]):
        if info.name.startswith("_"):
            continue
        mod = importlib.import_module(f"git_booster.skills.{info.name}")
        name = getattr(mod, "NAME", info.name)
        skills[name] = mod
    return skills


def get_skill(name: str) -> Any | None:
    """Return a skill module by name, or None if not found."""
    return list_skills().get(name)
