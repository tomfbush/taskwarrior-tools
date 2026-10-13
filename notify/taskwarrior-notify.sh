#!/bin/bash
# Taskwarrior due-task notifier for macOS
# Checks for tasks due within the next 5 minutes or up to 30 mins overdue

now=$(date +%s)

output=$(task rc.verbose=nothing rc.json.array=on status:pending due.any: export 2>/dev/null | \
python3 -c "
import json, sys
from datetime import datetime, timezone

now = $now
window = 300  # 5 minutes ahead
overdue = 1800  # 30 minutes behind
data = json.load(sys.stdin)

alerts = []
for t in data:
    due = t.get('due', '')
    if not due:
        continue
    try:
        dt = datetime.strptime(due, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
        due_ts = int(dt.timestamp())
    except ValueError:
        continue

    diff = due_ts - now
    if -overdue <= diff <= window:
        desc = t.get('description', 'Unknown task')
        project = t.get('project', '')
        prefix = f'[{project}] ' if project else ''
        if diff < 0:
            alerts.append(f'{prefix}{desc} (overdue)')
        else:
            alerts.append(f'{prefix}{desc}')

if alerts:
    print(chr(10).join(alerts))
")

if [ -n "$output" ]; then
    escaped=$(echo "$output" | sed 's/"/\\"/g')
    osascript -e "tell application \"System Events\" to display dialog \"$escaped\" with title \"Taskwarrior\" buttons {\"OK\"} default button \"OK\" giving up after 30"
fi
