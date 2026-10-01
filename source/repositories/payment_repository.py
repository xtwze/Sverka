"""Хранение платежей."""

import psycopg

from source.domain.models import Payment
from source.repositories.common import delete_absent


class PaymentRepository:
    def upsert_all(self, connection: psycopg.Connection, payments: tuple[Payment, ...]) -> None:
        connection.cursor().executemany(
            """INSERT INTO payments(id, account_id, payment_date, amount_kopecks)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (id) DO UPDATE SET account_id = EXCLUDED.account_id,
                   payment_date = EXCLUDED.payment_date,
                   amount_kopecks = EXCLUDED.amount_kopecks""",
            [(row.id, row.account_id, row.date, row.amount_kopecks) for row in payments],
        )

    def delete_absent(self, connection: psycopg.Connection, payments: tuple[Payment, ...]) -> None:
        delete_absent(connection, "payments", (row.id for row in payments))
