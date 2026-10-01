"""Доменные сущности сверки."""

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class Account:
    id: str
    account_number: str


@dataclass(frozen=True)
class Charge:
    id: str
    account_id: str
    period: str
    amount_kopecks: int


@dataclass(frozen=True)
class Payment:
    id: str
    account_id: str
    date: date
    amount_kopecks: int


@dataclass(frozen=True)
class SourceSnapshot:
    accounts: tuple[Account, ...]
    charges: tuple[Charge, ...]
    payments: tuple[Payment, ...]
