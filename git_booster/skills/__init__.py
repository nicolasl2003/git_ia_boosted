"""
Skills auto-discovery and execution engine.

Categories:
  manual  → run with `gai skill <name>`
  auto    → run automatically on trigger:
              pre-ai      : inject context into every AI prompt
              pre-commit  : before gai commit
              post-commit : after successful commit
              post-push   : after successful push
"""

import importlib.util
import sys
from pathlib import Path
from typing import Optional

import yaml  # pip install pyyaml (already a common dep)

_BUILTIN_DIR = Path(__file__).parent
_USER_DIR    = Path.home() / ".config" / "git-booster" / "skills"

# ── Loader ────────────────────────────────────────────────────────────────────

def _load_python_skill(path: Path) -> dict:
    spec   = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {
        "name":        getattr(module, "NAME",        path.stem),
        "description": getattr(module, "DESCRIPTION", ""),
        "trigger":     getattr(module, "TRIGGER",     "manual"),
        "category":    getattr(module, "CATEGORY",    "manual"),
        "run":         getattr(module, "run",          None),
        "context":     getattr(module, "context",      None),  # for pre-ai
        "_type":       "python",
    }

def _load_yaml_skill(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    return {
        "name":        data.get("name",        path.stem),
        "description": data.get("description", ""),
        "trigger":     data.get("trigger",     "manual"),
        "category":    data.get("category",    "manual"),
        "action":      data.get("action",      ""),
        "run":         None,
        "context":     None,
        "_type":       "yaml",
    }

def _discover(directory: Path) -> list[dict]:
    skills = []
    if not directory.exists():
        return skills
    for path in sorted(directory.iterdir()):
        try:
            if path.suffix == ".py" and not path.name.startswith("_"):
                skills.append(_load_python_skill(path))
            elif path.suffix in (".yaml", ".yml"):
                skills.append(_load_yaml_skill(path))
        except Exception as e:
            print(f"⚠️  Could not load skill {path.name}: {e}")
    return skills

def all_skills(trigger: str | None = None) -> list[dict]:
    seen   = {}
    skills = _discover(_BUILTIN_DIR) + _discover(_USER_DIR)
    for s in skills:
        seen[s["name"]] = s
    result = list(seen.values())
    if trigger:
        result = [s for s in result if s.get("trigger") == trigger]
    return result


def get_skill(name: str) -> Optional[dict]:
    for s in all_skills():
        if s["name"] == name:
            return s
    return None

# ── Execution ─────────────────────────────────────────────────────────────────

import subprocess

def _run_yaml_skill(skill: dict, args: list[str], cwd: Optional[str]) -> None:
    action = skill["action"]
    if args:
        action = action + " " + " ".join(args)
    subprocess.run(action, shell=True, cwd=cwd)

def run_skill(name: str, args: list[str] = [], cwd: Optional[str] = None) -> None:
    skill = get_skill(name)
    if not skill:
        print(f"❌ Skill '{name}' not found. Use `gai skills` to list available skills.")
        return
    if skill["_type"] == "python" and skill["run"]:
        skill["run"](args=args, path=cwd)
    elif skill["_type"] == "yaml":
        _run_yaml_skill(skill, args, cwd)

# ── Trigger runner ────────────────────────────────────────────────────────────

def run_trigger(trigger: str, cwd: Optional[str] = None) -> None:
    """Run all auto skills matching the given trigger."""
    for skill in all_skills():
        if skill["trigger"] == trigger and skill["trigger"] != "manual":
            print(f"⚡ Auto-skill [{trigger}]: {skill['name']}")
            run_skill(skill["name"], cwd=cwd)

def collect_context(cwd: Optional[str] = None) -> str:
    """
    Collect extra context from all pre-ai skills.
    Python skills expose a `context(path) -> str` function.
    YAML skills expose a `context_cmd` shell command whose stdout is captured.
    Returns a combined string to inject into the AI prompt.
    """
    parts = []
    for skill in all_skills():
        if skill["trigger"] != "pre-ai":
            continue
        try:
            if skill["_type"] == "python" and skill["context"]:
                result = skill["context"](path=cwd)
                if result:
                    parts.append(f"[{skill['name']}]\n{result.strip()}")
            elif skill["_type"] == "yaml" and skill.get("context_cmd"):
                result = subprocess.check_output(
                    skill["context_cmd"], shell=True, cwd=cwd,
                    stderr=subprocess.DEVNULL, text=True
                )
                if result.strip():
                    parts.append(f"[{skill['name']}]\n{result.strip()}")
        except Exception as e:
            print(f"⚠️  pre-ai skill '{skill['name']}' failed: {e}")
    return "\n\n".join(parts)
list_skills = all_skills
