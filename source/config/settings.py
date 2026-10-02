"""Настройки приложения из переменных окружения."""

import os
from dataclasses import asdict, dataclass

from source.config.source_settings import SourceSettings


@dataclass(frozen=True)
class Settings(SourceSettings):
    database_url: str

    @classmethod
    def from_env(cls) -> "Settings":
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("DATABASE_URL is required for the importer")
        return cls(
            **asdict(SourceSettings.from_env()),
            database_url=database_url,
        )
