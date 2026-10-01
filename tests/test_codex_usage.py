import sqlite3
import json
import pytest

from pathlib import Path
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

def test_read_usage_extracts_only_token_count_data(tmp_path):
    session = tmp_path / "session.jsonl"

    records = [
        '{"type":"user_message","payload":{"message":"PRIVATE PROMPT"}}',
        'this is deliberately invalid json',
        (
            '{"timestamp":"2026-09-29T20:08:54.716Z",'
            '"type":"event_msg","payload":{"type":"token_count",'
            '"info":{"last_token_usage":{'
            '"input_tokens":62424,'
            '"cached_input_tokens":56192,'
            '"output_tokens":302,'
            '"reasoning_output_tokens":13,'
            '"total_tokens":62726},'
            '"model_context_window":258400},'
            '"rate_limits":{"plan_type":"plus",'
            '"primary":{"used_percent":6,"window_minutes":300,'
            '"resets_at":1790716095},'
            '"secondary":{"used_percent":100,"window_minutes":10080,'
            '"resets_at":1791094774}}}}'
        ),
    ]

    session.write_text("\n".join(records) + "\n", encoding="utf-8")

    usage = codex_usage.read_usage(session)

    assert usage.token_timestamp == "2026-09-29T20:08:54.716Z"
    assert usage.allowance_timestamp == "2026-09-29T20:08:54.716Z"
    assert usage.plan_type == "plus"

    assert usage.tokens is not None
    assert usage.tokens.input_tokens == 62424
    assert usage.tokens.cached_input_tokens == 56192
    assert usage.tokens.output_tokens == 302
    assert usage.tokens.reasoning_output_tokens == 13
    assert usage.tokens.total_tokens == 62726
    assert usage.tokens.model_context_window == 258400

    assert usage.primary is not None
    assert usage.primary.used_percent == 6
    assert usage.primary.window_minutes == 300

    assert usage.secondary is not None
    assert usage.secondary.used_percent == 100
    assert usage.secondary.window_minutes == 10080

    assert not hasattr(usage, "session_path")

def test_read_usage_keeps_latest_tokens_and_latest_available_limits(tmp_path):
    session = tmp_path / "session.jsonl"

    records = [
        {
            "timestamp": "2026-10-01T10:00:00Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 100,
                        "cached_input_tokens": 40,
                        "output_tokens": 20,
                        "reasoning_output_tokens": 5,
                        "total_tokens": 120,
                    },
                    "model_context_window": 258400,
                },
                "rate_limits": {
                    "plan_type": "plus",
                    "primary": {
                        "used_percent": 10,
                        "window_minutes": 300,
                        "resets_at": 1000,
                    },
                    "secondary": {
                        "used_percent": 50,
                        "window_minutes": 10080,
                        "resets_at": 2000,
                    },
                },
            },
        },
        {
            "timestamp": "2026-10-01T10:01:00Z",
            "type": "event_msg",
            "payload": {
                "type": "token_count",
                "info": {
                    "last_token_usage": {
                        "input_tokens": 200,
                        "cached_input_tokens": 80,
                        "output_tokens": 30,
                        "reasoning_output_tokens": 7,
                        "total_tokens": 230,
                    },
                    "model_context_window": 258400,
                },
            },
        },
    ]

    session.write_text(
        "\n".join(json.dumps(record) for record in records) + "\n",
        encoding="utf-8",
    )

    usage = codex_usage.read_usage(session)

    assert usage.token_timestamp == "2026-10-01T10:01:00Z"
    assert usage.allowance_timestamp == "2026-10-01T10:00:00Z"

    assert usage.tokens is not None
    assert usage.tokens.input_tokens == 200
    assert usage.tokens.total_tokens == 230

    assert usage.primary is not None
    assert usage.primary.used_percent == 10

    assert usage.secondary is not None
    assert usage.secondary.used_percent == 50

    assert usage.plan_type == "plus"