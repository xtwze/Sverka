from fastapi.testclient import TestClient

from source.app import app

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_invalid_period_is_rejected_before_reconciliation():
    response = client.get("/api/reconcile", params={"period": "2026-13"})
    assert response.status_code == 422
