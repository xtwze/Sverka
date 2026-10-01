"""Общие операции репозиториев."""

from collections.abc import Iterable

import psycopg


def delete_absent(
    connection: psycopg.Connection, table: str, identifiers: Iterable[str]
) -> None:
    values = list(identifiers)
    if values:
        connection.execute(f"DELETE FROM {table} WHERE NOT (id = ANY(%s))", (values,))
    else:
        connection.execute(f"DELETE FROM {table}")
