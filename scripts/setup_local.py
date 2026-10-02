"""Generate local importer credentials without printing or passing them to the agent."""

import argparse
import os
import re
import secrets
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def configure(path: Path, *, rotate_existing: bool = False) -> None:
    text = path.read_text() if path.exists() else (ROOT / '.env.example').read_text()
    values = dict(re.findall(r'^([A-Z_]+)=(.*)$', text, re.MULTILINE))
    password = values.get('IMPORTER_PASSWORD') or secrets.token_hex(32)
    if not re.fullmatch(r'[a-zA-Z0-9_-]+', password):
        raise ValueError('IMPORTER_PASSWORD must use URL-safe letters, digits, _ or -')
    if rotate_existing:
        # Existing local volume: execute inside PostgreSQL's operator context.
        # No password is put in argv, stdout, the agent environment or a report.
        result = subprocess.run(
            ['docker', 'compose', 'exec', '-T', 'postgres', 'psql', '-U', 'importer',
             '-d', 'reporting', '-v', 'ON_ERROR_STOP=1'],
            input=f"ALTER ROLE importer PASSWORD '{password}';\n",
            text=True, capture_output=True, cwd=ROOT,
            env={**os.environ, "IMPORTER_PASSWORD": password},
        )
        if result.returncode:
            raise RuntimeError('Cannot rotate local PostgreSQL role; .env was not changed')
    updates = {
        'IMPORTER_PASSWORD': password,
        'DATABASE_URL': 'postgresql://importer:' + password
        + '@localhost:' + (values.get('POSTGRES_PORT') or '5543') + '/reporting',
    }
    for name, value in updates.items():
        if re.search(rf'^{name}=.*$', text, re.MULTILINE):
            text = re.sub(rf'^{name}=.*$', f'{name}={value}', text, flags=re.MULTILINE)
        else:
            text = text.rstrip() + f'\n{name}={value}\n'
    # Open with restrictive permissions before any secret bytes are written.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.fchmod(descriptor, 0o600)
    with os.fdopen(descriptor, 'w') as stream:
        stream.write(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rotate-existing', action='store_true',
                        help='Update the importer password in the existing local demo volume')
    args = parser.parse_args()
    configure(ROOT / '.env', rotate_existing=args.rotate_existing)
    print('Local importer credentials configured; values are not displayed.')


if __name__ == '__main__':
    main()
