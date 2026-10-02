"""Record real CLI evidence and restore the local demo PostgreSQL after discrepancies."""

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PERIOD = '2026-08'


def execute(service: str, *arguments: str) -> str:
    result = subprocess.run(
        ['docker', 'compose', 'exec', '-T', service, 'uv', 'run', '--frozen', '--no-dev',
         'python', *arguments], cwd=ROOT, text=True, capture_output=True,
    )
    if result.returncode:
        # Third-party stderr can contain environment details: keep it out of saved evidence.
        raise RuntimeError(f'{service}: {arguments[0]} failed (exit {result.returncode})')
    return result.stdout


def read_stage(mode: str) -> dict:
    outputs = {}
    for name in ('read_onec_charges', 'read_postgres_charges', 'reconcile_charges'):
        outputs[name] = json.loads(execute(
            'agent', '-m', 'source.cli.agent_tools', name, '--period', PERIOD,
        ))
    report = outputs['reconcile_charges']
    assert report['source_mode'] == mode, 'Source mode differs from requested mode'
    for tool, side in (('read_onec_charges', 'source'), ('read_postgres_charges', 'postgres')):
        rows = outputs[tool]
        assert rows['period'] == report['period'] == PERIOD
        assert {key: rows[key] for key in ('count', 'total_kopecks')} == report[side]
        assert len(rows['rows']) == rows['count']
        assert sum(row['amount_kopecks'] for row in rows['rows']) == rows['total_kopecks']
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('mock', 'real'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    evidence = {'checked_at': datetime.now(timezone.utc).isoformat(),
                'source_mode': args.mode, 'period': PERIOD, 'status': 'BLOCKED',
                'skills': ['validate-source-data', 'verify-reconciliation-report']}
    changed = False
    try:
        flags = ['--real'] if args.mode == 'real' else []
        evidence['preflight'] = json.loads(execute('agent', 'scripts/preflight.py', *flags))
        assert evidence['preflight']['status'] == 'PASS'
        evidence['baseline'] = read_stage(args.mode)
        assert evidence['baseline']['reconcile_charges']['status'] == 'MATCH'
        execute('api', 'scripts/discrepancy.py', 'introduce')
        changed = True
        evidence['discrepancy'] = read_stage(args.mode)
        report = evidence['discrepancy']['reconcile_charges']
        assert report['status'] == 'MISMATCH'
        assert [(d['record_id'], d['type'], d['source_value'], d['postgres_value'])
                for d in report['differences']] == [
            ('charge-2', 'amount_mismatch', 24950, 25050),
            ('charge-3', 'missing_in_postgres', 990000, None),
        ]
        evidence['agent'] = json.loads(execute(
            'agent', '-m', 'source.agent.cli', '--json',
            'Сверь начисления за 2026-08. Объясни каждое расхождение: укажи ID, '
            'тип и значения с обеих сторон в копейках. Не предполагай причины.',
        ))
        calls = evidence['agent']['tool_calls']
        assert len(calls) == 1 and calls[0]['name'] == 'reconcile_charges'
        assert calls[0]['arguments'] == {'period': PERIOD}
        for key in ('period', 'status', 'source', 'postgres', 'differences', 'source_mode'):
            assert calls[0]['output'][key] == report[key]
        assert all(identifier in evidence['agent']['answer']
                   for identifier in ('charge-2', 'charge-3'))
        evidence['status'] = 'PASS'
    except Exception as error:
        evidence['status'] = 'BLOCKED'
        evidence['reason'] = str(error)
        raise
    finally:
        try:
            if changed:
                execute('api', 'scripts/discrepancy.py', 'restore')
                evidence['restored'] = read_stage(args.mode)
                assert evidence['restored']['reconcile_charges']['status'] == 'MATCH'
                for tool in ('read_onec_charges', 'read_postgres_charges'):
                    assert evidence['baseline'][tool] == evidence['restored'][tool]
                if 'discrepancy' in evidence:
                    assert (evidence['baseline']['read_onec_charges']
                            == evidence['discrepancy']['read_onec_charges'])
        except Exception:
            evidence['status'] = 'BLOCKED'
            evidence['restore_error'] = 'Restore or its verification failed; operator action needed'
            raise
        finally:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'status': evidence['status'], 'source_mode': args.mode,
                      'output': str(args.output)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
