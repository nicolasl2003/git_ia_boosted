"""
Skills system for git-booster.
Supports two skill formats:

1. Python skill  (.py)
   ─────────────────────────────────────────────────────────────────────────
   NAME        = "myskill"          # gai skill myskill
   DESCRIPTION = "Does something"   # shown in: gai skills list
   TRIGGER     = "manual"           # optional: manual | pre-commit | post-push
   EXECUTE     = "manual"           # alias for TRIGGER

   def run(args: list[str], path: str | None = None) -> None:
       ...

2. YAML skill    (.yaml / .yml)
   ─────────────────────────────────────────────────────────────────────────
   # myskill.yaml
   name:        myskill
   description: Does something
   trigger:     manual          # manual | pre-commit | post-push | post-commit
   action:      echo "Hello"    # shell command OR multi-line script block

   Example multi-line action:
     action: |
       echo "Building..."
       make build
       echo "Done."

   ─────────────────────────────────────────────────────────────────────────

Auto-discovery
  All .py and .yaml/.yml files in git_booster/skills/ (and ~/.config/git-booster/skills/)
  are loaded automatically. No registration needed.

Adding a user skill
  Place a .yaml or .py file in:
    ~/.config/git-booster/skills/

Public API
  list_skills(trigger=None)   → {name: SkillInfo}
  get_skill(name)             → SkillInfo | None
  run_trigger(trigger, cwd)   → runs all skills with matching trigger
"""

import importlib
import pkgutil
import subprocess
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from rich.console import Console

console = Console()

# ── Skill descriptor ──────────────────────────────────────────────────────────

@dataclass
class SkillInfo:
    name:        str
    description: str
    trigger:     str                 # manual | pre-commit | post-commit | post-push
    source:      str                 # "python" | "yaml"
    source_path: str                 # absolute path to the skill file
    # For Python skills:
    _run_fn:     Callable | None = field(default=None, repr=False)
    # For YAML skills:
    _action:     str | None      = field(default=None, repr=False)

    def run(self, args: list[str] = (), path: str | None = None) -> None:
        """Execute this skill."""
        if self.source == "python" and self._run_fn:
            self._run_fn(list(args), path=path)
        elif self.source == "yaml" and self._action:
            _run_yaml_action(self._action, path or os.getcwd())
        else:
            console.print(f"[red]Skill '{self.name}' has no runnable action.[/red]")


def _run_yaml_action(action: str, cwd: str) -> None:
    """Execute a YAML skill action as a shell command."""
    console.print(f"[dim]Running: {action.splitlines()[0][:60]}[/dim]")
    result = subprocess.run(
        action, shell=True, cwd=cwd,
        text=True, capture_output=False,
    )
    if result.returncode != 0:
        console.print(f"[red]Skill exited with code {result.returncode}.[/red]")


# ── Loaders ───────────────────────────────────────────────────────────────────

def _load_python_skill(module_name: str) -> SkillInfo | None:
    """Load a Python skill module and return a SkillInfo."""
    try:
        mod = importlib.import_module(module_name)
        if not hasattr(mod, "run"):
            return None
        trigger = (
            getattr(mod, "TRIGGER", None)
            or getattr(mod, "EXECUTE", None)
            or "manual"
        )
        return SkillInfo(
            name        = getattr(mod, "NAME", module_name.split(".")[-1]),
            description = getattr(mod, "DESCRIPTION", ""),
            trigger     = trigger.lower(),
            source      = "python",
            source_path = str(Path(mod.__file__) if mod.__file__ else ""),
            _run_fn     = mod.run,
        )
    except Exception as e:
        console.print(f"[yellow]Could not load skill '{module_name}': {e}[/yellow]")
        return None


def _load_yaml_skill(yaml_path: Path) -> SkillInfo | None:
    """Load a YAML skill file and return a SkillInfo."""
    try:
        # Use stdlib only — no PyYAML dependency needed for simple key: value
        data = _parse_simple_yaml(yaml_path.read_text(encoding="utf-8"))
        name    = data.get("name", yaml_path.stem)
        trigger = (data.get("trigger") or data.get("execute") or "manual").lower()
        action  = data.get("action", "")
        if not action:
            console.print(f"[yellow]Skill '{name}' has no action field — skipped.[/yellow]")
            return None
        return SkillInfo(
            name        = name,
            description = data.get("description", ""),
            trigger     = trigger,
            source      = "yaml",
            source_path = str(yaml_path),
            _action     = action,
        )
    except Exception as e:
        console.print(f"[yellow]Could not load YAML skill '{yaml_path.name}': {e}[/yellow]")
        return None


def _parse_simple_yaml(text: str) -> dict[str, str]:
    """
    Minimal YAML parser — handles the subset used by skill files:
      key: value
      key: |
        line1
        line2
    No lists, no nested objects needed.
    """
    result: dict[str, str] = {}
    lines  = text.splitlines()
    i      = 0
    while i < len(lines):
        line = lines[i]
        # Skip comments and blank lines
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if ":" not in line:
            i += 1
            continue
        key, sep, rest = line.partition(":")
        key  = key.strip()
        rest = rest.strip()
        if rest == "|":
            # Multi-line block scalar
            block_lines = []
            i += 1
            indent = None
            while i < len(lines):
                bl = lines[i]
                if bl.strip() == "" or bl.startswith(" ") or bl.startswith("\t"):
                    if indent is None and bl.strip():
                        indent = len(bl) - len(bl.lstrip())
                    block_lines.append(bl[indent:] if indent else bl)
                    i += 1
                else:
                    break
            result[key] = "\n".join(block_lines).strip()
        else:
            result[key] = rest
            i += 1
    return result


# ── Discovery ─────────────────────────────────────────────────────────────────

def _skill_dirs() -> list[Path]:
    """Return all directories to scan for skills."""
    dirs = [Path(__file__).parent]
    user_dir = Path.home() / ".config" / "git-booster" / "skills"
    if user_dir.is_dir():
        dirs.append(user_dir)
    return dirs


def list_skills(trigger: str | None = None) -> dict[str, SkillInfo]:
    """Return {name: SkillInfo} for all valid skills, optionally filtered by trigger."""
    skills: dict[str, SkillInfo] = {}

    for skill_dir in _skill_dirs():
        # Python skills via pkgutil (only for the package directory)
        if skill_dir == Path(__file__).parent:
            for info in pkgutil.iter_modules([str(skill_dir)]):
                if info.name.startswith("_"):
                    continue
                si = _load_python_skill(f"git_booster.skills.{info.name}")
                if si:
                    skills[si.name] = si

        # Python files in user dir
        elif skill_dir.is_dir():
            for py_file in skill_dir.glob("*.py"):
                if py_file.name.startswith("_"):
                    continue
                import importlib.util
                spec = importlib.util.spec_from_file_location(py_file.stem, py_file)
                if spec and spec.loader:
                    mod = importlib.util.module_from_spec(spec)
                    try:
                        spec.loader.exec_module(mod)
                        if hasattr(mod, "run"):
                            t = getattr(mod, "TRIGGER", getattr(mod, "EXECUTE", "manual"))
                            si = SkillInfo(
                                name        = getattr(mod, "NAME", py_file.stem),
                                description = getattr(mod, "DESCRIPTION", ""),
                                trigger     = t.lower(),
                                source      = "python",
                                source_path = str(py_file),
                                _run_fn     = mod.run,
                            )
                            skills[si.name] = si
                    except Exception as e:
                        console.print(f"[yellow]Could not load '{py_file.name}': {e}[/yellow]")

        # YAML skills in any skill dir
        for ext in ("*.yaml", "*.yml"):
            for yaml_file in skill_dir.glob(ext):
                si = _load_yaml_skill(yaml_file)
                if si:
                    skills[si.name] = si

    if trigger:
        skills = {k: v for k, v in skills.items() if v.trigger == trigger.lower()}

    return skills


def get_skill(name: str) -> SkillInfo | None:
    """Return a SkillInfo by name, or None if not found."""
    return list_skills().get(name)


def run_trigger(trigger: str, cwd: str | None = None) -> None:
    """Run all skills whose trigger matches (e.g. 'pre-commit', 'post-push')."""
    matched = list_skills(trigger=trigger)
    if not matched:
        return
    cwd = cwd or os.getcwd()
    for name, skill in matched.items():
        console.print(f"[dim]Running skill ({trigger}): {name}[/dim]")
        try:
            skill.run(path=cwd)
        except Exception as e:
            console.print(f"[yellow]Skill '{name}' failed: {e}[/yellow]")
