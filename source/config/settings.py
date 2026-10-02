"""Настройки приложения из переменных окружения."""

import os
from dataclasses import asdict, dataclass

from source.config.source_settings import SourceSettings


@dataclass(frozen=True)
class Settings(SourceSettings):
    database_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            **asdict(SourceSettings.from_env()),
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql://importer:demo-importer-local@localhost:5543/reporting",
            ),
        )
