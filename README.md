# Token Allowance Monitor

A local usage monitor for OpenAI Codex on Linux.

Token Allowance Monitor reads Codex's locally stored session data and displays
the current 5-hour and weekly allowance usage without modifying Codex data.

The project includes both a command-line interface and a KDE Plasma 6 widget.

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

From the project directory:

    pipx install .

This installs Token Allowance Monitor into an isolated Python environment and
exposes the `codex-usage` command in:

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

The Plasma 6 widget source is located in:

    plasma/org.flanelcat.codexusage/

It can be installed for the current user with:

    kpackagetool6 --type Plasma/Applet \
        --install plasma/org.flanelcat.codexusage

For an already installed development version:

    kpackagetool6 --type Plasma/Applet \
        --upgrade plasma/org.flanelcat.codexusage

## Privacy

Token Allowance Monitor operates locally and reads only the Codex data required
to determine usage information.

It does not require access to `~/.codex/auth.json` and does not modify Codex
session data.

Codex session files may contain prompts, source code, and other private
information and should never be committed to this repository.

## License

MIT
