"""Проверка DTO, полученных от внешнего источника."""

import re
from datetime import date
from typing import Any

from source.domain.models import Account, Charge, Payment, SourceSnapshot

PERIOD_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class SourceContractError(ValueError):
    """Источник ответил, но нарушил согласованный контракт."""


def _text(row: dict[str, Any], field: str) -> str:
    value = row.get(field)
    if not isinstance(value, str) or not value.strip():
        raise SourceContractError(f"Field {field!r} must be a non-empty string")
    return value


def _kopecks(row: dict[str, Any]) -> int:
    value = row.get("amount_kopecks")
    if isinstance(value, bool) or not isinstance(value, int):
        raise SourceContractError("amount_kopecks must be an integer")
    return value


def parse_snapshot(payloads: dict[str, list[dict[str, Any]]]) -> SourceSnapshot:
    try:
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

    account_ids = {row.id for row in accounts}
    for name, rows in (("accounts", accounts), ("charges", charges), ("payments", payments)):
        ids = [row.id for row in rows]
        if len(ids) != len(set(ids)):
            raise SourceContractError(f"Duplicate id in {name}")
    if any(not PERIOD_PATTERN.fullmatch(row.period) for row in charges):
        raise SourceContractError("Charge period must use YYYY-MM")
    if any(row.account_id not in account_ids for row in (*charges, *payments)):
        raise SourceContractError("Charge or payment references an unknown account")
    return SourceSnapshot(accounts=accounts, charges=charges, payments=payments)
