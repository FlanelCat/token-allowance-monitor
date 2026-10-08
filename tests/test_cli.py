import json
import sys
from datetime import datetime, timedelta

from token_allowance_monitor import main
from token_allowance_monitor.codex_app_server import LiveAllowance
from token_allowance_monitor.codex_usage import WindowUsage


def test_json_works_without_history_database(monkeypatch, capsys):
    def fail():
        raise RuntimeError("Codex state database was not found.")

    monkeypatch.setattr(main, "newest_session", fail)
    future_reset = int((datetime.now().astimezone() + timedelta(hours=1)).timestamp())
    monkeypatch.setattr(
        main,
        "read_live_allowance",
        lambda: LiveAllowance(
            fetched_at="2026-10-08T12:00:00+00:00",
            plan_type="plus",
            primary=WindowUsage(0, 300, future_reset),
            secondary=WindowUsage(42, 10080, future_reset),
            ordinary_usage_allowed=False,
        ),
    )
    monkeypatch.setattr(sys, "argv", ["codex-usage", "--json"])

    main.cli()

    output = json.loads(capsys.readouterr().out)
    assert set(output) == {
        "plan",
        "five_hour",
        "weekly",
        "limit_reached",
        "token_timestamp",
        "allowance_timestamp",
        "ordinaryUsageAllowed",
        "allowance_error",
    }
    assert output["plan"] == "plus"
    assert output["five_hour"]["used_percent"] == 0
    assert output["five_hour"]["fresh"] is True
    assert output["weekly"]["used_percent"] == 42
    assert output["ordinaryUsageAllowed"] is False
    assert output["token_timestamp"] is None
    assert output["allowance_error"] is None


def test_json_reports_unavailable_without_reusing_old_allowance(monkeypatch, capsys):
    def no_history():
        raise RuntimeError("Codex state database was not found.")

    def api_failure():
        raise RuntimeError("Codex app-server request timed out.")

    monkeypatch.setattr(main, "newest_session", no_history)
    monkeypatch.setattr(main, "read_live_allowance", api_failure)

    main.json_output()

    output = json.loads(capsys.readouterr().out)
    assert output["five_hour"] is None
    assert output["weekly"] is None
    assert output["limit_reached"] is False
    assert output["allowance_timestamp"] is None
    assert output["ordinaryUsageAllowed"] is None
    assert output["allowance_error"] == "Codex app-server request timed out."
    assert output["token_timestamp"] is None


def test_json_does_not_turn_expired_window_into_zero_usage(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "current_usage",
        lambda: main.CodexUsage(
            token_timestamp=None,
            allowance_timestamp="2026-10-08T12:00:00+00:00",
            plan_type="plus",
            primary=WindowUsage(63, 300, 1),
            secondary=None,
            tokens=None,
            ordinary_usage_allowed=True,
        ),
    )

    main.json_output()

    output = json.loads(capsys.readouterr().out)
    assert output["five_hour"]["fresh"] is False
    assert output["five_hour"]["used_percent"] is None
    assert output["five_hour"]["remaining_percent"] is None
    assert output["five_hour"]["resets_at"] is None
    assert output["ordinaryUsageAllowed"] is True


def test_compact_does_not_turn_expired_window_into_zero(monkeypatch, capsys):
    monkeypatch.setattr(
        main,
        "current_usage",
        lambda: main.CodexUsage(
            token_timestamp=None,
            allowance_timestamp=None,
            plan_type="plus",
            primary=WindowUsage(63, 300, 1),
            secondary=None,
            tokens=None,
        ),
    )

    main.compact()

    output = capsys.readouterr().out
    assert "5h: ?" in output
    assert "5h: 0%" not in output
