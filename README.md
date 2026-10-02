# Token Allowance Monitor

A local usage monitor for OpenAI Codex on Linux.

Token Allowance Monitor reads Codex's locally stored session data and displays
the current 5-hour and weekly allowance usage without modifying Codex data.

The project includes both a command-line interface and a KDE Plasma 6 widget.

<a href="https://www.buymeacoffee.com/flanelcat">
  <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
       alt="Buy FlanelCat a Coffee"
       height="50">
</a>

## Features

- Displays 5-hour Codex allowance usage
- Displays weekly Codex allowance usage
- Shows remaining allowance
- Shows reset time and countdown
- Detects stale allowance data after a window has reset
- Displays latest request token usage
- Shows cached and non-cached input tokens
- Automatically follows the most recently active Codex session
- Live terminal watch mode
- Compact terminal output
- JSON output for integrations
- KDE Plasma 6 panel widget

## Requirements

- Linux
- Python 3.11 or newer
- A local Codex installation using `~/.codex`
- KDE Plasma 6 for the optional Plasma widget

## Installation

[pipx](https://pipx.pypa.io/) is the recommended installation method.

Clone the repository and install the command-line application with pipx:

    git clone https://github.com/FlanelCat/token-allowance-monitor.git
    cd token-allowance-monitor
    pipx install .

This keeps the application in an isolated Python environment while exposing
the `codex-usage` command in:

    ~/.local/bin/codex-usage

Run the monitor:

    codex-usage

Compact output:

    codex-usage --compact

Live monitoring:

    codex-usage --watch

Machine-readable output:

    codex-usage --json

## Development

Create a virtual environment and install the project in editable mode:

    python -m venv .venv
    .venv/bin/python -m pip install -e .

## KDE Plasma widget

The Plasma widget requires the command-line application to be installed with
pipx so that `$HOME/.local/bin/codex-usage` is available.

The Plasma 6 widget is included in the project source under:

    plasma/org.flanelcat.codexusage/

From a cloned or downloaded copy of the project, install it for the current
user with:

    kpackagetool6 --type Plasma/Applet \
        --install plasma/org.flanelcat.codexusage

For an already installed development version:

    kpackagetool6 --type Plasma/Applet \
        --upgrade plasma/org.flanelcat.codexusage

## Compatibility

Token Allowance Monitor reads Codex's local state and session data directly
from `~/.codex`.

These local data formats are internal to Codex and may change between Codex
versions. Such changes may require an update to Token Allowance Monitor.

## Privacy

Token Allowance Monitor operates locally and reads only the Codex data required
to determine usage information.

It does not require access to `~/.codex/auth.json` and does not modify Codex
session data.

Codex session files may contain prompts, source code, and other private
information and should never be committed to this repository.

## License

MIT
