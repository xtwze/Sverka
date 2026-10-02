"""CLI-контроллер сверки."""

import argparse
import json

from source.agent.dependencies import get_agent_tools


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile 1C charges with PostgreSQL")
    parser.add_argument("--period", required=True, help="Month in YYYY-MM format")
    args = parser.parse_args()
    report = get_agent_tools().invoke("reconcile_charges", {"period": args.period})
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "MATCH" else 1


if __name__ == "__main__":
    raise SystemExit(main())
