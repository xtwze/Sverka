"""Восстановить демобазу 1С из XML и JSON в НОВЫЙ каталог, без локального .dt."""

import argparse
import json
import subprocess
from pathlib import Path

from source.dto.source_dto import parse_snapshot

ROOT = Path(__file__).resolve().parents[1]


def run_platform(platform: Path, arguments: list[str], log: Path) -> None:
    result = subprocess.run(
        [str(platform), *arguments, "/Out", str(log), "/DisableStartupDialogs",
         "/DisableStartupMessages"],
        capture_output=True, text=True, timeout=180,
    )
    if result.returncode:
        raise RuntimeError(f"1C exited with code {result.returncode}; see {log}")


def restore_demo(platform: Path, database: Path) -> dict:
    database = database.resolve()
    platform = platform.resolve(strict=True)
    logs = database.with_name(database.name + "-logs")
    if database.exists() or logs.exists():
        raise ValueError("Choose a NEW database directory; existing data is never overwritten")
    if any(character in str(database) for character in ('"', ';', '|')):
        raise ValueError("Database path contains a command delimiter")
    fixtures = ROOT / "fixtures/data.json"
    expected_payload = json.loads(fixtures.read_text())
    expected = parse_snapshot(expected_payload)
    logs.mkdir(parents=True)
    run_platform(platform, ["CREATEINFOBASE", f'File="{database}";'], logs / "create.log")
    run_platform(platform, ["DESIGNER", "/F", str(database), "/LoadConfigFromFiles",
                           str(ROOT / "onec/configuration"), "/UpdateDBCfg"], logs / "load.log")
    reports = []
    for number in (1, 2):
        report_path = logs / f"seed-{number}.json"
        run_platform(platform, ["ENTERPRISE", "/F", str(database), "/C",
                               f"demo-seed|{fixtures}|{report_path}"], logs / f"seed-{number}.log")
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
        if report.get("status") != "PASS":
            raise RuntimeError(f"1C seed failed; see {report_path}")
        actual = parse_snapshot(report["snapshot"])
        for collection in ("accounts", "charges", "payments"):
            if sorted(getattr(expected, collection), key=lambda row: row.id) != sorted(
                getattr(actual, collection), key=lambda row: row.id,
            ):
                raise RuntimeError(f"1C {collection} differs from fixtures; see {report_path}")
        reports.append(str(report_path))
    return {
        "status": "PASS", "mode": "real-local-1c", "http_integration": "BLOCKED",
        "database": str(database), "runs": reports,
        "counts": {key: len(getattr(expected, key)) for key in ("accounts", "charges", "payments")},
        "august_total_kopecks": sum(
            row.amount_kopecks for row in expected.charges if row.period == "2026-08"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", type=Path, required=True, help="Path to 1cv8 executable")
    parser.add_argument("--database", type=Path, required=True, help="NEW local demo directory")
    args = parser.parse_args()
    try:
        result = restore_demo(args.platform, args.database)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "BLOCKED", "reason": str(error)}, ensure_ascii=False))
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
