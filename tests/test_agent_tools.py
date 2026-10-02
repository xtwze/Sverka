from datetime import date
from unittest.mock import Mock

import pytest
from langchain_core.tools import BaseTool

from source.agent.dependencies import get_agent_tools
from source.agent.tools import AgentTools, ToolInputError, UnknownToolError
from source.domain.models import Charge, Payment, SourceSnapshot
from source.dto.response_dto import ReconciliationResponse


def report() -> ReconciliationResponse:
    return ReconciliationResponse(
        run_id="test-run",
        period="2026-08",
        status="MATCH",
        source={"count": 3, "total_kopecks": 1140000},
        postgres={"count": 3, "total_kopecks": 1140000},
        differences=[],
    )


def test_only_allowed_tool_calls_shared_service():
    service = Mock()
    service.reconcile.return_value = report()
    tools = AgentTools(service, Mock(), Mock(), Mock())

    assert tools.names == (
        "read_onec_charges",
        "read_postgres_charges",
        "reconcile_charges",
        "summarize_payments",
    )
    result = tools.invoke("reconcile_charges", {"period": "2026-08"})

    service.reconcile.assert_called_once_with("2026-08")
    assert result["status"] == "MATCH"
    assert result["source"]["total_kopecks"] == 1140000


def test_decorated_tool_schema_is_used_for_model_calls():
    tools = AgentTools(Mock(), Mock(), Mock(), Mock())
    assert all(isinstance(item, BaseTool) for item in tools._handlers.values())

    function = tools.model_spec("reconcile_charges")["function"]
    assert function["name"] == "reconcile_charges"
    assert function["parameters"]["required"] == ["period"]
    assert function["parameters"]["additionalProperties"] is False
    assert set(function["parameters"]["properties"]) == {"period"}
    with pytest.raises(UnknownToolError):
        tools.model_spec("import_data")


def test_unknown_tool_and_invalid_input_never_reach_service():
    service = Mock()
    tools = AgentTools(service, Mock(), Mock(), Mock())

    with pytest.raises(UnknownToolError):
        tools.invoke("import_data", {})
    with pytest.raises(ToolInputError):
        tools.invoke("reconcile_charges", {"period": "2026-13"})
    with pytest.raises(ToolInputError):
        tools.invoke("reconcile_charges", {"period": "2026-08", "sql": "DELETE"})

    service.reconcile.assert_not_called()


def test_source_error_is_not_reported_as_match():
    service = Mock()
    service.reconcile.side_effect = RuntimeError("Source unavailable")

    with pytest.raises(RuntimeError, match="Source unavailable"):
        AgentTools(service, Mock(), Mock(), Mock()).invoke(
            "reconcile_charges", {"period": "2026-08"}
        )


def test_read_tools_return_filtered_rows_and_totals():
    source = Mock()
    source.fetch_snapshot.return_value = SourceSnapshot(
        accounts=(),
        charges=(
            Charge("august", "account", "2026-08", 125050),
            Charge("september", "account", "2026-09", 5000),
        ),
        payments=(),
    )
    database = Mock()
    database.connection.return_value.__enter__ = Mock(return_value=Mock())
    database.connection.return_value.__exit__ = Mock(return_value=None)
    charges = Mock()
    charges.for_period.return_value = (Charge("august", "account", "2026-08", 125050),)
    tools = AgentTools(Mock(), source, database, charges)

    onec = tools.invoke("read_onec_charges", {"period": "2026-08"})
    postgres = tools.invoke("read_postgres_charges", {"period": "2026-08"})

    assert onec["source"] == "onec"
    assert postgres["source"] == "postgres"
    assert onec["total_kopecks"] == postgres["total_kopecks"] == 125050
    assert onec["rows"] == postgres["rows"]
    assert [row["id"] for row in onec["rows"]] == ["august"]


def test_agent_requires_separate_database_url(monkeypatch):
    monkeypatch.delenv("AGENT_DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError, match="AGENT_DATABASE_URL"):
        get_agent_tools()


@pytest.mark.parametrize("name", ["DATABASE_URL", "IMPORTER_PASSWORD"])
def test_agent_refuses_importer_environment(monkeypatch, name):
    monkeypatch.setenv("AGENT_DATABASE_URL", "postgresql://agent_reader:reader@localhost/reporting")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("IMPORTER_PASSWORD", raising=False)
    monkeypatch.setenv(name, "writer-secret")
    with pytest.raises(RuntimeError, match=f"Remove {name}"):
        get_agent_tools()


def test_agent_refuses_writer_role_and_does_not_store_writer_settings(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AGENT_DATABASE_URL", "postgresql://importer:writer@localhost/reporting")
    with pytest.raises(RuntimeError, match="agent_reader"):
        get_agent_tools()
    monkeypatch.setenv("AGENT_DATABASE_URL", "postgresql://agent_reader:reader@localhost/reporting")
    tools = get_agent_tools()
    assert not hasattr(tools._source.settings, "database_url")


def test_payment_summary_filters_selected_month_and_uses_reader_connection():
    source = Mock()
    source.fetch_snapshot.return_value = SourceSnapshot(
        accounts=(), charges=(), payments=(
            Payment("august", "account", date(2026, 8, 20), 100000),
            Payment("september", "account", date(2026, 9, 1), 5000),
        ),
    )
    connection = Mock()
    connection.execute.return_value.fetchone.return_value = (1, 100000)
    database = Mock()
    database.connection.return_value = Mock()
    database.connection.return_value.__enter__ = Mock(return_value=connection)
    database.connection.return_value.__exit__ = Mock(return_value=None)
    tools = AgentTools(Mock(), source, database, Mock())

    assert tools.invoke("summarize_payments", {"period": "2026-08"}) == {
        "period": "2026-08",
        "source": {"count": 1, "total_kopecks": 100000},
        "postgres": {"count": 1, "total_kopecks": 100000},
    }
    assert connection.execute.call_args.args[1] == ("2026-08", "2026-08")
