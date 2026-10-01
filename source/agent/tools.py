"""Явный список операций, которые может вызвать агент."""

from collections.abc import Callable
from dataclasses import asdict
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from source.clients.onec_client import OneCClient
from source.domain.models import Charge
from source.dto.response_dto import ReconciliationResponse
from source.repositories.charge_repository import ChargeRepository
from source.repositories.database import Database
from source.services.reconciliation_service import ReconciliationService


class ToolInputError(ValueError):
    """Аргументы вызова не соответствуют контракту инструмента."""


class UnknownToolError(ValueError):
    """Операция отсутствует в разрешённом списке."""


class ReconcileChargesInput(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


class AgentTools:
    """Единственная точка вызова разрешённых инструментов агентом."""

    def __init__(
        self,
        reconciliation: ReconciliationService,
        source: OneCClient,
        database: Database,
        charges: ChargeRepository,
    ):
        self._reconciliation = reconciliation
        self._source = source
        self._database = database
        self._charges = charges
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
            "read_onec_charges": self._read_onec_charges,
            "read_postgres_charges": self._read_postgres_charges,
            "reconcile_charges": self._reconcile_charges,
            "summarize_payments": self._summarize_payments,
        }

    @property
    def names(self) -> tuple[str, ...]:
        return tuple(self._handlers)

    def invoke(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            handler = self._handlers[name]
        except KeyError as error:
            raise UnknownToolError(f"Unknown tool: {name}") from error
        if not isinstance(arguments, dict):
            raise ToolInputError("Tool arguments must be an object")
        return handler(arguments)

    @staticmethod
    def _period(arguments: dict[str, Any]) -> str:
        try:
            request = ReconcileChargesInput.model_validate(arguments)
        except ValidationError as error:
            raise ToolInputError("Tool requires a valid YYYY-MM period") from error
        return request.period

    def _read_onec_charges(self, arguments: dict[str, Any]) -> dict[str, Any]:
        period = self._period(arguments)
        rows = tuple(row for row in self._source.fetch_snapshot().charges if row.period == period)
        return self._charge_result("onec", period, rows)

    def _read_postgres_charges(self, arguments: dict[str, Any]) -> dict[str, Any]:
        period = self._period(arguments)
        with self._database.connection() as connection:
            rows = self._charges.for_period(connection, period)
        return self._charge_result("postgres", period, rows)

    @staticmethod
    def _charge_result(source: str, period: str, rows: tuple[Charge, ...]) -> dict[str, Any]:
        return {
            "source": source,
            "period": period,
            "count": len(rows),
            "total_kopecks": sum(row.amount_kopecks for row in rows),
            "rows": [asdict(row) for row in rows],
        }

    def _reconcile_charges(self, arguments: dict[str, Any]) -> dict[str, Any]:
        period = self._period(arguments)
        report = self._reconciliation.reconcile(period)
        return ReconciliationResponse.model_validate(report).model_dump(mode="json")

    def _summarize_payments(self, arguments: dict[str, Any]) -> dict[str, Any]:
        period = self._period(arguments)
        source_rows = tuple(
            row for row in self._source.fetch_snapshot().payments
            if row.date.strftime("%Y-%m") == period
        )
        with self._database.connection() as connection:
            count, total = connection.execute(
                """SELECT count(*), coalesce(sum(amount_kopecks), 0)
                   FROM payments WHERE payment_date >= to_date(%s, 'YYYY-MM')
                   AND payment_date < to_date(%s, 'YYYY-MM') + interval '1 month'""",
                (period, period),
            ).fetchone()
        return {
            "period": period,
            "source": {
                "count": len(source_rows),
                "total_kopecks": sum(row.amount_kopecks for row in source_rows),
            },
            "postgres": {"count": int(count), "total_kopecks": int(total)},
        }
