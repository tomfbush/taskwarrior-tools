# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A collection of Python/shell utilities that extend Taskwarrior on macOS. These are exposed as custom subcommands via a shell function wrapper in `~/.zshrc`.

## Architecture

- **`tw-tools/week.py`** — Weekly agenda view (`task week`). Exports all pending tasks via `task export`, filters to those due/scheduled this work week or overdue, groups by day, sorts by time within each day.
- **`tw-tools/urgency.py`** — Project urgency ranking (`task urgency`). Aggregates Taskwarrior's built-in urgency scores by project. Two modes: weighted (`mean × ln(n+1)`) and simple mean (`--mean`).
- **`notify/taskwarrior-notify.sh`** — macOS notification script. Checks for tasks due within 5 minutes or 30 minutes overdue, pops an `osascript` dialog. Runs via cron every 5 minutes.

All tools shell out to `task export` and parse the JSON. Taskwarrior date format is `%Y%m%dT%H%M%SZ` (UTC). Times are converted to local timezone for display.

## Running

```bash
python3 tw-tools/week.py
python3 tw-tools/urgency.py [--mean]
bash notify/taskwarrior-notify.sh
```

No dependencies beyond Python 3 stdlib and Taskwarrior 3.x.

## Shell Integration

The `task` wrapper in `~/.zshrc` dispatches custom subcommands before falling through to `command task`:

```bash
task() {
    case "$1" in
        week) python3 ~/taskwarrior-claude-cleanup/tw-tools/week.py ;;
        urgency) shift; python3 ~/taskwarrior-claude-cleanup/tw-tools/urgency.py "$@" ;;
        *) command task "$@" ;;
    esac
}
```

New tools should follow this pattern: add a Python script in `tw-tools/` and a case branch in the wrapper.

## Conventions

- No real client names, employee names, or identifying information in code, examples, or commit history. Use generic placeholders like "ProjectA" in README examples.
- ANSI colour constants are defined at module level; use the same set (`RED`, `YELLOW`, `GREEN`, `CYAN`, `DIM`, `BOLD`, `RESET`) for consistency.
- Taskwarrior export flags: always use `rc.verbose=nothing rc.json.array=on rc.context=none` to get clean JSON output.
- Public repo: https://github.com/tomfbush/taskwarrior-tools
