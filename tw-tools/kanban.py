#!/usr/bin/env python3
"""Terminal kanban: pending tasks in side-by-side columns grouped by top-level project.

Usage:
  task kanban           group by top-level project
  task kanban --sub     group by full subproject (ATSPACE.PPC, ATSPACE.SEO, …)
  task kanban ATSPACE   only show columns under one top-level project
"""

import json
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone

RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

PRI_DOT = {"H": f"{RED}H{RESET}", "M": f"{YELLOW}M{RESET}", "L": f"{GREEN}L{RESET}"}
PRI_ORDER = {"H": 0, "M": 1, "L": 2, "": 3}

GAP = 2          # spaces between columns
PREFERRED_COL = 30  # target column width; fewer wider cols on narrow terminals


def vlen(s):
    """Visible length of string (strips ANSI codes)."""
    return len(re.sub(r'\033\[[0-9;]*m', '', s))


def vtrim(s, width):
    """Hard-trim string to at most `width` visible characters, preserving ANSI codes."""
    result = []
    count = 0
    i = 0
    while i < len(s):
        if s[i] == '\033':
            j = i + 1
            while j < len(s) and s[j] != 'm':
                j += 1
            result.append(s[i:j + 1])
            i = j + 1
        else:
            if count >= width:
                break
            result.append(s[i])
            count += 1
            i += 1
    result.append(RESET)
    return ''.join(result)


def vfit(s, width):
    """Pad or trim string to exactly `width` visible characters."""
    current = vlen(s)
    if current < width:
        return s + ' ' * (width - current)
    if current > width:
        return vtrim(s, width)
    return s


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


def build_block(project_name, tasks, col_width, now, show_sub_tag=True):
    """Return a list of padded lines for one project column."""
    lines = []

    # Header — truncate name if it would overflow col_width
    name = project_name or "(none)"
    count_visible = f" {len(tasks)}"
    max_name = col_width - len(count_visible)
    if len(name) > max_name:
        name = name[:max_name - 1] + "…"
    header = f"{BOLD}{CYAN}{name}{RESET}{DIM}{count_visible}{RESET}"
    lines.append(vfit(header, col_width))
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

        # Subproject suffix (e.g. ".PPC" shown as dim tag) — only in top-level mode
        top = project_name or ""
        subproject_tag = ""
        sub_chars = 0
        if show_sub_tag and sub and sub != top and sub.startswith(top + "."):
            tag = sub[len(top) + 1:].split(".")[0]
            subproject_tag = f"{DIM}.{tag}{RESET}"
            sub_chars = len(tag) + 1

        # Time prefix
        time_prefix = f"{BOLD}{time_str}{RESET} " if time_str else ""
        time_chars = len(time_str) + 1 if time_str else 0

        # Available chars for description
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

        lines.append(vfit(line, col_width))

    return lines


def main():
    args = sys.argv[1:]
    use_sub = "--sub" in args
    filter_top = next((a for a in args if not a.startswith("-")), None)

    term_width = shutil.get_terminal_size((120, 40)).columns
    now = datetime.now().date()

    result = subprocess.run(
        ["task", "rc.verbose=nothing", "rc.json.array=on", "rc.context=",
         "status:pending", "export"],
        capture_output=True, text=True
    )
    tasks = json.loads(result.stdout)

    # Determine grouping key
    def group_key(t):
        project = t.get("project", "")
        if use_sub:
            return project  # full project path as column
        return project.split(".")[0] if project else ""

    # Filter to a single top-level project if requested
    if filter_top:
        tasks = [t for t in tasks
                 if t.get("project", "").split(".")[0].lower() == filter_top.lower()]

    by_project = defaultdict(list)
    for t in tasks:
        by_project[group_key(t)].append(t)

    # Sort within each project
    for proj_tasks in by_project.values():
        proj_tasks.sort(key=lambda t: (
            PRI_ORDER.get(t.get("priority", ""), 3),
            -t.get("urgency", 0),
        ))

    # Sort projects alphabetically, (none) last
    projects = sorted(by_project.keys(), key=lambda p: ("\xff" if not p else p.lower()))

    # Calculate column layout
    num_cols = max(1, min(len(projects), (term_width + GAP) // (PREFERRED_COL + GAP)))
    col_width = (term_width - GAP * (num_cols - 1)) // num_cols

    # In --sub mode, no subproject tag (the column name IS the subproject)
    blocks = [build_block(p, by_project[p], col_width, now, show_sub_tag=not use_sub)
              for p in projects]

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
