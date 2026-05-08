import pytest
from git_booster.ai import prompts


class TestCommitPrompt:
    def test_returns_tuple(self):
        result = prompts.commit_prompt("diff --git a/f.py\n+x = 1", "M  f.py")
        assert isinstance(result, tuple) and len(result) == 2

    def test_diff_in_prompt(self):
        diff = "diff --git a/main.py\n+print('hello')"
        system, user = prompts.commit_prompt(diff, "M  main.py")
        assert "main.py" in user or "diff" in user

    def test_empty_diff(self):
        system, user = prompts.commit_prompt("", "")
        assert isinstance(system, str)
        assert isinstance(user, str)


class TestConflictPrompt:
    def test_returns_tuple(self):
        result = prompts.conflict_prompt("file.py", "<<<<<<\nmine\n=====\ntheirs\n>>>>>>")
        assert isinstance(result, tuple) and len(result) == 2

    def test_filepath_in_prompt(self):
        system, user = prompts.conflict_prompt("src/main.py", "conflict content")
        assert "src/main.py" in user or "src/main.py" in system

    def test_conflict_content_in_prompt(self):
        system, user = prompts.conflict_prompt("f.py", "<<<<<<\nA\n======\nB\n>>>>>>")
        assert "<<<<<<" in user or "A" in user


class TestGitignorePrompt:
    def test_returns_tuple(self):
        result = prompts.gitignore_rules_prompt(["__pycache__", ".env"], "", ["__pycache__", ".env"])
        assert isinstance(result, tuple) and len(result) == 2

    def test_files_in_prompt(self):
        files = ["node_modules", ".DS_Store"]
        system, user = prompts.gitignore_rules_prompt(files, "", files)
        assert any(f in user for f in files)




