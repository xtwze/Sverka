"""Сценарий сверки источника с PostgreSQL."""

from source.clients.onec_client import OneCClient
from source.domain.reconciliation import reconcile_charges
from source.dto.response_dto import ReconciliationResponse
from source.dto.source_dto import PERIOD_PATTERN
from source.repositories.account_repository import AccountRepository
from source.repositories.charge_repository import ChargeRepository
from source.repositories.database import Database


class ReconciliationService:
    def __init__(
        self,
        source: OneCClient,
        database: Database,
        accounts: AccountRepository,
        charges: ChargeRepository,
    ):
        self.source = source
        self.database = database
        self.accounts = accounts
        self.charges = charges

    def reconcile(self, period: str) -> ReconciliationResponse:
        if not PERIOD_PATTERN.fullmatch(period):
            raise ValueError("Period must use YYYY-MM")
        snapshot = self.source.fetch_snapshot()
        with self.database.connection() as connection:
            postgres_rows = self.charges.for_period(connection, period)
            account_numbers = self.accounts.numbers(connection)
        account_numbers.update({row.id: row.account_number for row in snapshot.accounts})
        report = reconcile_charges(period, snapshot.charges, postgres_rows, account_numbers)
        return ReconciliationResponse.model_validate(report)
