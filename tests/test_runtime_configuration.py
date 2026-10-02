import json
import runpy
from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from scripts.setup_local import configure
from source.config.settings import Settings


def test_importer_requires_explicit_credentials(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError, match='DATABASE_URL is required'):
        Settings.from_env()


def test_local_setup_preserves_configuration_and_password_on_repeat(tmp_path):
    env = tmp_path / '.env'
    env.write_text('ONEC_BASE_URL=http://source.example/api\nLLM_API=keep-me\nPOSTGRES_PORT=6000\n')
    configure(env)
    first = env.read_text()
    configure(env)
    assert env.read_text() == first
    assert 'ONEC_BASE_URL=http://source.example/api' in first
    assert 'LLM_API=keep-me' in first
    assert '@localhost:6000/reporting' in first
    assert env.stat().st_mode & 0o777 == 0o600


def test_mock_preflight_uses_container_source_url(monkeypatch, capsys):
    monkeypatch.setenv('SOURCE_BASE_URL', 'http://source-mock:8000')
    monkeypatch.setenv('ONEC_BASE_URL', 'http://real-source.test')
    urls = []

    def response(request):
        urls.append(str(request.url))
        return httpx.Response(200, json={'value': [{'id': 'fixture'}]})

    client = httpx.Client(transport=httpx.MockTransport(response))
    with patch('httpx.Client', return_value=client), patch('sys.argv', ['preflight.py']):
        runpy.run_path(str(Path('scripts/preflight.py')), run_name='__main__')
    result = json.loads(capsys.readouterr().out)
    assert result == {'status': 'PASS', 'mode': 'mock',
                      'counts': {'accounts': 1, 'charges': 1, 'payments': 1}}
    assert len(urls) == 3
    assert all(url.startswith('http://source-mock:8000/') for url in urls)


def test_failed_rotation_does_not_change_local_configuration(tmp_path):
    env = tmp_path / '.env'
    env.write_text('LLM_API=keep-me\n')
    with patch('scripts.setup_local.subprocess.run') as run:
        run.return_value.returncode = 1
        with pytest.raises(RuntimeError, match='was not changed'):
            configure(env, rotate_existing=True)
    assert env.read_text() == 'LLM_API=keep-me\n'
