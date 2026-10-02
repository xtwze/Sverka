"""DTO ответов прикладного API."""

from typing import Literal

from pydantic import BaseModel


class ImportResponse(BaseModel):
    accounts: int
    charges: int
    payments: int


class ReconciliationSummary(BaseModel):
    count: int
    total_kopecks: int


class DifferenceResponse(BaseModel):
    type: str
    record_id: str
    account_number: str
    source_value: int | str | None
    postgres_value: int | str | None


class ReconciliationResponse(BaseModel):
    run_id: str
    period: str
    status: Literal["MATCH", "MISMATCH"]
    source: ReconciliationSummary
    postgres: ReconciliationSummary
    differences: list[DifferenceResponse]
    source_mode: Literal["mock", "real", "unknown"] = "unknown"


class HealthResponse(BaseModel):
    status: Literal["ok"]
