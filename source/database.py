"""Доступ к отчётной PostgreSQL."""

from collections.abc import Iterable

import psycopg

from source.models import Charge, SourceSnapshot

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS accounts (
    id text PRIMARY KEY,
    account_number text NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS charges (
    id text PRIMARY KEY,
    account_id text NOT NULL REFERENCES accounts(id),
    period char(7) NOT NULL CHECK (period ~ '^[0-9]{4}-(0[1-9]|1[0-2])$'),
    amount_kopecks bigint NOT NULL
);
CREATE INDEX IF NOT EXISTS charges_period_idx ON charges(period);
CREATE TABLE IF NOT EXISTS payments (
    id text PRIMARY KEY,
    account_id text NOT NULL REFERENCES accounts(id),
    payment_date date NOT NULL,
    amount_kopecks bigint NOT NULL
);
"""


class Database:
    def __init__(self, url: str):
        self.url = url

    def initialize(self) -> None:
        with psycopg.connect(self.url) as connection:
            connection.execute(SCHEMA_SQL)

    def replace_snapshot(self, snapshot: SourceSnapshot) -> dict[str, int]:
        """Синхронизирует снимок в одной транзакции; повторный запуск безопасен."""
        with psycopg.connect(self.url) as connection:
            connection.execute("SELECT pg_advisory_xact_lock(20260801)")
            cursor = connection.cursor()
            cursor.executemany(
                """INSERT INTO accounts(id, account_number) VALUES (%s, %s)
                   ON CONFLICT (id) DO UPDATE SET account_number = EXCLUDED.account_number""",
                [(row.id, row.account_number) for row in snapshot.accounts],
            )
            cursor.executemany(
                """INSERT INTO charges(id, account_id, period, amount_kopecks)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET account_id = EXCLUDED.account_id,
                       period = EXCLUDED.period, amount_kopecks = EXCLUDED.amount_kopecks""",
                [
                    (row.id, row.account_id, row.period, row.amount_kopecks)
                    for row in snapshot.charges
                ],
            )
            cursor.executemany(
                """INSERT INTO payments(id, account_id, payment_date, amount_kopecks)
                   VALUES (%s, %s, %s, %s)
                   ON CONFLICT (id) DO UPDATE SET account_id = EXCLUDED.account_id,
                       payment_date = EXCLUDED.payment_date,
                       amount_kopecks = EXCLUDED.amount_kopecks""",
                [
                    (row.id, row.account_id, row.date, row.amount_kopecks)
                    for row in snapshot.payments
                ],
            )
            self._delete_absent(connection, "payments", (row.id for row in snapshot.payments))
            self._delete_absent(connection, "charges", (row.id for row in snapshot.charges))
            self._delete_absent(connection, "accounts", (row.id for row in snapshot.accounts))
        return {
            "accounts": len(snapshot.accounts),
            "charges": len(snapshot.charges),
            "payments": len(snapshot.payments),
        }

    @staticmethod
    def _delete_absent(connection: psycopg.Connection, table: str, ids: Iterable[str]) -> None:
        values = list(ids)
        if values:
            connection.execute(f"DELETE FROM {table} WHERE NOT (id = ANY(%s))", (values,))
        else:
            connection.execute(f"DELETE FROM {table}")

    def charges_for_period(self, period: str) -> tuple[Charge, ...]:
        with psycopg.connect(self.url) as connection:
            rows = connection.execute(
                """SELECT id, account_id, period, amount_kopecks
                   FROM charges WHERE period = %s ORDER BY id""",
                (period,),
            ).fetchall()
        return tuple(Charge(*row) for row in rows)

    def account_numbers(self) -> dict[str, str]:
        with psycopg.connect(self.url) as connection:
            rows = connection.execute("SELECT id, account_number FROM accounts").fetchall()
        return dict(rows)
