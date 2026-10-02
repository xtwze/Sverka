"""HTTP-настройки источника: не содержат реквизитов импортёра."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceSettings:
    source_base_url: str
    source_user: str
    source_password: str
    accounts_path: str
    charges_path: str
    payments_path: str
    source_mode: str

    @classmethod
    def from_env(cls) -> "SourceSettings":
        return cls(
            source_base_url=(os.getenv("ONEC_BASE_URL") or os.getenv(
                "SOURCE_BASE_URL", "http://localhost:8093"
            )).rstrip("/"),
            source_user=os.getenv("ONEC_USER", ""),
            source_password=os.getenv("ONEC_PASSWORD", ""),
            accounts_path=os.getenv("ONEC_ACCOUNTS_PATH", "accounts"),
            charges_path=os.getenv("ONEC_CHARGES_PATH", "charges"),
            payments_path=os.getenv("ONEC_PAYMENTS_PATH", "payments"),
            source_mode="real" if os.getenv("ONEC_BASE_URL") else "mock",
        )
