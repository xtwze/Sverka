from fastapi.testclient import TestClient

from source.clients.onec_client import SourceUnavailable
from source.config.dependencies import get_reconciliation_service
from source.main import app, create_app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_invalid_period_is_rejected_before_reconciliation():
    response = client.get("/api/reconcile", params={"period": "2026-13"})
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
