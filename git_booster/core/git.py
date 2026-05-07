"""
Core Git wrapper — all subprocess calls to git live here.
"""

import subprocess
import os
from pathlib import Path
from typing import Optional


class GitError(Exception):
    """Raised when a git command fails."""
    pass


def _run(args: list[str], cwd: Optional[str] = None, check: bool = True) -> subprocess.CompletedProcess:
    """Run a git command and return the CompletedProcess result."""
    try:
        result = subprocess.run(
            args,
            cwd=cwd or os.getcwd(),
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            raise GitError(result.stderr.strip() or result.stdout.strip())
        return result
    except FileNotFoundError:
        raise GitError("git executable not found. Make sure git is installed.")


def is_git_repo(path: Optional[str] = None) -> bool:
    """Return True if the given path (or cwd) is inside a git repository."""
    result = _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path, check=False)
    return result.returncode == 0


def get_repo_root(path: Optional[str] = None) -> str:
    """Return the absolute path of the repository root."""
    result = _run(["git", "rev-parse", "--show-toplevel"], cwd=path)
    return result.stdout.strip()


def status(path: Optional[str] = None) -> str:
    """Return the raw output of `git status`."""
    result = _run(["git", "status"], cwd=path)
    return result.stdout.strip()


def status_porcelain(path: Optional[str] = None) -> list[tuple[str, str]]:
    """Return a parsed list of (status_code, filepath) tuples from `git status --porcelain`."""
    result = _run(["git", "status", "--porcelain"], cwd=path)
    entries = []
    for line in result.stdout.splitlines():
        if line.strip():
            code = line[:2].strip()
            filepath = line[3:].strip()
            entries.append((code, filepath))
    return entries


def diff_staged(path: Optional[str] = None) -> str:
    """Return the diff of staged changes."""
    result = _run(["git", "diff", "--staged"], cwd=path)
    return result.stdout.strip()


def diff_unstaged(path: Optional[str] = None) -> str:
    """Return the diff of unstaged changes."""
    result = _run(["git", "diff"], cwd=path)
    return result.stdout.strip()


def diff_head(path: Optional[str] = None) -> str:
    """Return the full diff between working tree and HEAD."""
    result = _run(["git", "diff", "HEAD"], cwd=path, check=False)
    return result.stdout.strip()


def add(files: list[str], path: Optional[str] = None) -> None:
    """Stage the given files (equivalent to `git add <files>`)."""
    _run(["git", "add"] + files, cwd=path)


def add_all(path: Optional[str] = None) -> None:
    """Stage all changes (equivalent to `git add .`)."""
    _run(["git", "add", "."], cwd=path)


def commit(message: str, path: Optional[str] = None) -> str:
    """Create a commit with the given message. Returns git output."""
    result = _run(["git", "commit", "-m", message], cwd=path)
    return result.stdout.strip()


def list_files_tracked(path: Optional[str] = None) -> list[str]:
    """Return all files tracked by git."""
    result = _run(["git", "ls-files"], cwd=path)
    return result.stdout.splitlines()


def list_files_all(path: Optional[str] = None) -> list[str]:
    """Return all files in the working tree (tracked + untracked, excluding ignored)."""
    result = _run(
        ["git", "ls-files", "--others", "--exclude-standard", "--cached"],
        cwd=path,
    )
    return result.stdout.splitlines()


def has_merge_conflicts(path: Optional[str] = None) -> bool:
    """Return True if there are unresolved merge conflicts in the working tree."""
    entries = status_porcelain(path)
    return any(code in ("UU", "AA", "DD", "AU", "UA", "DU", "UD") for code, _ in entries)


def get_conflict_files(path: Optional[str] = None) -> list[str]:
    """Return the list of files with merge conflicts."""
    entries = status_porcelain(path)
    return [
        f for code, f in entries
        if code in ("UU", "AA", "DD", "AU", "UA", "DU", "UD")
    ]


def read_conflict_file(filepath: str, repo_root: Optional[str] = None) -> str:
    """Read the raw content of a conflict file."""
    base = repo_root or os.getcwd()
    full_path = Path(base) / filepath
    return full_path.read_text(encoding="utf-8", errors="replace")


def write_resolved_file(filepath: str, content: str, repo_root: Optional[str] = None) -> None:
    """Write resolved content back to a conflict file."""
    base = repo_root or os.getcwd()
    full_path = Path(base) / filepath
    full_path.write_text(content, encoding="utf-8")


def mark_resolved(filepath: str, path: Optional[str] = None) -> None:
    """Mark a conflict file as resolved by staging it."""
    _run(["git", "add", filepath], cwd=path)


def get_log(n: int = 10, path: Optional[str] = None) -> str:
    """Return the last n commits as a formatted string.
    Returns an empty string if there are no commits yet."""
    result = _run(
        ["git", "log", f"-{n}", "--oneline", "--decorate"],
        cwd=path,
        check=False,
    )
    if result.returncode != 0:
        return ""   # repo has no commits yet
    return result.stdout.strip()


def get_branch(path: Optional[str] = None) -> str:
    """Return the current branch name.
    Falls back to reading .git/HEAD directly if there are no commits yet."""
    result = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path, check=False)
    if result.returncode == 0 and result.stdout.strip() not in ("", "HEAD"):
        return result.stdout.strip()
    # No commits yet — read the branch name from .git/HEAD
    repo_root = get_repo_root(path)
    head_file = Path(repo_root) / ".git" / "HEAD"
    if head_file.exists():
        content = head_file.read_text().strip()
        if content.startswith("ref: refs/heads/"):
            return content.replace("ref: refs/heads/", "")
    return "unknown"


def list_untracked_files(path: Optional[str] = None) -> list[str]:
    """Return untracked files (not yet staged, not ignored)."""
    result = _run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=path,
    )
    return result.stdout.splitlines()


def is_tracked(filepath: str, path: Optional[str] = None) -> bool:
    """Return True if the file is tracked by git."""
    result = _run(["git", "ls-files", "--error-unmatch", filepath], cwd=path, check=False)
    return result.returncode == 0


def rm_file(filepath: str, path: Optional[str] = None, force: bool = False, cached: bool = False) -> None:
    """Remove a file from git index. cached=True keeps it on disk."""
    args = ["git", "rm"]
    if force:
        args.append("-f")
    if cached:
        args.append("--cached")
    args.append(filepath)
    _run(args, cwd=path)


def walk_all_files(repo_root: str) -> list[str]:
    """Walk the repo root and return all file paths relative to repo_root,
    excluding hidden directories like .git."""
    all_files = []
    root = Path(repo_root)
    for p in root.rglob("*"):
        if p.is_file():
            # Skip .git internals
            parts = p.relative_to(root).parts
            if ".git" not in parts:
                all_files.append(str(p.relative_to(root)))
    return all_files
