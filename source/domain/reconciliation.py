"""Чистые доменные правила сверки начислений."""

from uuid import uuid4

from source.domain.models import Charge


def reconcile_charges(
    period: str,
    source_rows: tuple[Charge, ...],
    postgres_rows: tuple[Charge, ...],
    account_numbers: dict[str, str],
) -> dict:
    source = {row.id: row for row in source_rows if row.period == period}
    target = {row.id: row for row in postgres_rows if row.period == period}
    differences = []
    for record_id in sorted(source.keys() | target.keys()):
        left = source.get(record_id)
        right = target.get(record_id)
        row = left or right
        assert row is not None
        if left is None:
            difference_type = "extra_in_postgres"
        elif right is None:
            difference_type = "missing_in_postgres"
        else:
            # Независимые изменения одной записи должны присутствовать одновременно.
            for field, kind in (("account_id", "account_mismatch"),
                                ("amount_kopecks", "amount_mismatch")):
                if getattr(left, field) != getattr(right, field):
                    differences.append({
                        "type": kind,
                        "record_id": record_id,
                        "account_number": account_numbers.get(row.account_id, row.account_id),
                        "source_value": getattr(left, field),
                        "postgres_value": getattr(right, field),
                    })
            continue
        differences.append(
            {
                "type": difference_type,
                "record_id": record_id,
                "account_number": account_numbers.get(row.account_id, row.account_id),
                "source_value": left.amount_kopecks if left else None,
                "postgres_value": right.amount_kopecks if right else None,
            }
        )
    return {
        "run_id": str(uuid4()),
        "period": period,
        "status": "MATCH" if not differences else "MISMATCH",
        "source": {
            "count": len(source),
            "total_kopecks": sum(row.amount_kopecks for row in source.values()),
        },
        "postgres": {
            "count": len(target),
            "total_kopecks": sum(row.amount_kopecks for row in target.values()),
        },
        "differences": differences,
    }
