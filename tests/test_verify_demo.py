import json
from unittest.mock import patch

import pytest

from scripts import verify_demo


def test_demo_restores_after_failed_discrepancy_read(tmp_path):
    output = tmp_path / 'mock-evidence.json'
    rows = {'period': '2026-08', 'count': 0, 'total_kopecks': 0, 'rows': []}
    baseline = {'read_onec_charges': rows, 'read_postgres_charges': rows,
                'reconcile_charges': {'status': 'MATCH'}}
    with (
        patch('sys.argv', ['verify_demo.py', '--mode', 'mock', '--output', str(output)]),
        patch.object(verify_demo, 'execute', return_value='{"status":"PASS"}') as execute,
        patch.object(verify_demo, 'read_stage',
                     side_effect=[baseline, RuntimeError('source offline'), baseline]),
    ):
        with pytest.raises(RuntimeError, match='source offline'):
            verify_demo.main()
    assert execute.call_args_list[-1].args == ('api', 'scripts/discrepancy.py', 'restore')
    evidence = json.loads(output.read_text())
    assert evidence['status'] == 'BLOCKED'
    assert evidence['source_mode'] == 'mock'
    assert evidence['restored']['reconcile_charges']['status'] == 'MATCH'


def test_demo_does_not_restore_when_introduce_refuses_existing_changes(tmp_path):
    output = tmp_path / 'mock-evidence.json'
    with (
        patch('sys.argv', ['verify_demo.py', '--mode', 'mock', '--output', str(output)]),
        patch.object(verify_demo, 'execute',
                     side_effect=['{"status":"PASS"}', RuntimeError('unexpected state')]) as run,
        patch.object(verify_demo, 'read_stage',
                     return_value={'reconcile_charges': {'status': 'MATCH'}}),
    ):
        with pytest.raises(RuntimeError, match='unexpected state'):
            verify_demo.main()
    assert all(call.args[-1] != 'restore' for call in run.call_args_list)
    assert json.loads(output.read_text())['status'] == 'BLOCKED'
