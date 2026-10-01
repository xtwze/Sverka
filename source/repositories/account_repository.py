"""Хранение лицевых счетов."""

import psycopg

from source.domain.models import Account
from source.repositories.common import delete_absent


class AccountRepository:
    def upsert_all(self, connection: psycopg.Connection, accounts: tuple[Account, ...]) -> None:
        connection.cursor().executemany(
            """INSERT INTO accounts(id, account_number) VALUES (%s, %s)
               ON CONFLICT (id) DO UPDATE SET account_number = EXCLUDED.account_number""",
            [(row.id, row.account_number) for row in accounts],
        )

    def delete_absent(
        self, connection: psycopg.Connection, accounts: tuple[Account, ...]
    ) -> None:
        delete_absent(connection, "accounts", (row.id for row in accounts))

    def numbers(self, connection: psycopg.Connection) -> dict[str, str]:
        rows = connection.execute("SELECT id, account_number FROM accounts").fetchall()
        return dict(rows)
