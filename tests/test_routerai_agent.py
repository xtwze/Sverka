import json
from unittest.mock import Mock

import httpx
import pytest

from source.agent.routerai import ModelResponseError, RouterAIAgent
from source.agent.tools import AgentTools
from source.dto.response_dto import ReconciliationResponse


def test_model_can_call_only_registered_tool_and_explain_its_result():
    requests = []

    def respond(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "type": "function",
                                        "function": {
                                            "name": "reconcile_charges",
                                            "arguments": '{"period":"2026-08"}',
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                },
            )
        return httpx.Response(200, json={"choices": [{"message": {"content": "Совпадает."}}]})

    service = Mock()
    service.reconcile.return_value = ReconciliationResponse(
        run_id="test",
        period="2026-08",
        status="MATCH",
        source={"count": 3, "total_kopecks": 1140000},
        postgres={"count": 3, "total_kopecks": 1140000},
        differences=[],
    )
    client = httpx.Client(transport=httpx.MockTransport(respond))
    agent = RouterAIAgent(AgentTools(service, Mock(), Mock(), Mock()), "test-key", client)

    assert agent.ask("Сверь август 2026") == "Совпадает."
    assert requests[0]["tools"][0]["function"]["name"] == "reconcile_charges"
    assert requests[1]["messages"][-1]["role"] == "tool"
    assert json.loads(requests[1]["messages"][-1]["content"])["status"] == "MATCH"
    service.reconcile.assert_called_once_with("2026-08")
    assert agent.trace == [{"name": "reconcile_charges",
                            "arguments": {"period": "2026-08"},
                            "output": json.loads(requests[1]["messages"][-1]["content"])}]
    assert "test-key" not in json.dumps(agent.trace)
    assert agent.ask("Какой период?") == "Укажите месяц сверки в формате YYYY-MM."
    assert agent.trace == []


def test_model_cannot_invoke_unlisted_operation():
    client = httpx.Client(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "tool_calls": [
                                    {
                                        "id": "call-1",
                                        "function": {"name": "import_data", "arguments": "{}"},
                                    }
                                ]
                            }
                        }
                    ]
                },
            )
        )
    )
    service = Mock()
    with pytest.raises(ModelResponseError, match="Invalid tool call"):
        RouterAIAgent(AgentTools(service, Mock(), Mock(), Mock()), "test-key", client).ask(
            "Импортируй данные"
        )
    service.reconcile.assert_not_called()


def test_web_agent_uses_only_server_facts_for_selected_month():
    requests = []
    def respond(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"choices": [{"message": {"content": "Один платёж."}}]})

    tools = Mock()
    tools.invoke.side_effect = [
        {"period": "2026-08", "status": "MATCH"},
        {"period": "2026-08", "source": {"count": 1}, "postgres": {"count": 1}},
    ]
    client = httpx.Client(transport=httpx.MockTransport(respond))
    agent = RouterAIAgent(tools, "test-key", client)
    assert agent.ask_for_period("Сколько платежей?", "2026-08") == "Один платёж."
    assert [call.args for call in tools.invoke.call_args_list] == [
        ("reconcile_charges", {"period": "2026-08"}),
        ("summarize_payments", {"period": "2026-08"}),
    ]
    assert "tools" not in requests[0]
    assert "payments_summary" in requests[0]["messages"][1]["content"]
