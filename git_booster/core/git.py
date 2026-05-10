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


# Alias for tests
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


# Alias for tests
def get_staged_diff(path: Optional[str] = None) -> str:
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


# Alias for tests — accepts optional file arg
def git_add(file: Optional[str] = None, path: Optional[str] = None) -> None:
    if file:
        add([file], path)
    else:
        add_all(path)


def commit(message: str, path: Optional[str] = None) -> str:
    result = _run(["git", "commit", "-m", message], cwd=path)
    return result.stdout.strip()


# Alias for tests — returns CompletedProcess
def git_commit(message: str, path: Optional[str] = None) -> subprocess.CompletedProcess:
    return _run(["git", "commit", "-m", message], cwd=path, check=False)


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


# Alias for tests
def get_conflicts(path: Optional[str] = None) -> list[str]:
    return get_conflict_files(path)


def read_conflict_file(filepath: str, repo_root: Optional[str] = None) -> str:
    base = repo_root or os.getcwd()
    full_path = Path(base) / filepath
    return full_path.read_text(encoding="utf-8", errors="replace")


def write_resolved_file(filepath: str, content: str, repo_root: Optional[str] = None) -> None:
    base = repo_root or os.getcwd()
    full_path = Path(base) / filepath
    full_path.write_text(content, encoding="utf-8")


def mark_resolved(filepath: str, path: Optional[str] = None) -> None:
    _run(["git", "add", filepath], cwd=path)


def get_log(n: int = 10, path: Optional[str] = None) -> str:
    result = _run(
        ["git", "log", f"-{n}", "--oneline", "--decorate"],
        cwd=path,
        check=False,
    )
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def get_branch(path: Optional[str] = None) -> str:
    result = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=path, check=False)
    if result.returncode == 0 and result.stdout.strip() not in ("", "HEAD"):
        return result.stdout.strip()
    repo_root = get_repo_root(path)
    head_file = Path(repo_root) / ".git" / "HEAD"
    if head_file.exists():
        content = head_file.read_text().strip()
        if content.startswith("ref: refs/heads/"):
            return content.replace("ref: refs/heads/", "")
    return "unknown"


# Alias for tests
def get_current_branch(path: Optional[str] = None) -> str:
    return get_branch(path)


def list_untracked_files(path: Optional[str] = None) -> list[str]:
    result = _run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=path,
    )
    return result.stdout.splitlines()


def is_tracked(filepath: str, path: Optional[str] = None) -> bool:
    result = _run(["git", "ls-files", "--error-unmatch", filepath], cwd=path, check=False)
    return result.returncode == 0


def rm_file(filepath: str, path: Optional[str] = None, force: bool = False, cached: bool = False) -> None:
    args = ["git", "rm"]
    if force:
        args.append("-f")
    if cached:
        args.append("--cached")
    args.append(filepath)
    _run(args, cwd=path)


def push(remote: str = "origin", branch: str = "", set_upstream: bool = False,
         path: Optional[str] = None) -> tuple[bool, str]:
    args = ["git", "push"]
    if set_upstream:
        args += ["-u", remote, branch or get_branch(path)]
    elif branch:
        args += [remote, branch]
    else:
        args += [remote]
    result = _run(args, cwd=path, check=False)
    out = (result.stdout + result.stderr).strip()
    return result.returncode == 0, out


# Alias for tests — returns CompletedProcess
def git_push(branch: Optional[str] = None, remote: str = "origin",
             path: Optional[str] = None) -> subprocess.CompletedProcess:
    args = ["git", "push", remote]
    if branch:
        args.append(branch)
    return _run(args, cwd=path, check=False)


# Push error categories
PUSH_ERR_FETCH_FIRST   = "fetch_first"
PUSH_ERR_NO_UPSTREAM   = "no_upstream"
PUSH_ERR_REFSPEC       = "refspec"
PUSH_ERR_REJECTED      = "rejected"
PUSH_ERR_AUTH          = "auth"
PUSH_ERR_NO_REMOTE     = "no_remote"
PUSH_ERR_UNKNOWN       = "unknown"


def parse_push_error(output: str) -> str:
    low = output.lower()
    if ("authentication failed" in low or "could not read username" in low
            or "permission denied" in low or "access denied" in low):
        return PUSH_ERR_AUTH
    if ("repository not found" in low
            or "does not appear to be a git repository" in low
            or "could not resolve host" in low
            or "connection refused" in low):
        return PUSH_ERR_NO_REMOTE
    if ("no upstream branch" in low or "--set-upstream" in low
            or "set-upstream" in low):
        return PUSH_ERR_NO_UPSTREAM
    if ("src refspec" in low or "does not match any" in low
            or "invalid refspec" in low):
        return PUSH_ERR_REFSPEC
    if ("fetch first" in low
            or ("updates were rejected" in low and "behind" in low)
            or ("updates were rejected" in low and "fetch first" in low)):
        return PUSH_ERR_FETCH_FIRST
    if "non-fast-forward" in low:
        return PUSH_ERR_REJECTED
    if "rejected" in low:
        return PUSH_ERR_FETCH_FIRST
    return PUSH_ERR_UNKNOWN


def list_remote_branches(remote: str = "origin", path: Optional[str] = None) -> list[str]:
    result = _run(["git", "branch", "-r"], cwd=path, check=False)
    branches = []
    prefix = f"{remote}/"
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith(prefix) and "HEAD" not in line:
            branches.append(line[len(prefix):])
    return branches


def set_upstream(remote: str, branch: str, path: Optional[str] = None) -> tuple[bool, str]:
    result = _run(
        ["git", "push", "--set-upstream", remote, branch],
        cwd=path, check=False,
    )
    out = (result.stdout + result.stderr).strip()
    return result.returncode == 0, out


def fetch(remote: str = "origin", path: Optional[str] = None) -> tuple[bool, str]:
    result = _run(["git", "fetch", remote], cwd=path, check=False)
    return result.returncode == 0, result.stderr.strip()


def get_remote(path: Optional[str] = None) -> str | None:
    result = _run(["git", "remote"], cwd=path, check=False)
    remotes = [r for r in result.stdout.splitlines() if r.strip()]
    return remotes[0] if remotes else None


# Alias for tests
def get_remote_url(remote: str = "origin", path: Optional[str] = None) -> Optional[str]:
    result = _run(["git", "remote", "get-url", remote], cwd=path, check=False)
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def is_behind_remote(branch: str, remote: str = "origin", path: Optional[str] = None) -> bool:
    result = _run(
        ["git", "rev-list", "--count", f"HEAD..{remote}/{branch}"],
        cwd=path, check=False,
    )
    if result.returncode != 0:
        return False
    try:
        return int(result.stdout.strip()) > 0
    except ValueError:
        return False


def is_ahead_of_remote(branch: str, remote: str = "origin", path: Optional[str] = None) -> bool:
    result = _run(
        ["git", "rev-list", "--count", f"{remote}/{branch}..HEAD"],
        cwd=path, check=False,
    )
    if result.returncode != 0:
        return False
    try:
        return int(result.stdout.strip()) > 0
    except ValueError:
        return False


def pull(remote: str = "origin", branch: str = "HEAD", rebase: bool = False,
         path: Optional[str] = None) -> tuple[bool, str]:
    args = ["git", "pull", remote, branch]
    if rebase:
        args.insert(2, "--rebase")
    result = _run(args, cwd=path, check=False)
    out = (result.stdout + result.stderr).strip()
    return result.returncode == 0, out


# Alias for tests — returns CompletedProcess
def git_pull(strategy: str = "merge", path: Optional[str] = None) -> subprocess.CompletedProcess:
    args = ["git", "pull"]
    if strategy == "rebase":
        args.append("--rebase")
    return _run(args, cwd=path, check=False)


def has_uncommitted_changes(path: Optional[str] = None) -> bool:
    result = _run(["git", "status", "--porcelain"], cwd=path, check=False)
    return bool(result.stdout.strip())


def stash_push(message: str = "gai-resolve-autostash", path: Optional[str] = None) -> tuple[bool, str]:
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
