#!/usr/bin/env python3
"""Show weighted urgency by project across all incomplete Taskwarrior tasks."""

import json
import math
import subprocess
import sys
from collections import defaultdict

# ANSI colours
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
CYAN = "\033[96m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def colour_score(score, max_score):
    if max_score == 0:
        return f"{DIM}{score:>7.1f}{RESET}"
    ratio = score / max_score
    if ratio > 0.7:
        return f"{RED}{score:>7.1f}{RESET}"
    elif ratio > 0.4:
        return f"{YELLOW}{score:>7.1f}{RESET}"
    else:
        return f"{score:>7.1f}"


def main():
    mode = "weighted"
    if len(sys.argv) > 1 and sys.argv[1] in ("--mean", "-m"):
        mode = "mean"

    result = subprocess.run(
        ["task", "rc.verbose=nothing", "rc.json.array=on", "rc.context=none",
         "(status:pending or status:waiting)", "export"],
        capture_output=True, text=True
    )
    tasks = json.loads(result.stdout)

    projects = defaultdict(lambda: {"count": 0, "total_urgency": 0, "max_urgency": 0})

    for t in tasks:
        proj = t.get("project", "(none)")
        urg = t.get("urgency", 0)
        projects[proj]["count"] += 1
        projects[proj]["total_urgency"] += urg
        projects[proj]["max_urgency"] = max(projects[proj]["max_urgency"], urg)

    rows = []
    for proj, d in projects.items():
        avg = d["total_urgency"] / d["count"] if d["count"] else 0
        if mode == "weighted":
            score = avg * math.log(d["count"] + 1)
        else:
            score = avg
        rows.append((score, avg, d["count"], d["max_urgency"], proj))

    rows.sort(key=lambda x: -x[0])

    if mode == "weighted":
        label = "Score"
        description = f"score = mean urgency × ln(tasks + 1)"
    else:
        label = "Mean"
        description = f"score = mean urgency"

    max_score = rows[0][0] if rows else 0

    print(f"\n{BOLD}Project Urgency{RESET}  {DIM}({description}){RESET}")
    print(f"{'─' * 62}")
    print(f"  {'Project':<25s} {'Tasks':>5s} {label:>7s} {'Avg':>7s} {'Max':>7s}")
    print(f"  {'─' * 56}")

    for score, avg, count, max_urg, proj in rows:
        score_str = colour_score(score, max_score)
        print(f"  {proj:<25s} {count:>5d} {score_str} {avg:>7.1f} {max_urg:>7.1f}")

    print(f"\n  {DIM}{len(rows)} projects, {sum(r[2] for r in rows)} tasks{RESET}")
    if mode == "weighted":
        print(f"  {DIM}Use --mean / -m for simple mean urgency{RESET}")
    else:
        print(f"  {DIM}Omit --mean for weighted score (mean × ln(n+1)){RESET}")
    print()


if __name__ == "__main__":
    main()
