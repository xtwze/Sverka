"""Соединение с PostgreSQL и граница транзакции."""

from collections.abc import Iterator
from contextlib import contextmanager

import psycopg

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

    @contextmanager
    def transaction(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self.url) as connection:
            connection.execute("SELECT pg_advisory_xact_lock(20260801)")
            yield connection

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self.url) as connection:
            yield connection
