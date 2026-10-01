"""Клиент read-only HTTP API 1С или стартового mock-источника."""

from typing import Any

import httpx

from source.models import SourceContractError, SourceSnapshot, parse_snapshot
from source.settings import Settings


class SourceUnavailable(RuntimeError):
    pass


class SourceClient:
    def __init__(self, settings: Settings):
        self.settings = settings

    def fetch_snapshot(self) -> SourceSnapshot:
        auth = None
        if self.settings.source_user:
            auth = (self.settings.source_user, self.settings.source_password)
        paths = {
            "accounts": self.settings.accounts_path,
            "charges": self.settings.charges_path,
            "payments": self.settings.payments_path,
        }
        payloads: dict[str, list[dict[str, Any]]] = {}
        try:
            with httpx.Client(auth=auth, timeout=15) as client:
                for name, path in paths.items():
                    response = client.get(
                        f"{self.settings.source_base_url}/{path.lstrip('/')}",
                        params={"$format": "json"},
                    )
                    response.raise_for_status()
                    rows = response.json()["value"]
                    if not isinstance(rows, list):
                        raise SourceContractError(f"{name}.value must be a list")
                    payloads[name] = rows
        except (httpx.HTTPError, KeyError, ValueError) as error:
            if isinstance(error, SourceContractError):
                raise
            raise SourceUnavailable(f"Source request failed: {type(error).__name__}") from error
        return parse_snapshot(payloads)
