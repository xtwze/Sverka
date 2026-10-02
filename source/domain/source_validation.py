"""Расширяемые проверки полного снимка перед любой записью в PostgreSQL."""

import re
from collections.abc import Callable, Sequence

from source.domain.models import SourceSnapshot

PERIOD_PATTERN = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


class SourceContractError(ValueError):
    """Источник ответил, но нарушил согласованный контракт."""


SnapshotRule = Callable[[SourceSnapshot], None]


def unique_ids(snapshot: SourceSnapshot) -> None:
    for name in ("accounts", "charges", "payments"):
        ids = [row.id for row in getattr(snapshot, name)]
        if len(ids) != len(set(ids)):
            raise SourceContractError(f"Duplicate id in {name}")


def valid_periods(snapshot: SourceSnapshot) -> None:
    if any(not PERIOD_PATTERN.fullmatch(row.period) for row in snapshot.charges):
        raise SourceContractError("Charge period must use YYYY-MM")


def known_accounts(snapshot: SourceSnapshot) -> None:
    account_ids = {row.id for row in snapshot.accounts}
    if any(row.account_id not in account_ids for row in (*snapshot.charges, *snapshot.payments)):
        raise SourceContractError("Charge or payment references an unknown account")


def unique_account_numbers(snapshot: SourceSnapshot) -> None:
    """Дополнительное правило: заранее проверяет UNIQUE из схемы PostgreSQL."""
    numbers = [row.account_number for row in snapshot.accounts]
    if len(numbers) != len(set(numbers)):
        raise SourceContractError("Duplicate account_number in accounts")


DEFAULT_SOURCE_RULES: tuple[SnapshotRule, ...] = (
    unique_ids, valid_periods, known_accounts, unique_account_numbers,
)


def validate_snapshot(
    snapshot: SourceSnapshot, rules: Sequence[SnapshotRule] = DEFAULT_SOURCE_RULES,
) -> None:
    for rule in rules:
        rule(snapshot)
