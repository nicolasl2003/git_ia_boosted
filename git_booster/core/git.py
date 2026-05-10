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


def _run(
    args: list[str],
    cwd: Optional[str] = None,
    check: bool = True,
    env: Optional[dict] = None,
) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(
            args,
            cwd=cwd or os.getcwd(),
            env=env,
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            raise GitError(result.stderr.strip() or result.stdout.strip())
        return result
    except FileNotFoundError:
        raise GitError("git executable not found. Make sure git is installed.")


def is_git_repo(path: Optional[str] = None) -> bool:
    result = _run(["git", "rev-parse", "--is-inside-work-tree"], cwd=path, check=False)
    return result.returncode == 0


def get_repo_root(path: Optional[str] = None) -> str:
    result = _run(["git", "rev-parse", "--show-toplevel"], cwd=path)
    return result.stdout.strip()


def status(path: Optional[str] = None) -> str:
    result = _run(["git", "status"], cwd=path)
    return result.stdout.strip()


def get_status(path: Optional[str] = None) -> str:
    return status(path)


def status_porcelain(path: Optional[str] = None) -> list[tuple[str, str]]:
    result = _run(["git", "status", "--porcelain"], cwd=path)
    entries = []
    for line in result.stdout.splitlines():
        if line.strip():
            code = line[:2].strip()
            filepath = line[3:].strip()
            entries.append((code, filepath))
    return entries


def diff_staged(path: Optional[str] = None) -> str:
    result = _run(["git", "diff", "--staged"], cwd=path)
    return result.stdout.strip()


def get_staged_diff(path: Optional[str] = None) -> str:
    return diff_staged(path)


def staged_diff(path: Optional[str] = None) -> str:
    return diff_staged(path)


def diff_unstaged(path: Optional[str] = None) -> str:
    result = _run(["git", "diff"], cwd=path)
    return result.stdout.strip()


def diff_head(path: Optional[str] = None) -> str:
    result = _run(["git", "diff", "HEAD"], cwd=path, check=False)
    return result.stdout.strip()


def add(files: list[str], path: Optional[str] = None) -> None:
    _run(["git", "add"] + files, cwd=path)


def add_all(path: Optional[str] = None) -> None:
    _run(["git", "add", "."], cwd=path)


def git_add(file: Optional[str] = None, path: Optional[str] = None) -> None:
    if file:
        add([file], path)
    else:
        add_all(path)


def commit(message: str, path: Optional[str] = None) -> str:
    result = _run(["git", "commit", "-m", message], cwd=path)
    return result.stdout.strip()


def git_commit(message: str, path: Optional[str] = None) -> subprocess.CompletedProcess:
    return _run(["git", "commit", "-m", message], cwd=path, check=False)


def push(branch: Optional[str] = None, remote: str = "origin", path: Optional[str] = None) -> tuple[bool, str]:
    args = ["git", "push", remote]
    if branch:
        args.append(branch)
    result = _run(args, cwd=path, check=False)
    out = (result.stdout + result.stderr).strip()
    return result.returncode == 0, out


def git_push(branch: Optional[str] = None, remote: str = "origin", path: Optional[str] = None) -> tuple[bool, str]:
    return push(branch, remote, path)


def pull(branch: Optional[str] = None, remote: str = "origin", strategy: str = "rebase", path: Optional[str] = None) -> tuple[bool, str]:
    args = ["git", "pull", f"--{strategy}", remote]
    if branch:
        args.append(branch)
    result = _run(args, cwd=path, check=False)
    out = (result.stdout + result.stderr).strip()
    return result.returncode == 0, out


def git_pull(branch: Optional[str] = None, remote: str = "origin", strategy: str = "rebase", path: Optional[str] = None) -> tuple[bool, str]:
    return pull(branch, remote, strategy, path)


def get_current_branch(path: Optional[str] = None) -> str:
    result = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path, check=False)
    return result.stdout.strip()


def get_remote_url(remote: str = "origin", path: Optional[str] = None) -> str:
    result = _run(["git", "remote", "get-url", remote], cwd=path, check=False)
    return result.stdout.strip()


def list_files_tracked(path: Optional[str] = None) -> list[str]:
    result = _run(["git", "ls-files"], cwd=path)
    return result.stdout.splitlines()


def list_files_all(path: Optional[str] = None) -> list[str]:
    result = _run(
        ["git", "ls-files", "--others", "--exclude-standard", "--cached"],
        cwd=path,
    )
    return result.stdout.splitlines()


def has_merge_conflicts(path: Optional[str] = None) -> bool:
    entries = status_porcelain(path)
    return any(code in ("UU", "AA", "DD", "AU", "UA", "DU", "UD") for code, _ in entries)


def get_conflict_files(path: Optional[str] = None) -> list[str]:
    entries = status_porcelain(path)
    return [
        f for code, f in entries
        if code in ("UU", "AA", "DD", "AU", "UA", "DU", "UD")
    ]


def get_conflicts(path: Optional[str] = None) -> list[str]:
    return get_conflict_files(path)


def read_conflict_file(filepath: str, repo_root: Optional[str] = None) -> str:
    root = repo_root or os.getcwd()
    full_path = Path(root) / filepath
    return full_path.read_text(encoding="utf-8")


def write_resolved_file(filepath: str, content: str, repo_root: Optional[str] = None) -> None:
    root = repo_root or os.getcwd()
    full_path = Path(root) / filepath
    full_path.write_text(content, encoding="utf-8")


def mark_resolved(filepath: str, path: Optional[str] = None) -> None:
    _run(["git", "add", filepath], cwd=path)


def stash(message: str = "gai-stash", path: Optional[str] = None) -> tuple[bool, str]:
    result = _run(
        ["git", "stash", "push", "-u", "-m", message],
        cwd=path, check=False,
    )
    out = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        return False, out
    for line in out.splitlines():
        if "stash@{" in line:
            start = line.index("stash@{")
            ref = line[start:].split()[0].rstrip(")")
            return True, ref
    return True, "stash@{0}"


def stash_pop(path: Optional[str] = None) -> tuple[bool, str]:
    result = _run(["git", "stash", "pop"], cwd=path, check=False)
    out = (result.stdout + result.stderr).strip()
    return result.returncode == 0, out


def stash_drop(ref: str = "stash@{0}", path: Optional[str] = None) -> None:
    _run(["git", "stash", "drop", ref], cwd=path, check=False)


def rebase_continue(path: Optional[str] = None) -> tuple[bool, str]:
    env = {**os.environ, "GIT_EDITOR": "true"}
    result = _run(["git", "rebase", "--continue"], cwd=path, check=False, env=env)
    out = (result.stdout + result.stderr).strip()
    return result.returncode == 0, out


def rebase_skip(path: Optional[str] = None) -> tuple[bool, str]:
    result = _run(["git", "rebase", "--skip"], cwd=path, check=False)
    out = (result.stdout + result.stderr).strip()
    return result.returncode == 0, out


def abort_merge(path: Optional[str] = None) -> tuple[bool, str]:
    result = _run(["git", "merge", "--abort"], cwd=path, check=False)
    return result.returncode == 0, result.stderr.strip()


def abort_rebase(path: Optional[str] = None) -> tuple[bool, str]:
    result = _run(["git", "rebase", "--abort"], cwd=path, check=False)
    return result.returncode == 0, result.stderr.strip()


def is_merging(path: Optional[str] = None) -> bool:
    repo_root = get_repo_root(path)
    return (Path(repo_root) / ".git" / "MERGE_HEAD").exists()


def is_rebasing(path: Optional[str] = None) -> bool:
    repo_root = get_repo_root(path)
    git_dir = Path(repo_root) / ".git"
    return (git_dir / "rebase-merge").exists() or (git_dir / "rebase-apply").exists()


def count_local_commits(branch: str, remote: str = "origin", path: Optional[str] = None) -> int:
    result = _run(
        ["git", "rev-list", "--count", f"{remote}/{branch}..HEAD"],
        cwd=path, check=False,
    )
    try:
        return int(result.stdout.strip())
    except ValueError:
        return 0


def has_merge_commits(path: Optional[str] = None, n: int = 20) -> bool:
    result = _run(
        ["git", "log", f"-{n}", "--merges", "--oneline"],
        cwd=path, check=False,
    )
    if result.returncode != 0:
        return False
    return bool(result.stdout.strip())


def get_remote_default_branch(remote: str = "origin", path: Optional[str] = None) -> str:
    result = _run(
        ["git", "remote", "show", remote],
        cwd=path, check=False,
    )
    for line in result.stdout.splitlines():
        if "HEAD branch" in line:
            return line.split(":")[-1].strip()
    return "main"


def diff_commit(commit_ref: str, path: Optional[str] = None) -> str:
    result = _run(
        ["git", "show", "--format=", commit_ref],
        cwd=path, check=False,
    )
    if result.returncode != 0:
        raise GitError(f"Cannot show commit '{commit_ref}': {result.stderr.strip()}")
    return result.stdout.strip()


def get_commit_info(commit_ref: str, path: Optional[str] = None) -> str:
    result = _run(
        ["git", "log", "-1", "--pretty=format:%H%n%an <%ae>%n%ad%n%s", commit_ref],
        cwd=path, check=False,
    )
    if result.returncode != 0:
        raise GitError(f"Cannot find commit '{commit_ref}'")
    return result.stdout.strip()


def walk_all_files(repo_root: str) -> list[str]:
    all_files = []
    root = Path(repo_root)
    for p in root.rglob("*"):
        if p.is_file():
            parts = p.relative_to(root).parts
            if ".git" not in parts:
                all_files.append(str(p.relative_to(root)))
    return all_files


def run(args: list[str], cwd: Optional[str] = None) -> str:
    if not args or args[0] != "git":
        args = ["git"] + args
    result = _run(args, cwd=cwd, check=False)
    return result.stdout.strip()


def list_untracked_files(cwd: Optional[str] = None) -> list[str]:
    result = _run(["git", "ls-files", "--others", "--exclude-standard"], cwd=cwd, check=False)
    return [f for f in result.stdout.strip().splitlines() if f]


# Push error constants
PUSH_ERR_FETCH_FIRST = "fetch first"
PUSH_ERR_NO_UPSTREAM = "no upstream"
PUSH_ERR_BAD_REFSPEC = "bad refspec"
PUSH_ERR_AUTH = "authentication"
PUSH_ERR_NO_REMOTE = "no remote"
PUSH_ERR_REJECTED = "rejected"
PUSH_ERR_PERMISSION = "permission denied"
PUSH_ERR_UNKNOWN = "unknown"
PUSH_ERR_REFSPEC = "refspec"
PUSH_ERR_REMOTE_NOT_FOUND = "remote not found"


def get_remote(cwd: str | None = None) -> str | None:
    """Return the first configured remote, or None."""
    try:
        result = run(["remote"], cwd=cwd)
        remotes = [r.strip() for r in result.splitlines() if r.strip()]
        return remotes[0] if remotes else None
    except Exception:
        return None


def get_current_branch(cwd: str | None = None) -> str:
    """Return the current branch name."""
    return run(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd).strip()

# alias
get_branch = get_current_branch


def has_uncommitted_changes(path: str = ".") -> bool:
    r = _run(["git", "status", "--porcelain"], cwd=path)
    return bool(r.stdout.strip())


def list_remote_branches(remote: str = "origin", path: str = ".") -> list[str]:
    r = _run(["git", "branch", "-r"], cwd=path)
    branches = []
    for line in r.stdout.splitlines():
        line = line.strip()
        if line.startswith(f"{remote}/") and "HEAD" not in line:
            branches.append(line[len(remote)+1:])
    return branches


def set_upstream(remote: str, branch: str, path: str = ".") -> tuple[bool, str]:
    r = _run(["git", "push", "--set-upstream", remote, branch], cwd=path)
    return r.returncode == 0, r.stdout + r.stderr


def stash_push(path: str = ".") -> tuple[bool, str]:
    r = _run(["git", "stash", "push", "-m", "gai-auto-stash"], cwd=path)
    ok = r.returncode == 0
    ref = "stash@{0}" if ok else ""
    return ok, ref


def stash_pop(path: str = ".") -> tuple[bool, str]:
    r = _run(["git", "stash", "pop"], cwd=path)
    return r.returncode == 0, r.stdout + r.stderr
