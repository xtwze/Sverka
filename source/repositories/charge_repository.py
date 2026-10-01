"""Хранение начислений."""

import psycopg

from source.domain.models import Charge
from source.repositories.common import delete_absent


class ChargeRepository:
    def upsert_all(self, connection: psycopg.Connection, charges: tuple[Charge, ...]) -> None:
        connection.cursor().executemany(
            """INSERT INTO charges(id, account_id, period, amount_kopecks)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET account_id = EXCLUDED.account_id,
                   period = EXCLUDED.period, amount_kopecks = EXCLUDED.amount_kopecks""",
            [(row.id, row.account_id, row.period, row.amount_kopecks) for row in charges],
        )

    def delete_absent(self, connection: psycopg.Connection, charges: tuple[Charge, ...]) -> None:
        delete_absent(connection, "charges", (row.id for row in charges))

    def for_period(self, connection: psycopg.Connection, period: str) -> tuple[Charge, ...]:
        rows = connection.execute(
            """SELECT id, account_id, period, amount_kopecks
               FROM charges WHERE period = %s ORDER BY id""",
            (period,),
        ).fetchall()
        return tuple(Charge(*row) for row in rows)
