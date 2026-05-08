import pytest
from unittest.mock import patch
from click.testing import CliRunner
from git_booster.cli import main as cli


class TestCommitCommand:
    def test_commit_generates_message(self, tmp_git_repo, monkeypatch):
        monkeypatch.chdir(tmp_git_repo)
        (tmp_git_repo / "app.py").write_text("print('hello')")

        import subprocess
        subprocess.run(["git", "add", "."], cwd=tmp_git_repo)

        runner = CliRunner()
        with patch("git_booster.commands.commit.ai.ask") as mock_ai:
            mock_ai.return_value = "feat(app): add hello world script"
            # Simuler "commit" puis "n" pour ne pas push
            result = runner.invoke(cli, ["commit"], input="commit\nn\n")

        assert result.exit_code == 0
        assert "feat(app)" in result.output

    def test_commit_abort(self, tmp_git_repo, monkeypatch):
        monkeypatch.chdir(tmp_git_repo)
        (tmp_git_repo / "b.py").write_text("z = 3")

        import subprocess
        subprocess.run(["git", "add", "."], cwd=tmp_git_repo)

        runner = CliRunner()
        with patch("git_booster.commands.commit.ai.ask") as mock_ai:
            mock_ai.return_value = "chore: update b"
            result = runner.invoke(cli, ["commit"], input="abort\n")

        assert result.exit_code == 0
        assert "abort" in result.output.lower() or "Aborted" in result.output
