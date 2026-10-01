from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CODEX_DIR = Path.home() / ".codex"
STATE_DB = CODEX_DIR / "state_5.sqlite"


@dataclass
class WindowUsage:
    used_percent: float
    window_minutes: int
    resets_at: int


@dataclass
class TokenUsage:
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    reasoning_output_tokens: int
    total_tokens: int
    model_context_window: int


@dataclass
class CodexUsage:
    session_path: Path
    token_timestamp: str | None
    allowance_timestamp: str | None
    plan_type: str | None
    primary: WindowUsage | None
    secondary: WindowUsage | None
    tokens: TokenUsage | None


def newest_session() -> Path:
    """Return the rollout file belonging to the most recently updated thread."""

    connection = sqlite3.connect(STATE_DB)

    try:
        row = connection.execute(
            """
            SELECT rollout_path
            FROM threads
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        raise RuntimeError("No Codex threads found.")

    path = Path(row[0])

    if not path.is_file():
        raise RuntimeError(f"Codex session does not exist: {path}")

    return path


def _window(data: dict[str, Any] | None) -> WindowUsage | None:
    if not data:
        return None

    return WindowUsage(
        used_percent=float(data["used_percent"]),
        window_minutes=int(data["window_minutes"]),
        resets_at=int(data["resets_at"]),
    )


def read_usage(session_path: Path) -> CodexUsage:
    latest_tokens: TokenUsage | None = None
    latest_timestamp: str | None = None
    allowance_timestamp: str | None = None

    primary: WindowUsage | None = None
    secondary: WindowUsage | None = None
    plan_type: str | None = None

    with session_path.open(encoding="utf-8") as session:
        for line in session:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("type") != "event_msg":
                continue

            payload = event.get("payload", {})

            if payload.get("type") != "token_count":
                continue

            event_timestamp = event.get("timestamp")

            info = payload.get("info")

            if info:
                token_timestamp = event_timestamp
                last = info.get("last_token_usage")

                if last:
                    latest_tokens = TokenUsage(
                        input_tokens=int(last.get("input_tokens", 0)),
                        cached_input_tokens=int(
                            last.get("cached_input_tokens", 0)
                        ),
                        output_tokens=int(last.get("output_tokens", 0)),
                        reasoning_output_tokens=int(
                            last.get("reasoning_output_tokens", 0)
                        ),
                        total_tokens=int(last.get("total_tokens", 0)),
                        model_context_window=int(
                            info.get("model_context_window", 0)
                        ),
                    )

            # Some token_count events contain no rate_limits.
            # Keep the newest valid rate-limit information we've seen.
            limits = payload.get("rate_limits")

            if limits:
                allowance_timestamp = event_timestamp

                primary_data = limits.get("primary")
                secondary_data = limits.get("secondary")

                if primary_data:
                    primary = _window(primary_data)

                if secondary_data:
                    secondary = _window(secondary_data)

                if limits.get("plan_type"):
                    plan_type = limits["plan_type"]

    return CodexUsage(
        session_path=session_path,
        token_timestamp=token_timestamp,
        allowance_timestamp=allowance_timestamp,
        plan_type=plan_type,
        primary=primary,
        secondary=secondary,
        tokens=latest_tokens,
   )
