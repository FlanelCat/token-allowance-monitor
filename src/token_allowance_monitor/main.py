from __future__ import annotations

import argparse
import json
import os
import time
import sys
import sqlite3
from datetime import datetime

from .codex_usage import WindowUsage, newest_session, read_usage


def bar(percent: float, width: int = 20) -> str:
    percent = max(0.0, min(100.0, percent))
    filled = round(width * percent / 100)
    return "█" * filled + "░" * (width - filled)


def reset_time(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).astimezone().strftime(
        "%Y-%m-%d %H:%M:%S %Z"
    )


def time_remaining(reset: datetime, now: datetime) -> str:
    seconds = max(0, int((reset - now).total_seconds()))

    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, _ = divmod(seconds, 60)

    parts = []

    if days:
        parts.append(f"{days}d")

    if hours or days:
        parts.append(f"{hours}h")

    parts.append(f"{minutes}m")

    return " ".join(parts)


def print_window(name: str, usage: WindowUsage | None) -> None:
    print(name)

    if usage is None:
        print("  No usage information available")
        return

    now = datetime.now().astimezone()
    reset = datetime.fromtimestamp(usage.resets_at).astimezone()
    expired = reset <= now

    if expired:
        print(f"  {bar(0)}  0% used")
        print("  100% remaining")
        print(
            "  STATUS: NEW WINDOW — "
            "awaiting fresh Codex activity"
        )
        return

    print(
        f"  {bar(usage.used_percent)}  "
        f"{usage.used_percent:.0f}% used"
    )
    print(f"  {100 - usage.used_percent:.0f}% remaining")
    print(
        "  Reset:",
        reset.strftime("%Y-%m-%d %H:%M:%S %Z"),
    )
    print(f"  Time remaining: {time_remaining(reset, now)}")

    if usage.used_percent >= 100:
        print("  STATUS: LIMIT REACHED")


def main() -> None:
    session = newest_session()
    usage = read_usage(session)

    print()
    print(f"CODEX USAGE — {(usage.plan_type or 'unknown').upper()}")
    print("=" * 48)

    if usage.token_timestamp:
        timestamp = datetime.fromisoformat(
            usage.token_timestamp.replace("Z", "+00:00")
        ).astimezone()

        print(
            "Latest token data:",
            timestamp.strftime("%Y-%m-%d %H:%M:%S %Z"),
        )

    if usage.allowance_timestamp:
        timestamp = datetime.fromisoformat(
            usage.allowance_timestamp.replace("Z", "+00:00")
        ).astimezone()

        print(
            "Latest allowance data:",
            timestamp.strftime("%Y-%m-%d %H:%M:%S %Z"),
        )

    if usage.token_timestamp or usage.allowance_timestamp:
        print()

    print_window("5-hour allowance", usage.primary)

    print()
    print_window("Weekly allowance", usage.secondary)

    if usage.tokens is not None:
        tokens = usage.tokens
        non_cached = max(
            0,
            tokens.input_tokens - tokens.cached_input_tokens,
        )

        print()
        print("Latest request")
        print(f"  Input:       {tokens.input_tokens:>10,}")
        print(f"  Cached:      {tokens.cached_input_tokens:>10,}")
        print(f"  Non-cached:  {non_cached:>10,}")
        print(f"  Output:      {tokens.output_tokens:>10,}")
        print(f"  Reasoning:   {tokens.reasoning_output_tokens:>10,}")
        print(f"  Total:       {tokens.total_tokens:>10,}")

        if tokens.model_context_window:
            context_percent = (
                tokens.input_tokens
                / tokens.model_context_window
                * 100
            )

            print()
            print("Request input / context window")
            print(
                f"  {tokens.input_tokens:,} / "
                f"{tokens.model_context_window:,} "
                f"({context_percent:.1f}%)"
            )

    print()


def compact() -> None:
    session = newest_session()
    usage = read_usage(session)
    now = datetime.now().astimezone()

    def percent(window: WindowUsage | None) -> float | None:
        if window is None:
            return None

        reset = datetime.fromtimestamp(
            window.resets_at
        ).astimezone()

        if reset <= now:
            return 0.0

        return window.used_percent

    primary_percent = percent(usage.primary)
    secondary_percent = percent(usage.secondary)

    if primary_percent is None:
        primary_text = "5h: ?"
    else:
        primary_text = f"5h: {primary_percent:.0f}%"

    if secondary_percent is None:
        secondary_text = "Week: ?"
    else:
        secondary_text = f"Week: {secondary_percent:.0f}%"

        if usage.secondary is not None:
            reset = datetime.fromtimestamp(
                usage.secondary.resets_at
            ).astimezone()

            if reset > now:
                secondary_text += (
                    f" · {time_remaining(reset, now)}"
                )

    status = ""

    if (
        usage.secondary is not None
        and secondary_percent is not None
        and secondary_percent >= 100
    ):
        status = " | LIMIT REACHED"
    elif (
        usage.primary is not None
        and primary_percent is not None
        and primary_percent >= 100
    ):
        status = " | LIMIT REACHED"

    print(
        f"{primary_text} | "
        f"{secondary_text}"
        f"{status}"
    )


def json_output() -> None:
    session = newest_session()
    usage = read_usage(session)
    now = datetime.now().astimezone()

    def window_data(
        window: WindowUsage | None,
    ) -> dict[str, object] | None:
        if window is None:
            return None

        reset = datetime.fromtimestamp(
            window.resets_at
        ).astimezone()

        fresh = reset > now

        if fresh:
            used_percent = window.used_percent
        else:
            used_percent = 0.0

        return {
            "used_percent": used_percent,
            "remaining_percent": max(
                0.0,
                100.0 - used_percent,
            ),
            "fresh": fresh,
            "resets_at": (
                reset.isoformat()
                if fresh
                else None
            ),
            "reset_display": (
                reset.strftime("%Y-%m-%d %H:%M %Z")
                if fresh
                else None
            ),
            "time_remaining": (
                time_remaining(reset, now)
                if fresh
                else None
            ),
        }

    five_hour = window_data(usage.primary)
    weekly = window_data(usage.secondary)

    limit_reached = any(
        window is not None
        and bool(window["fresh"])
        and float(window["used_percent"]) >= 100
        for window in (five_hour, weekly)
    )

    data = {
        "plan": usage.plan_type,
        "five_hour": five_hour,
        "weekly": weekly,
        "limit_reached": limit_reached,
        "token_timestamp": usage.token_timestamp,
        "allowance_timestamp": usage.allowance_timestamp,
    }

    print(json.dumps(data, indent=2))


def cli() -> None:
    parser = argparse.ArgumentParser(
        description="Display local Codex allowance and token usage."
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Continuously refresh the display.",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Display a single-line usage summary.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Display usage as JSON.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Refresh interval in seconds (default: 5).",
    )

    args = parser.parse_args()
    if args.json and args.watch:
        parser.error("--json cannot currently be combined with --watch")

    if args.interval <= 0:
        parser.error("--interval must be greater than zero")

    try:
        if not args.watch:
            if args.json:
                json_output()
            elif args.compact:
                compact()
            else:
                main()
            return

        while True:
            os.system("clear")
            if args.compact:
                compact()
            else:
                main()
            print()
            print(
                f"Watching for Codex activity — "
                f"refresh every {args.interval:g}s"
            )
            print("Press Ctrl+C to stop.")
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print()
    except (RuntimeError, OSError, sqlite3.Error) as error:
        print(f"codex-usage: error: {error}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    cli()
