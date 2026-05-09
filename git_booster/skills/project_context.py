# ~/.config/git-booster/skills/project_context.py

NAME        = "project_context"
DESCRIPTION = "Inject project name and language into every AI prompt"
TRIGGER     = "pre-ai"

def context(path: str | None = None) -> str:
    import subprocess, json
    from pathlib import Path

    info = []

    # Repo name
    try:
        remote = subprocess.check_output(
            ["git", "remote", "get-url", "origin"],
            cwd=path, text=True, stderr=subprocess.DEVNULL
        ).strip()
        info.append(f"Repository: {remote.split('/')[-1].replace('.git','')}")
    except Exception:
        pass

    # Current branch
    try:
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            cwd=path, text=True, stderr=subprocess.DEVNULL
        ).strip()
        info.append(f"Branch: {branch}")
    except Exception:
        pass

    # Detect language
    if path:
        p = Path(path)
        if (p / "package.json").exists():
            info.append("Language: JavaScript/TypeScript")
        elif (p / "pyproject.toml").exists() or (p / "setup.py").exists():
            info.append("Language: Python")
        elif (p / "Cargo.toml").exists():
            info.append("Language: Rust")
        elif (p / "go.mod").exists():
            info.append("Language: Go")

    return "\n".join(info)
