from unittest.mock import Mock

import pytest

from scripts.onec_demo import restore_demo


def test_restore_never_overwrites_existing_database(tmp_path, monkeypatch):
    platform = tmp_path / "1cv8"
    platform.touch()
    database = tmp_path / "existing"
    database.mkdir()
    valuable_file = database / "1Cv8.1CD"
    valuable_file.write_bytes(b"existing database")
    run = Mock()
    monkeypatch.setattr("scripts.onec_demo.run_platform", run)
    with pytest.raises(ValueError, match="NEW database"):
        restore_demo(platform, database)
    run.assert_not_called()
    assert valuable_file.read_bytes() == b"existing database"
