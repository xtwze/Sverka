"""CLI-контроллер сверки."""

import argparse
import json

from source.config.dependencies import get_reconciliation_service


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile 1C charges with PostgreSQL")
    parser.add_argument("--period", required=True, help="Month in YYYY-MM format")
    args = parser.parse_args()
    report = get_reconciliation_service().reconcile(args.period)
    print(json.dumps(report.model_dump(), ensure_ascii=False, indent=2))
    return 0 if report.status == "MATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
