"""Настройки приложения из переменных окружения."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str
    source_base_url: str
    source_user: str
    source_password: str
    accounts_path: str
    charges_path: str
    payments_path: str

    @classmethod
    def from_env(cls) -> "Settings":
        source_base_url = os.getenv("ONEC_BASE_URL") or os.getenv(
            "SOURCE_BASE_URL", "http://localhost:8093"
        )
        return cls(
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql://importer:demo-importer-local@localhost:5543/reporting",
            ),
            source_base_url=source_base_url.rstrip("/"),
            source_user=os.getenv("ONEC_USER", ""),
            source_password=os.getenv("ONEC_PASSWORD", ""),
            accounts_path=os.getenv("ONEC_ACCOUNTS_PATH", "accounts"),
            charges_path=os.getenv("ONEC_CHARGES_PATH", "charges"),
            payments_path=os.getenv("ONEC_PAYMENTS_PATH", "payments"),
        )
