from __future__ import annotations

import json
import queue
import shutil
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .codex_usage import WindowUsage


@dataclass
class LiveAllowance:
    fetched_at: str
    plan_type: str | None
    primary: WindowUsage | None
    secondary: WindowUsage | None
    ordinary_usage_allowed: bool | None


def _window(data: dict[str, Any] | None) -> WindowUsage | None:
    if not isinstance(data, dict):
        return None

    try:
        duration = int(data["windowDurationMins"])
        if duration not in (300, 10080):
            return None

        return WindowUsage(
            used_percent=float(data["usedPercent"]),
            window_minutes=duration,
            resets_at=int(data["resetsAt"]),
        )
    except (KeyError, TypeError, ValueError, OverflowError):
        return None


def _read_response(
    lines: queue.Queue[bytes | None],
    request_id: int,
    deadline: float,
) -> dict[str, Any]:
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise RuntimeError("Codex app-server request timed out.")

        try:
            line = lines.get(timeout=remaining)
        except queue.Empty:
            raise RuntimeError("Codex app-server request timed out.") from None

        if line is None:
            raise RuntimeError("Codex app-server closed before replying.")

        try:
            message = json.loads(line)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise RuntimeError("Codex app-server returned invalid JSON.") from None

        if not isinstance(message, dict) or message.get("id") != request_id:
            continue

        if "error" in message:
            raise RuntimeError("Codex app-server rejected the request.")

        result = message.get("result")
        if not isinstance(result, dict):
            raise RuntimeError("Codex app-server returned an invalid response.")
        return result


def _send(process: subprocess.Popen[bytes], message: dict[str, Any]) -> None:
    if process.stdin is None:
        raise RuntimeError("Could not communicate with Codex app-server.")

    try:
        process.stdin.write(json.dumps(message).encode("utf-8") + b"\n")
        process.stdin.flush()
    except OSError:
        raise RuntimeError("Could not communicate with Codex app-server.") from None


def read_live_allowance(
    executable: str | Path | None = None,
    timeout: float = 10.0,
) -> LiveAllowance:
    """Read current allowance data from Codex's app-server."""

    if timeout <= 0:
        raise ValueError("timeout must be greater than zero")

    command = str(executable) if executable is not None else shutil.which("codex")
    if not command:
        raise RuntimeError("Codex CLI was not found.")

    try:
        process = subprocess.Popen(
            [command, "app-server", "--stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        raise RuntimeError("Could not start Codex app-server.") from None

    lines: queue.Queue[bytes | None] = queue.Queue()

    def read_stdout() -> None:
        assert process.stdout is not None
        try:
            for line in iter(process.stdout.readline, b""):
                lines.put(line)
        finally:
            lines.put(None)

    reader = threading.Thread(target=read_stdout, daemon=True)
    reader.start()
    deadline = time.monotonic() + timeout

    try:
        _send(
            process,
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "token-allowance-monitor",
                        "version": "0.1.0",
                    }
                },
            },
        )
        _read_response(lines, 1, deadline)
        _send(
            process,
            {"jsonrpc": "2.0", "method": "initialized"},
        )
        _send(
            process,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "account/rateLimits/read",
                "params": {"excludeResetCreditDetails": True},
            },
        )
        result = _read_response(lines, 2, deadline)
        rate_limits = result.get("rateLimits")
        if not isinstance(rate_limits, dict):
            raise RuntimeError("Codex app-server returned no rate limits.")

        windows = [
            _window(value)
            for value in rate_limits.values()
            if isinstance(value, dict)
        ]
        primary = next(
            (window for window in windows if window and window.window_minutes == 300),
            None,
        )
        secondary = next(
            (window for window in windows if window and window.window_minutes == 10080),
            None,
        )
        ordinary = result.get("ordinaryUsageAllowed")

        return LiveAllowance(
            fetched_at=datetime.now(timezone.utc).isoformat(),
            plan_type=(
                rate_limits.get("planType")
                if isinstance(rate_limits.get("planType"), str)
                else None
            ),
            primary=primary,
            secondary=secondary,
            ordinary_usage_allowed=(ordinary if isinstance(ordinary, bool) else None),
        )
    finally:
        if process.stdin is not None:
            try:
                process.stdin.close()
            except OSError:
                pass
        try:
            process.wait(timeout=1)
        except subprocess.TimeoutExpired:
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        reader.join(timeout=1)
        if process.stdout is not None:
            process.stdout.close()