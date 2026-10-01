"""Сценарий атомарного импорта снимка источника."""

from source.clients.onec_client import OneCClient
from source.dto.response_dto import ImportResponse
from source.repositories.account_repository import AccountRepository
from source.repositories.charge_repository import ChargeRepository
from source.repositories.database import Database
from source.repositories.payment_repository import PaymentRepository


class ImportService:
    def __init__(
        self,
        source: OneCClient,
        database: Database,
        accounts: AccountRepository,
        charges: ChargeRepository,
        payments: PaymentRepository,
    ):
        self.source = source
        self.database = database
        self.accounts = accounts
        self.charges = charges
        self.payments = payments

    def import_data(self) -> ImportResponse:
        snapshot = self.source.fetch_snapshot()
        self.database.initialize()
        with self.database.transaction() as connection:
            self.accounts.upsert_all(connection, snapshot.accounts)
            self.charges.upsert_all(connection, snapshot.charges)
            self.payments.upsert_all(connection, snapshot.payments)
            self.payments.delete_absent(connection, snapshot.payments)
            self.charges.delete_absent(connection, snapshot.charges)
            self.accounts.delete_absent(connection, snapshot.accounts)
        return ImportResponse(
            accounts=len(snapshot.accounts),
            charges=len(snapshot.charges),
            payments=len(snapshot.payments),
        )
