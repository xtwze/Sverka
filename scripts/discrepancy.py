"""Вносит или устраняет контролируемое расхождение в отчётной PostgreSQL."""

import argparse
import os

import psycopg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("introduce", "restore"))
    args = parser.parse_args()
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql://importer:demo-importer-local@localhost:5543/reporting",
    )
    amount = 25050 if args.action == "introduce" else 24950
    with psycopg.connect(database_url) as connection:
        result = connection.execute(
            "UPDATE charges SET amount_kopecks = %s WHERE id = 'charge-2'",
            (amount,),
        )
        if result.rowcount != 1:
            raise RuntimeError("Run the import first: charge-2 was not found")
    print(f"charge-2 amount_kopecks={amount}")


if __name__ == "__main__":
    main()
