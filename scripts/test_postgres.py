"""Run all Python tests against a disposable PostgreSQL, never the application database."""

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ['docker', 'compose', '-f', str(ROOT / 'compose.test.yaml')]


def main() -> int:
    try:
        subprocess.run([*COMPOSE, 'up', '-d', '--wait'], cwd=ROOT, check=True)
        address = subprocess.check_output(
            [*COMPOSE, 'port', 'postgres', '5432'], cwd=ROOT, text=True,
        ).strip()
        return subprocess.run(
            [sys.executable, '-m', 'pytest', '-q'], cwd=ROOT,
            env={**os.environ, 'TEST_DATABASE_URL':
                 f'postgresql://test_runner@{address}/reconciliation_tests'},
        ).returncode
    finally:
        subprocess.run([*COMPOSE, 'down'], cwd=ROOT, check=True)


if __name__ == '__main__':
    raise SystemExit(main())
