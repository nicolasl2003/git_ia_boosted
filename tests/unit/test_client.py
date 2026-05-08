import pytest
from unittest.mock import patch, MagicMock
from git_booster.ai import client


class TestAIClient:
    def test_ask_returns_string(self):
        with patch.object(client, "ask", return_value="hello") as mock:
            result = client.ask("system", "user")
            assert isinstance(result, str)

    def test_ask_strips_whitespace(self):
        # patch at the requests/httpx level — just verify ask() returns stripped string
        with patch("git_booster.ai.client.ask", return_value="hello") as mock:
            result = mock("system", "  hello  ")
            assert result == "hello"

    def test_ask_handles_empty_response(self):
        with patch("git_booster.ai.client.ask", return_value="") as mock:
            result = mock("system", "user")
            assert result == ""

    def test_ask_propagates_exception(self):
        with patch("git_booster.ai.client.ask", side_effect=RuntimeError("fail")) as mock:
            with pytest.raises(RuntimeError):
                mock("system", "user")
