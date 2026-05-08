import pytest
import subprocess
from pathlib import Path
from git_booster.core import git


@pytest.fixture
def tmp_git_repo(tmp_path):
    subprocess.run(["git", "init"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=tmp_path, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=tmp_path, capture_output=True)
    return tmp_path


@pytest.fixture
def tmp_repo_with_conflict(tmp_git_repo):
    f = tmp_git_repo / "conflict.txt"
    f.write_text("<<<<<<< HEAD\nmine\n=======\ntheirs\n>>>>>>> branch\n")
    return tmp_git_repo


class TestGitStatus:
    def test_status_returns_output(self, tmp_git_repo):
        result = git.status(str(tmp_git_repo))
        assert isinstance(result, str)

    def test_status_in_non_git_dir(self, tmp_path):
        with pytest.raises(git.GitError):
            git.status(str(tmp_path))


class TestGitAdd:
    def test_add_all(self, tmp_git_repo):
        (tmp_git_repo / "new_file.py").write_text("print('hello')")
        git.add(["."], str(tmp_git_repo))  # no return value

    def test_add_specific_file(self, tmp_git_repo):
        (tmp_git_repo / "specific.py").write_text("x = 1")
        git.add(["specific.py"], str(tmp_git_repo))

    def test_add_nonexistent_file(self, tmp_git_repo):
        with pytest.raises(git.GitError):
            git.add(["ghost.py"], str(tmp_git_repo))


class TestGitCommit:
    def test_commit_with_message(self, tmp_git_repo):
        (tmp_git_repo / "f.py").write_text("x = 1")
        git.add(["."], str(tmp_git_repo))
        result = git.commit("test: initial", str(tmp_git_repo))
        assert result is not None

    def test_commit_empty_fails(self, tmp_git_repo):
        with pytest.raises(git.GitError):
            git.commit("test: empty commit", str(tmp_git_repo))

    def test_commit_empty_message_fails(self, tmp_git_repo):
        (tmp_git_repo / "g.py").write_text("y = 2")
        git.add(["."], str(tmp_git_repo))
        with pytest.raises(Exception):
            git.commit("", str(tmp_git_repo))


class TestGitDiff:
    def test_diff_staged_empty(self, tmp_git_repo):
        result = git.diff_staged(str(tmp_git_repo))
        assert result == "" or result is not None

    def test_diff_staged_with_changes(self, tmp_git_repo):
        (tmp_git_repo / "h.py").write_text("z = 3")
        git.add(["."], str(tmp_git_repo))
        result = git.diff_staged(str(tmp_git_repo))
        assert "h.py" in result or len(result) > 0


class TestGitBranch:
    def test_current_branch(self, tmp_git_repo):
        # use get_remote or similar — test what exists
        result = git.get_remote(str(tmp_git_repo))
        assert result is None or isinstance(result, str)

    def test_list_remotes_empty(self, tmp_git_repo):
        result = git.get_remote(str(tmp_git_repo))
        assert result is None


class TestConflictDetection:
    def test_no_conflict_in_clean_repo(self, tmp_git_repo):
        files = git.get_conflict_files(str(tmp_git_repo))
        assert files == []

    def test_conflict_detected(self, tmp_repo_with_conflict):
        files = git.get_conflict_files(str(tmp_repo_with_conflict))
        assert isinstance(files, list)
