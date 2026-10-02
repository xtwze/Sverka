import json
from unittest.mock import patch

import httpx
import pytest
from fastapi.testclient import TestClient

from source.clients.onec_client import OneCClient, SourceUnavailable
from source.config.dependencies import get_reconciliation_service
from source.config.source_settings import SourceSettings
from source.dto.source_dto import SourceContractError
from source.main import app, create_app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_invalid_period_is_rejected_before_reconciliation():
    application = create_app()
    application.dependency_overrides[get_reconciliation_service] = lambda: None
    response = TestClient(application).get("/api/reconcile", params={"period": "2026-13"})
    assert response.status_code == 422


def test_source_failure_does_not_return_a_match_report():
    application = create_app()

    class UnavailableReconciliation:
        def reconcile(self, period: str):
            raise SourceUnavailable("Source request failed")

    application.dependency_overrides[get_reconciliation_service] = UnavailableReconciliation
    try:
        response = TestClient(application).get("/api/reconcile?period=2026-08")
        assert response.status_code == 502
        assert "MATCH" not in response.text
    finally:
        application.dependency_overrides.clear()


@pytest.mark.parametrize("payload", [None, [], {"value": [None]}, {"value": ["broken"]}])
def test_http_source_rejects_malformed_payload(payload):
    http = httpx.Client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=json.dumps(payload)),
    ))
    with patch("source.clients.onec_client.httpx.Client", return_value=http):
        with pytest.raises(SourceContractError):
            OneCClient(SourceSettings.from_env()).fetch_snapshot()


def test_http_network_failure_is_source_unavailable():
    def unavailable(request):
        raise httpx.ConnectError("offline", request=request)

    http = httpx.Client(transport=httpx.MockTransport(unavailable))
    with patch("source.clients.onec_client.httpx.Client", return_value=http):
        with pytest.raises(SourceUnavailable):
            OneCClient(SourceSettings.from_env()).fetch_snapshot()


def test_source_info_distinguishes_configured_modes(monkeypatch):
    monkeypatch.delenv("ONEC_BASE_URL", raising=False)
    assert client.get("/api/source-info").json() == {"mode": "mock"}
    monkeypatch.setenv("ONEC_BASE_URL", "http://onec.test/demo/hs/api")
    assert client.get("/api/source-info").json() == {"mode": "real"}
