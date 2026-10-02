"""Проверка DTO, полученных от внешнего источника."""

from collections.abc import Sequence
from datetime import date
from typing import Any

from source.domain.models import Account, Charge, Payment, SourceSnapshot
from source.domain.source_validation import (
    DEFAULT_SOURCE_RULES,
    SnapshotRule,
    validate_snapshot,
)
from source.domain.source_validation import (
    PERIOD_PATTERN as PERIOD_PATTERN,
)
from source.domain.source_validation import (
    SourceContractError as SourceContractError,
)


def _text(row: dict[str, Any], field: str) -> str:
    if not isinstance(row, dict):
        raise SourceContractError("Collection items must be objects")
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SourceContractError(f"Field {field!r} must be a non-empty string")
    return value


def _kopecks(row: dict[str, Any]) -> int:
    value = row.get("amount_kopecks")
    if isinstance(value, bool) or not isinstance(value, int):
        raise SourceContractError("amount_kopecks must be an integer")
    return value


def parse_snapshot(
    payloads: dict[str, list[dict[str, Any]]],
    *, rules: Sequence[SnapshotRule] = DEFAULT_SOURCE_RULES,
) -> SourceSnapshot:
    try:
        if not isinstance(payloads, dict):
            raise SourceContractError("Snapshot must be an object")
        for name in ("accounts", "charges", "payments"):
            if not isinstance(payloads.get(name), list):
                raise SourceContractError(f"{name} must be a list")
        accounts = tuple(
            Account(id=_text(row, "id"), account_number=_text(row, "account_number"))
            for row in payloads["accounts"]
        )
        charges = tuple(
            Charge(
                id=_text(row, "id"),
                account_id=_text(row, "account_id"),
                period=_text(row, "period"),
                amount_kopecks=_kopecks(row),
            )
            for row in payloads["charges"]
        )
        payments = tuple(
            Payment(
                id=_text(row, "id"),
                account_id=_text(row, "account_id"),
                date=date.fromisoformat(_text(row, "date")),
                amount_kopecks=_kopecks(row),
            )
            for row in payloads["payments"]
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, SourceContractError):
            raise
        raise SourceContractError(str(error)) from error

    snapshot = SourceSnapshot(accounts=accounts, charges=charges, payments=payments)
    validate_snapshot(snapshot, rules)
    return snapshot
