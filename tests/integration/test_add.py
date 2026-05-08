content = '''\
import pytest
from unittest.mock import patch
from click.testing import CliRunner
from git_booster.cli import cli


class TestAddCommand:
    def test_add_all_no_ai(self, tmp_git_repo, monkeypatch):
        monkeypatch.chdir(tmp_git_repo)
        (tmp_git_repo / "new.py").write_text("x = 1")

        runner = CliRunner()
        with patch("git_booster.commands.add.ai.ask") as mock_ai:
            mock_ai.return_value = "__pycache__/\\n*.pyc\\n.venv/\\n"
            result = runner.invoke(cli, ["add"], input="y\\n")

        assert result.exit_code == 0

    def test_add_specific_file(self, tmp_git_repo, monkeypatch):
        monkeypatch.chdir(tmp_git_repo)
        (tmp_git_repo / "specific.py").write_text("y = 2")

        runner = CliRunner()
        with patch("git_booster.commands.add.ai.ask") as mock_ai:
            mock_ai.return_value = "*.pyc\\n"
            result = runner.invoke(cli, ["add", "specific.py"], input="y\\n")

        assert result.exit_code == 0
'''

with open("test_add.py", "w") as f:
    f.write(content)
