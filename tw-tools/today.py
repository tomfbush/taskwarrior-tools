#!/usr/bin/env python3
"""Show Taskwarrior tasks due, scheduled, or overdue for today."""

import json
import subprocess
from datetime import datetime, timezone

# ANSI colours
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

PRI_COLOUR = {"H": RED, "M": YELLOW, "L": GREEN}


def parse_tw_date(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone().date()
    except ValueError:
        return None


def parse_tw_datetime(s):
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc).astimezone()
    except ValueError:
        return None


def format_time(dt):
    if dt and (dt.hour != 0 or dt.minute != 0):
        return dt.strftime("%H:%M")
    return ""


def print_task(t, due, sched, now, overdue=False):
    pri = t.get("priority", "")
    project = t.get("project", "")
    desc = t.get("description", "")
    colour = PRI_COLOUR.get(pri, "")

    pri_str = f"{colour}{pri}{RESET}" if pri else " "
    proj_str = f"{DIM}{project}{RESET}" if project else ""

    due_dt = parse_tw_datetime(t.get("due", ""))
    sched_dt = parse_tw_datetime(t.get("scheduled", ""))
    time_str = format_time(due_dt) or format_time(sched_dt)
    time_col = f"{BOLD}{time_str}{RESET}" if time_str else "     "

    due_date = parse_tw_date(t.get("due", ""))
    sched_date = parse_tw_date(t.get("scheduled", ""))
    date_parts = []
    if due_date and overdue:
        days = (now - due_date).days
        date_parts.append(f"{RED}due {days}d ago{RESET}")
    if sched_date and sched_date != now:
        date_parts.append(f"sched {sched_date.strftime('%a')}")
    date_str = f" {DIM}({', '.join(date_parts)}){RESET}" if date_parts else ""

    task_id = t.get("id", 0)
    id_str = f"{DIM}{task_id:>3d}{RESET}" if task_id else f"{DIM}  -{RESET}"

    max_desc = 38
    if len(desc) > max_desc:
        desc = desc[:max_desc - 1] + "…"

    print(f"  {id_str} {time_col} {pri_str} {desc:<39s} {proj_str:<18s}{date_str}")


def main():
    now = datetime.now().date()

    result = subprocess.run(
        ["task", "rc.verbose=nothing", "rc.json.array=on", "rc.context=none",
         "status:pending", "export"],
        capture_output=True, text=True
    )
    tasks = json.loads(result.stdout)

    today_tasks = []
    overdue_tasks = []

    for t in tasks:
        due = parse_tw_date(t.get("due", ""))
        sched = parse_tw_date(t.get("scheduled", ""))
        due_dt = parse_tw_datetime(t.get("due", ""))
        sched_dt = parse_tw_datetime(t.get("scheduled", ""))

        is_overdue = due and due < now
        due_today = due and due == now
        sched_today = sched and sched == now

        if is_overdue:
            overdue_tasks.append((due, t))
        elif due_today or sched_today:
            sort_time = None
            for dt in [due_dt, sched_dt]:
                if dt and (dt.hour != 0 or dt.minute != 0):
                    sort_time = dt.time() if sort_time is None else min(sort_time, dt.time())
            if sort_time is None:
                sort_time = datetime.max.time()
            today_tasks.append((sort_time, due, sched, t))

    overdue_tasks.sort(key=lambda x: x[0])
    today_tasks.sort(key=lambda x: x[0])

    print(f"\n{BOLD}Today — {now.strftime('%A %d %b %Y')}{RESET}")
    print(f"{'─' * 72}")

    if overdue_tasks:
        print(f"\n{RED}{BOLD}  OVERDUE{RESET}")
        for due, t in overdue_tasks:
            print_task(t, due, None, now, overdue=True)

    if today_tasks:
        print(f"\n{CYAN}{BOLD}  Today{RESET}")
        for sort_time, due, sched, t in today_tasks:
            print_task(t, due, sched, now)

    if not overdue_tasks and not today_tasks:
        print(f"\n  {DIM}Nothing due or scheduled for today.{RESET}")

    total = len(overdue_tasks) + len(today_tasks)
    print(f"\n{'─' * 72}")
    print(f"  {total} task{'s' if total != 1 else ''}", end="")
    if overdue_tasks:
        print(f" ({RED}{len(overdue_tasks)} overdue{RESET})", end="")
    print()
    print()


if __name__ == "__main__":
    main()
