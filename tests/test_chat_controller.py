from unittest.mock import Mock

from fastapi.testclient import TestClient

from source.agent.main import create_app
from source.agent.routerai import RouterAIAgent
from source.controllers.chat_controller import get_chat_tools


def test_agent_app_has_no_import_endpoint():
    client = TestClient(create_app())
    assert client.post("/api/import").status_code == 404


def test_web_chat_passes_selected_period_to_agent(monkeypatch):
    app = create_app()
    app.dependency_overrides[get_chat_tools] = lambda: Mock()
    agent = Mock()
    agent.ask_for_period.return_value = "Расхождений нет."
    monkeypatch.setattr(RouterAIAgent, "from_env", lambda tools: agent)

    response = TestClient(app).post(
        "/api/agent/chat", json={"period": "2026-08", "message": "Что с начислениями?"}
    )

    assert response.status_code == 200
    assert response.json() == {"answer": "Расхождений нет."}
    agent.ask_for_period.assert_called_once_with("Что с начислениями?", "2026-08")
    app.dependency_overrides.clear()


def test_web_chat_rejects_invalid_month_and_blank_question():
    app = create_app()
    app.dependency_overrides[get_chat_tools] = lambda: Mock()
    client = TestClient(app)
    assert client.post("/api/agent/chat", json={"period": "2026-13", "message": "Тест"}).status_code == 422
    assert client.post("/api/agent/chat", json={"period": "2026-08", "message": "  "}).status_code == 422
    app.dependency_overrides.clear()
