"""Сборка зависимостей приложения."""

from functools import lru_cache

from source.clients.onec_client import OneCClient
from source.config.settings import Settings
from source.repositories.account_repository import AccountRepository
from source.repositories.charge_repository import ChargeRepository
from source.repositories.database import Database
from source.repositories.payment_repository import PaymentRepository
from source.services.import_service import ImportService
from source.services.reconciliation_service import ReconciliationService


@lru_cache
def get_settings() -> Settings:
    return Settings.from_env()


def get_import_service() -> ImportService:
    settings = get_settings()
    return ImportService(
        OneCClient(settings),
        Database(settings.database_url),
        AccountRepository(),
        ChargeRepository(),
        PaymentRepository(),
    )


def get_reconciliation_service() -> ReconciliationService:
    settings = get_settings()
    return ReconciliationService(
        OneCClient(settings),
        Database(settings.database_url),
        AccountRepository(),
        ChargeRepository(),
    )
