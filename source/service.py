"""Сценарии приложения, используемые HTTP API и CLI."""

from source.database import Database
from source.models import PERIOD_PATTERN
from source.reconciliation import reconcile_charges
from source.source_client import SourceClient


class ReconciliationService:
    def __init__(self, source: SourceClient, database: Database):
        self.source = source
        self.database = database

    def import_data(self) -> dict[str, int]:
        snapshot = self.source.fetch_snapshot()
        self.database.initialize()
        return self.database.replace_snapshot(snapshot)

    def reconcile(self, period: str) -> dict:
        if not PERIOD_PATTERN.fullmatch(period):
            raise ValueError("Period must use YYYY-MM")
        snapshot = self.source.fetch_snapshot()
        postgres_rows = self.database.charges_for_period(period)
        account_numbers = {row.id: row.account_number for row in snapshot.accounts}
        account_numbers.update(self.database.account_numbers())
        return reconcile_charges(period, snapshot.charges, postgres_rows, account_numbers)
