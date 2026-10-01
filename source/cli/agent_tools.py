"""Read-only CLI-инструменты для существующего агента."""

import argparse
import json

from source.agent.dependencies import get_agent_tools


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only reconciliation tools")
    parser.add_argument(
        "tool",
        choices=("read_onec_charges", "read_postgres_charges", "reconcile_charges"),
    )
    parser.add_argument("--period", required=True, help="Month in YYYY-MM format")
    args = parser.parse_args()
    result = get_agent_tools().invoke(args.tool, {"period": args.period})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
