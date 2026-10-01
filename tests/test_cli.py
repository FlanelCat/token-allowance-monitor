import sys

import pytest

from token_allowance_monitor import main


def test_cli_reports_runtime_error_without_traceback(monkeypatch, capsys):
    def fail():
        raise RuntimeError("Codex state database was not found.")

    monkeypatch.setattr(main, "newest_session", fail)
    monkeypatch.setattr(sys, "argv", ["codex-usage", "--compact"])

    with pytest.raises(SystemExit) as exc_info:
        main.cli()

    assert exc_info.value.code == 1

    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == (
        "codex-usage: error: Codex state database was not found.\n"
    )
    assert "Traceback" not in captured.err
