#!/usr/bin/env python3
"""Terminal kanban: pending tasks in side-by-side columns grouped by top-level project."""

import json
import re
import shutil
import subprocess
from collections import defaultdict
from datetime import datetime, timezone

RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

PRI_DOT = {"H": f"{RED}●{RESET}", "M": f"{YELLOW}●{RESET}", "L": f"{GREEN}·{RESET}"}
PRI_ORDER = {"H": 0, "M": 1, "L": 2, "": 3}

GAP = 2   # spaces between columns
MIN_COL = 22


def vlen(s):
    """Visible length of string (strips ANSI codes)."""
    return len(re.sub(r'\033\[[0-9;]*m', '', s))


def vpad(s, width):
    """Pad string to visible width."""
    return s + ' ' * max(0, width - vlen(s))


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


def build_block(project_name, tasks, col_width, now):
    """Return a list of padded lines for one project column."""
    lines = []

    # Header
    name = project_name or "(none)"
    count = f"{DIM} {len(tasks)}{RESET}"
    header = f"{BOLD}{CYAN}{name}{RESET}{count}"
    lines.append(vpad(header, col_width))
    lines.append(DIM + "─" * col_width + RESET)

    for t in tasks:
        pri = t.get("priority", "")
        desc = t.get("description", "")
        task_id = t.get("id", 0)
        sub = t.get("project", "")

        due_dt = parse_tw_datetime(t.get("due", ""))
        sched_dt = parse_tw_datetime(t.get("scheduled", ""))
        time_str = format_time(due_dt) or format_time(sched_dt)

        dot = PRI_DOT.get(pri, " ")
        id_str = f"{DIM}{task_id}{RESET}"
        id_chars = len(str(task_id)) if task_id else 1

        # Subproject suffix (e.g. ".PPC" shown as dim tag)
        top = project_name or ""
        subproject_tag = ""
        if sub and sub != top and sub.startswith(top + "."):
            tag = sub[len(top) + 1:].split(".")[0]
            subproject_tag = f"{DIM}.{tag}{RESET}"
            sub_chars = len(tag) + 1
        else:
            sub_chars = 0

        # Time prefix
        time_prefix = f"{BOLD}{time_str}{RESET} " if time_str else ""
        time_chars = len(time_str) + 1 if time_str else 0

        # Available chars for description:
        # dot(1) + space(1) + time_prefix + desc + space(1) + subproject + space(1) + id
        overhead = 1 + 1 + time_chars + 1 + sub_chars + (1 if sub_chars else 0) + 1 + id_chars
        desc_max = max(8, col_width - overhead)
        if len(desc) > desc_max:
            desc = desc[:desc_max - 1] + "…"

        # Check overdue
        due_date = due_dt.date() if due_dt else None
        if due_date and due_date < now:
            desc_col = f"{RED}{desc}{RESET}"
        else:
            desc_col = desc

        line = f"{dot} {time_prefix}{desc_col}"
        if subproject_tag:
            line += f" {subproject_tag}"
        line += f" {id_str}"

        lines.append(vpad(line, col_width))

    return lines


def main():
    term_width = shutil.get_terminal_size((120, 40)).columns
    now = datetime.now().date()

    result = subprocess.run(
        ["task", "rc.verbose=nothing", "rc.json.array=on", "rc.context=",
         "status:pending", "export"],
        capture_output=True, text=True
    )
    tasks = json.loads(result.stdout)

    # Group by top-level project
    by_project = defaultdict(list)
    for t in tasks:
        project = t.get("project", "")
        top = project.split(".")[0] if project else ""
        by_project[top].append(t)

    # Sort within each project: H first, then by urgency desc
    for proj_tasks in by_project.values():
        proj_tasks.sort(key=lambda t: (
            PRI_ORDER.get(t.get("priority", ""), 3),
            -t.get("urgency", 0),
        ))

    # Sort projects: named projects alphabetically, (none) last
    projects = sorted(by_project.keys(), key=lambda p: ("\xff" if not p else p.lower()))

    # Calculate column layout
    num_cols = max(1, min(len(projects), (term_width + GAP) // (MIN_COL + GAP)))
    col_width = (term_width - GAP * (num_cols - 1)) // num_cols

    # Build and print rows of blocks
    blocks = [build_block(p, by_project[p], col_width, now) for p in projects]

    print()
    for row_start in range(0, len(blocks), num_cols):
        row = [list(b) for b in blocks[row_start:row_start + num_cols]]
        height = max(len(b) for b in row)
        empty = ' ' * col_width
        for b in row:
            b += [empty] * (height - len(b))
        for i in range(height):
            print((' ' * GAP).join(b[i] for b in row))
        print()

    total = len(tasks)
    print(f"{DIM}  {total} task{'s' if total != 1 else ''} · {len(projects)} project{'s' if len(projects) != 1 else ''}{RESET}\n")


if __name__ == "__main__":
    main()
