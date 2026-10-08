import json
import sys
import textwrap
import time

import pytest

from token_allowance_monitor import main
from token_allowance_monitor.codex_app_server import read_live_allowance


def fake_codex(tmp_path, body):
    executable = tmp_path / "codex"
    executable.write_text(
        "#!/usr/bin/env python3\n"
        "import json, sys, time\n"
        "for line in sys.stdin:\n"
        "    message = json.loads(line)\n"
        + textwrap.indent(textwrap.dedent(body).strip(), "    ")
        + "\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


def test_reads_live_allowance_and_maps_windows_by_duration(tmp_path):
    executable = fake_codex(
        tmp_path,
        """
        if message["method"] == "initialize":
            print(json.dumps({"jsonrpc": "2.0", "id": 1, "result": {}}), flush=True)
        elif message["method"] == "account/rateLimits/read":
            print(json.dumps({
                "jsonrpc": "2.0",
                "id": 2,
                "result": {
                    "ordinaryUsageAllowed": False,
                    "rateLimits": {
                        "planType": "plus",
                        "weekly": {"usedPercent": 51, "windowDurationMins": 10080, "resetsAt": 2000},
                        "primary": {"usedPercent": 12, "windowDurationMins": 300, "resetsAt": 1000},
                        "unknown": {"usedPercent": 99, "windowDurationMins": 60, "resetsAt": 3000}
                    }
                }
            }), flush=True)
        """,
    )

    result = read_live_allowance(executable)

    assert result.plan_type == "plus"
    assert result.ordinary_usage_allowed is False
    assert result.primary is not None
    assert result.primary.used_percent == 12
    assert result.primary.window_minutes == 300
    assert result.secondary is not None
    assert result.secondary.used_percent == 51
    assert result.secondary.window_minutes == 10080
    assert result.fetched_at


@pytest.mark.parametrize(
    "rate_limits, expected_plan",
    [
        ({"planType": "plus"}, "plus"),
        ({}, None),
        ({"planType": None}, None),
        ({"planType": 123}, None),
        ({"planType": False}, None),
        ({"planType": []}, None),
        ({"planType": {}}, None),
    ],
)
def test_cli_json_uses_nested_plan_type(
    tmp_path, monkeypatch, capsys, rate_limits, expected_plan
):
    response = json.dumps({"id": 2, "result": {"rateLimits": rate_limits}})
    fake_codex(
        tmp_path,
        f"""
        if message["method"] == "initialize":
            print(json.dumps({{"id": 1, "result": {{}}}}), flush=True)
        elif message["method"] == "account/rateLimits/read":
            print({response!r}, flush=True)
        """,
    )
    monkeypatch.setenv("PATH", str(tmp_path), prepend=":")

    def no_history():
        raise RuntimeError("Codex state database was not found.")

    monkeypatch.setattr(main, "newest_session", no_history)
    monkeypatch.setattr(sys, "argv", ["codex-usage", "--json"])

    main.cli()

    output = json.loads(capsys.readouterr().out)
    assert output["plan"] == expected_plan
    assert output["allowance_error"] is None


def test_sends_expected_handshake_and_read_params(tmp_path):
    executable = fake_codex(
        tmp_path,
        """
        if message["method"] == "initialize":
            assert message["params"]["clientInfo"]["name"] == "token-allowance-monitor"
            print(json.dumps({"id": 1, "result": {}}), flush=True)
        elif message["method"] == "initialized":
            pass
        elif message["method"] == "account/rateLimits/read":
            assert message["params"]["excludeResetCreditDetails"] is True
            print(json.dumps({"id": 2, "result": {"rateLimits": {}}}), flush=True)
        """,
    )

    result = read_live_allowance(executable)

    assert result.primary is None
    assert result.secondary is None


def test_times_out_without_stalling(tmp_path):
    executable = fake_codex(
        tmp_path,
        """
        if message["method"] == "initialize":
            print(json.dumps({"id": 1, "result": {}}), flush=True)
        elif message["method"] == "account/rateLimits/read":
            time.sleep(10)
        """,
    )

    started = time.monotonic()
    with pytest.raises(RuntimeError, match="request timed out"):
        read_live_allowance(executable, timeout=0.1)

    assert time.monotonic() - started < 2


def test_api_error_is_sanitized(tmp_path):
    executable = fake_codex(
        tmp_path,
        """
        if message["method"] == "initialize":
            print(json.dumps({"id": 1, "result": {}}), flush=True)
        elif message["method"] == "account/rateLimits/read":
            print(json.dumps({"id": 2, "error": {"message": "private account token"}}), flush=True)
        """,
    )

    with pytest.raises(RuntimeError, match="rejected") as error:
        read_live_allowance(executable)

    assert "private account token" not in str(error.value)