"""Вносит или устраняет два расхождения только в тестовой PostgreSQL."""

import argparse
import json
import os
from pathlib import Path

import psycopg

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "data.json"
AMOUNT_ID = "charge-2"
MISSING_ID = "charge-3"


def fixture_charges() -> dict[str, dict]:
    rows = json.loads(FIXTURES.read_text())["charges"]
    return {row["id"]: row for row in rows if row["id"] in (AMOUNT_ID, MISSING_ID)}


def introduce(connection: psycopg.Connection, fixtures: dict[str, dict]) -> None:
    """Проверяет исходное состояние до изменения двух записей в одной транзакции."""
    rows = connection.execute(
        """SELECT id, account_id, period, amount_kopecks
           FROM charges WHERE id IN (%s, %s) FOR UPDATE""",
        (AMOUNT_ID, MISSING_ID),
    ).fetchall()
    expected = {
        identifier: (
            fixture["account_id"],
            fixture["period"],
            fixture["amount_kopecks"],
        )
        for identifier, fixture in fixtures.items()
    }
    actual = {identifier: tuple(values) for identifier, *values in rows}
    if actual != expected:
        raise RuntimeError("Expected original fixture rows; restore or import before introducing")
    connection.execute(
        "UPDATE charges SET amount_kopecks = %s WHERE id = %s",
        (fixtures[AMOUNT_ID]["amount_kopecks"] + 100, AMOUNT_ID),
    )
    connection.execute("DELETE FROM charges WHERE id = %s", (MISSING_ID,))


def restore(connection: psycopg.Connection, fixtures: dict[str, dict]) -> None:
    """Восстанавливает только две выбранные записи из неизменённых фикстур."""
    for identifier in (AMOUNT_ID, MISSING_ID):
        row = fixtures[identifier]
        connection.execute(
            """INSERT INTO charges (id, account_id, period, amount_kopecks)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET
                   account_id = EXCLUDED.account_id,
                   period = EXCLUDED.period,
                   amount_kopecks = EXCLUDED.amount_kopecks""",
            (row["id"], row["account_id"], row["period"], row["amount_kopecks"]),
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("introduce", "restore"))
    args = parser.parse_args()
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://importer:demo-importer-local@localhost:5543/reporting",
    )
    fixtures = fixture_charges()
    if set(fixtures) != {AMOUNT_ID, MISSING_ID}:
        raise RuntimeError("Required charge fixtures are missing")
    with psycopg.connect(database_url) as connection:
        if args.action == "introduce":
            introduce(connection, fixtures)
        else:
            restore(connection, fixtures)
    if args.action == "introduce":
        print(f"changed {AMOUNT_ID} amount by 100 kopecks; deleted {MISSING_ID}")
    else:
        print(f"restored {AMOUNT_ID} and {MISSING_ID} from fixtures")


if __name__ == "__main__":
    main()
