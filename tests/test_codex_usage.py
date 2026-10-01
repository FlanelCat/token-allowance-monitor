import sqlite3
from pathlib import Path

import pytest

from token_allowance_monitor import codex_usage


def test_newest_session_missing_database(tmp_path, monkeypatch):
    state_db = tmp_path / "state_5.sqlite"
    monkeypatch.setattr(codex_usage, "STATE_DB", state_db)

    with pytest.raises(
        RuntimeError,
        match="Codex state database was not found.",
    ):
        codex_usage.newest_session()


def test_newest_session_no_threads(tmp_path, monkeypatch):
    state_db = tmp_path / "state_5.sqlite"

    connection = sqlite3.connect(state_db)
    connection.execute(
        """
        CREATE TABLE threads (
            rollout_path TEXT,
            updated_at INTEGER
        )
        """
    )
    connection.commit()
    connection.close()

    monkeypatch.setattr(codex_usage, "STATE_DB", state_db)

    with pytest.raises(
        RuntimeError,
        match="No Codex threads found.",
    ):
        codex_usage.newest_session()


def test_newest_session_missing_rollout(tmp_path, monkeypatch):
    state_db = tmp_path / "state_5.sqlite"
    missing_session = tmp_path / "missing.jsonl"

    connection = sqlite3.connect(state_db)
    connection.execute(
        """
        CREATE TABLE threads (
            rollout_path TEXT,
            updated_at INTEGER
        )
        """
    )
    connection.execute(
        "INSERT INTO threads (rollout_path, updated_at) VALUES (?, ?)",
        (str(missing_session), 1),
    )
    connection.commit()
    connection.close()

    monkeypatch.setattr(codex_usage, "STATE_DB", state_db)

    with pytest.raises(
        RuntimeError,
        match="The latest Codex session file does not exist.",
    ):
        codex_usage.newest_session()
