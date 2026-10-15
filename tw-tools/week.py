#!/usr/bin/env python3
"""Show Taskwarrior tasks scheduled, due, or overdue for the current work week (Mon-Fri)."""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone

# ANSI colours
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

PRI_COLOUR = {"H": RED, "M": YELLOW, "L": GREEN}


def get_week_bounds():
    """Return Monday 00:00 and Friday 23:59:59 of the current work week."""
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    return monday, friday


def parse_tw_date(s):
    """Parse Taskwarrior date string like 20261008T200000Z. Returns date only."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone().date()
    except ValueError:
        return None


def parse_tw_datetime(s):
    """Parse Taskwarrior date string, return full local datetime."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone()
    except ValueError:
        return None


def main():
    monday, friday = get_week_bounds()
    now = datetime.now().date()

    result = subprocess.run(
        ["task", "rc.verbose=nothing", "rc.json.array=on", "rc.context=",
         "status:pending", "export"],
        capture_output=True, text=True
    )
    tasks = json.loads(result.stdout)

    week_tasks = []
    overdue_tasks = []

    for t in tasks:
        due = parse_tw_date(t.get("due", ""))
        sched = parse_tw_date(t.get("scheduled", ""))
        due_dt = parse_tw_datetime(t.get("due", ""))
        sched_dt = parse_tw_datetime(t.get("scheduled", ""))

        is_overdue = due and due < now
        in_week_due = due and monday <= due <= friday
        in_week_sched = sched and monday <= sched <= friday

        if is_overdue:
            overdue_tasks.append((due, sched, t))
        elif in_week_due or in_week_sched:
            sort_date = min(d for d in [due, sched] if d) if any([due, sched]) else monday
            # Sort time: use the earliest datetime with a real time, fallback to end of day
            sort_time = None
            for dt in [due_dt, sched_dt]:
                if dt and (dt.hour != 0 or dt.minute != 0):
                    sort_time = dt.time() if sort_time is None else min(sort_time, dt.time())
            if sort_time is None:
                sort_time = datetime.max.time()  # no specific time = end of day
            week_tasks.append((sort_date, sort_time, due, sched, t))

    overdue_tasks.sort(key=lambda x: x[0])
    week_tasks.sort(key=lambda x: (x[0], x[1]))

    print(f"\n{BOLD}Week of {monday.strftime('%d %b')} – {friday.strftime('%d %b %Y')}{RESET}")
    print(f"{'─' * 72}")

    if overdue_tasks:
        print(f"\n{RED}{BOLD}  OVERDUE{RESET}")
        for due, sched, t in overdue_tasks:
            print_task(t, due, sched, now, overdue=True)

    # Group by day
    days_shown = set()
    for sort_date, sort_time, due, sched, t in week_tasks:
        display_date = sort_date
        if display_date not in days_shown:
            day_label = "Today" if display_date == now else display_date.strftime("%A %d %b")
            print(f"\n{CYAN}{BOLD}  {day_label}{RESET}")
            days_shown.add(display_date)
        print_task(t, due, sched, now)

    if not overdue_tasks and not week_tasks:
        print(f"\n  {DIM}Nothing scheduled or due this week.{RESET}")

    total = len(overdue_tasks) + len(week_tasks)
    print(f"\n{'─' * 72}")
    print(f"  {total} task{'s' if total != 1 else ''}", end="")
    if overdue_tasks:
        print(f" ({RED}{len(overdue_tasks)} overdue{RESET})", end="")
    print()
    print()


def format_time(dt):
    """Format a datetime's time component, or return empty if midnight (no specific time)."""
    if dt and (dt.hour != 0 or dt.minute != 0):
        return dt.strftime("%H:%M")
    return ""


def print_task(t, due, sched, now, overdue=False):
    pri = t.get("priority", "")
    project = t.get("project", "")
    desc = t.get("description", "")
    colour = PRI_COLOUR.get(pri, "")

    # Priority indicator
    pri_str = f"{colour}{pri}{RESET}" if pri else " "

    # Project tag
    proj_str = f"{DIM}{project}{RESET}" if project else ""

    # Time — pick the most relevant time to show
    due_dt = parse_tw_datetime(t.get("due", ""))
    sched_dt = parse_tw_datetime(t.get("scheduled", ""))
    time_str = format_time(due_dt) or format_time(sched_dt)
    time_col = f"{BOLD}{time_str}{RESET}" if time_str else "     "

    # Date info for context
    due_date = parse_tw_date(t.get("due", ""))
    sched_date = parse_tw_date(t.get("scheduled", ""))
    date_parts = []
    if due_date:
        if overdue:
            days = (now - due_date).days
            date_parts.append(f"{RED}due {days}d ago{RESET}")
        else:
            date_parts.append(f"due {due_date.strftime('%a')}")
    if sched_date:
        date_parts.append(f"sched {sched_date.strftime('%a')}")
    date_str = f" {DIM}({', '.join(date_parts)}){RESET}" if date_parts else ""

    # Task ID
    task_id = t.get("id", 0)
    id_str = f"{DIM}{task_id:>3d}{RESET}" if task_id else f"{DIM}  -{RESET}"

    # Truncate description
    max_desc = 38
    if len(desc) > max_desc:
        desc = desc[:max_desc - 1] + "…"

    print(f"  {id_str} {time_col} {pri_str} {desc:<39s} {proj_str:<18s}{date_str}")


if __name__ == "__main__":
    main()
