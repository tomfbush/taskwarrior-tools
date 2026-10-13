# taskwarrior-tools

A couple of scrappy utilities for [Taskwarrior](https://taskwarrior.org/) on macOS. Built with Claude Code in a single session — it works, but it's a bit of a hack.

## `task week` — Weekly Agenda View

A terminal agenda showing tasks scheduled, due, or overdue for the current work week (Mon–Fri). Groups by day, sorts by time, highlights overdue tasks in red.

```
Week of 07 Oct – 11 Oct 2026
────────────────────────────────────────────────────────────────────────

  OVERDUE
   12 09:00 H Fix login page timeout             ProjectA   (due 2d ago)

  Today
    5 10:00 M Weekly sync call                    ProjectB   (due Tue)
   18       L Update DNS records                  Personal   (sched Tue)

  Wednesday 09 Oct
    3 14:00 H Deploy staging build                ProjectA   (due Wed)
```

### Setup

Add a shell function wrapper to your `.zshrc` / `.bashrc`:

```bash
task() {
    case "$1" in
        week) python3 /path/to/tw-tools/week.py ;;
        urgency) shift; python3 /path/to/tw-tools/urgency.py "$@" ;;
        *) command task "$@" ;;
    esac
}
```

Then just run `task week`.

## `task urgency` — Project Urgency Ranking

Shows weighted urgency aggregated by project across all incomplete tasks (pending + waiting).

Two modes:

- **`task urgency`** — weighted score: `mean_urgency × ln(task_count + 1)`. Projects with both high urgency *and* lots of tasks rise to the top.
- **`task urgency --mean`** — simple mean urgency per project. Shows which projects are hottest per-task regardless of volume.

```
Project Urgency  (score = mean urgency × ln(tasks + 1))
──────────────────────────────────────────────────────────────
  Project                   Tasks   Score     Avg     Max
  ────────────────────────────────────────────────────────
  ProjectB                     11    20.3     8.2     9.0
  ProjectA                     13    18.7     7.1    14.9
  Home                          4    10.8     6.7    11.0
  Personal                     15     5.0     1.8    26.9
```

Output is colour-coded: red for top 30%, yellow for middle, white for lower urgency.

## `taskwarrior-notify.sh` — macOS Due Task Notifications

A shell script that checks for tasks due within the next 5 minutes (or up to 30 minutes overdue) and shows a macOS dialog popup via `osascript`.

### Setup

1. Copy `notify/taskwarrior-notify.sh` somewhere sensible
2. Make it executable: `chmod +x taskwarrior-notify.sh`
3. Add a cron job: `crontab -e`

```
*/5 * * * * /path/to/taskwarrior-notify.sh
```

**Requires:** Python 3, Taskwarrior 3.x, macOS (uses `osascript`)

## Caveats

- These were thrown together quickly to scratch a personal itch
- The notification script uses `osascript` System Events dialogs — not proper notification centre integration
- Only tested on macOS with Taskwarrior 3.5.0
- The week view assumes your work week is Monday–Friday
- No tests, no CI, no warranty

## License

MIT
