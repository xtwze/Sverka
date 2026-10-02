"""Проверки повторного импорта и отказа источника."""

import json
import os
from pathlib import Path
from unittest.mock import Mock
from uuid import uuid4

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg import sql
from psycopg.conninfo import make_conninfo

from scripts.discrepancy import fixture_charges, introduce, restore
from source.clients.onec_client import SourceUnavailable
from source.config.dependencies import get_import_service
from source.domain.reconciliation import reconcile_charges
from source.dto.source_dto import parse_snapshot
from source.main import create_app
from source.repositories.account_repository import AccountRepository
from source.repositories.charge_repository import ChargeRepository
from source.repositories.database import Database
from source.repositories.payment_repository import PaymentRepository
from source.services.import_service import ImportService


def _fixture_snapshot():
    payload = json.loads((Path(__file__).parent.parent / "fixtures/data.json").read_text())
    return parse_snapshot(payload)


def _stored_rows(database: Database) -> tuple:
    with database.connection() as connection:
        return (
            connection.execute("SELECT id, account_number FROM accounts ORDER BY id").fetchall(),
            connection.execute(
                "SELECT id, account_id, period, amount_kopecks FROM charges ORDER BY id"
            ).fetchall(),
            connection.execute(
                "SELECT id, account_id, payment_date, amount_kopecks "
                "FROM payments ORDER BY id"
            ).fetchall(),
        )


@pytest.fixture
def isolated_database():
    """Каждый тест пишет только во временную схему отдельной тестовой базы."""
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("Set TEST_DATABASE_URL to run the isolated PostgreSQL import test")

    schema = f"test_import_{uuid4().hex}"
    with psycopg.connect(base_url) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
    try:
        database = Database(make_conninfo(base_url, options=f"-c search_path={schema}"))
        yield database
    finally:
        with psycopg.connect(base_url) as connection:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_repeated_import_keeps_ids_links_and_exact_amounts(isolated_database):
    database = isolated_database
    source = Mock()
    source.fetch_snapshot.return_value = _fixture_snapshot()
    service = ImportService(
        source, database, AccountRepository(), ChargeRepository(), PaymentRepository()
    )
    first_result = service.import_data()
    first_rows = _stored_rows(database)
    second_result = service.import_data()
    second_rows = _stored_rows(database)
    assert first_result == second_result
    assert (len(first_rows[0]), len(first_rows[1]), len(first_rows[2])) == (2, 4, 1)
    assert second_rows == first_rows
    assert first_rows[1][1] == ("charge-2", "acc-alice", "2026-08", 24950)
    assert first_rows[2][0][0:2] == ("payment-1", "acc-alice")
    assert source.fetch_snapshot.call_count == 2


def test_discrepancy_script_and_restore_roundtrip(isolated_database):
    database = isolated_database
    snapshot = _fixture_snapshot()
    source = Mock()
    source.fetch_snapshot.return_value = snapshot
    ImportService(source, database, AccountRepository(), ChargeRepository(),
                  PaymentRepository()).import_data()
    before = _stored_rows(database)
    with database.transaction() as connection:
        introduce(connection, fixture_charges())
    with database.connection() as connection:
        rows = ChargeRepository().for_period(connection, "2026-08")
    report = reconcile_charges("2026-08", snapshot.charges, rows, {})
    assert [(row["record_id"], row["type"], row["source_value"], row["postgres_value"])
            for row in report["differences"]] == [
        ("charge-2", "amount_mismatch", 24950, 25050),
        ("charge-3", "missing_in_postgres", 990000, None),
    ]
    assert report["postgres"] == {"count": 2, "total_kopecks": 150100}
    with database.transaction() as connection:
        restore(connection, fixture_charges())
    assert _stored_rows(database) == before


def test_unavailable_source_does_not_start_database_import():
    source = Mock()
    source.fetch_snapshot.side_effect = SourceUnavailable("Source request failed")
    database = Mock()
    service = ImportService(source, database, Mock(), Mock(), Mock())

    with pytest.raises(SourceUnavailable, match="Source request failed"):
        service.import_data()

    database.initialize.assert_not_called()
    database.transaction.assert_not_called()


def test_unavailable_source_returns_error_instead_of_success():
    service = Mock()
    service.import_data.side_effect = SourceUnavailable("Source request failed")
    app = create_app()
    app.dependency_overrides[get_import_service] = lambda: service
    try:
        response = TestClient(app).post("/api/import")
        assert response.status_code == 502
        assert "Source request failed" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()
