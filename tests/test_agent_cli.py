from unittest.mock import Mock

import pytest

from source.agent import cli
from source.agent.routerai import ModelResponseError


@pytest.mark.parametrize("fails", [False, True])
def test_cli_closes_agent_on_success_and_failure(monkeypatch, capsys, fails):
    agent = Mock()
    agent.ask.return_value = "Совпадает."
    if fails:
        agent.ask.side_effect = ModelResponseError("Provider failed")
    monkeypatch.setattr(cli, "get_agent_tools", Mock())
    monkeypatch.setattr(cli.RouterAIAgent, "from_env", lambda tools: agent)
    monkeypatch.setattr("sys.argv", ["agent", "Сверь 2026-08"])

    if fails:
        with pytest.raises(ModelResponseError):
            cli.main()
    else:
        assert cli.main() == 0
        assert capsys.readouterr().out.strip() == "Совпадает."
    agent.close.assert_called_once_with()
